"""Synthetic offline transfer-integrity, gate, archive and fail-closed parser cases."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from gzip import compress
from hashlib import sha256
from io import BytesIO
from json import dumps, loads
from pathlib import Path
from re import findall
from tarfile import SYMTYPE, TarFile, TarInfo
from time import monotonic

from pytest import fixture, mark, raises

from scripts.image_scan import DB_REPOSITORY, TRIVY_SHA256, TRIVY_VERSION, image_result
from scripts.release_archive import BoundedReader, inspect_release_archive, strict_json
from scripts.release_artifacts import FILES, IMAGE_REPORTS, main, same_json, verify_artifacts

NOW = datetime(2026, 11, 4, 6, tzinfo=UTC)
REVISION = "a" * 40
TAG = "finsecure-pay-ci:jenkins-finsecure-ci-1"


def encoded(value: object) -> bytes:
    return dumps(value, separators=(",", ":")).encode()


def export_members(diff_id: str | None = None) -> tuple[list[tuple[str, bytes]], str]:
    """Build one small valid OCI/Docker export, using only synthetic layer content."""
    inner = BytesIO()
    with TarFile.open(fileobj=inner, mode="w") as archive:
        info = TarInfo("synthetic.txt")
        info.size = len(b"synthetic")
        archive.addfile(info, BytesIO(b"synthetic"))
    layer = compress(inner.getvalue(), mtime=0)
    config = encoded(
        {
            "os": "linux",
            "architecture": "amd64",
            "config": {
                "User": "10001:10001",
                "Labels": {"org.opencontainers.image.revision": REVISION},
            },
            "rootfs": {
                "type": "layers",
                "diff_ids": [diff_id or "sha256:" + sha256(inner.getvalue()).hexdigest()],
            },
        }
    )
    image_id = "sha256:" + sha256(config).hexdigest()
    layer_id = "sha256:" + sha256(layer).hexdigest()
    oci = encoded(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {
                "mediaType": "application/vnd.oci.image.config.v1+json",
                "digest": image_id,
                "size": len(config),
            },
            "layers": [
                {
                    "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                    "digest": layer_id,
                    "size": len(layer),
                }
            ],
        }
    )
    index = encoded(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [
                {
                    "mediaType": "application/vnd.oci.image.manifest.v1+json",
                    "digest": "sha256:" + sha256(oci).hexdigest(),
                    "size": len(oci),
                    "platform": {"architecture": "amd64", "os": "linux"},
                }
            ],
        }
    )
    config_name = "blobs/sha256/" + image_id.split(":")[1]
    layer_name = "blobs/sha256/" + layer_id.split(":")[1]
    manifest = encoded([{"RepoTags": [TAG], "Config": config_name, "Layers": [layer_name]}])
    return [
        (config_name, config),
        (layer_name, layer),
        ("blobs/sha256/" + sha256(oci).hexdigest(), oci),
        ("manifest.json", manifest),
        ("index.json", index),
        ("oci-layout", encoded({"imageLayoutVersion": "1.0.0"})),
    ], image_id


def write_archive(path: Path, members: list[tuple[str, bytes]], link: bool = False) -> None:
    with TarFile.open(path, mode="w:gz") as archive:
        for name, data in members:
            info = TarInfo(name)
            info.size = len(data)
            archive.addfile(info, BytesIO(data))
        if link:
            info = TarInfo("blobs/sha256/" + "f" * 64)
            info.type = SYMTYPE
            info.linkname = "../../outside"
            archive.addfile(info)


def refresh(tree: dict, image_hashes: bool = True) -> None:
    """Model a controller receipt over producer bytes; never treat it as release eligibility."""
    root, control = tree["root"], tree["control"]
    if image_hashes:
        path = root / "reports/image-security-summary.json"
        image = loads(path.read_bytes())
        image["report_sha256"] = {
            name: sha256((root / "reports" / name).read_bytes()).hexdigest()
            for name in IMAGE_REPORTS
            if name != "image-security-summary.json"
        }
        path.write_bytes(encoded(image))
    receipt = {
        "schema_version": 1,
        "context": tree["context"],
        "artifacts": {
            name: {
                "size": (root / name).stat().st_size,
                "sha256": sha256((root / name).read_bytes()).hexdigest(),
            }
            for name in FILES
        },
    }
    (control / "receipt.json").write_bytes(encoded(receipt))


def mutate_json(tree: dict, name: str, changes: dict) -> None:
    path = tree["root"] / "reports" / name
    data = loads(path.read_bytes())
    data.update(changes)
    path.write_bytes(encoded(data))
    refresh(tree)


@fixture
def tree(tmp_path: Path) -> dict:
    root, control = tmp_path.resolve() / "input", tmp_path.resolve() / "control"
    root.mkdir(mode=0o700)
    control.mkdir(mode=0o700)
    for name in FILES:
        path = root / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"")
    members, image_id = export_members()
    write_archive(root / "images/finsecure-pay.tar.gz", members)
    lock = '[[package]]\nname="sample"\nversion="1"\nwheels=[{hash="sha256:' + "b" * 64 + '"}]\n'
    project = '[project]\nname="finsecure-pay"\nversion="0.3.0"\n'
    (control / "uv.lock").write_text(lock)
    (control / "pyproject.toml").write_text(project)
    context = {
        "upstream_job": "finsecure-ci",
        "upstream_build": 1,
        "revision": REVISION,
        "image_id": image_id,
        "local_tag": TAG,
        "archive_sha256": sha256((root / "images/finsecure-pay.tar.gz").read_bytes()).hexdigest(),
        "lock_sha256": sha256(lock.encode()).hexdigest(),
        "pyproject_sha256": sha256(project.encode()).hexdigest(),
        "source_sha256": {"src/finsecure_pay/main.py": "c" * 64},
    }
    source = {
        "status": "passed",
        "lock_sha256": context["lock_sha256"],
        "source_sha256": context["source_sha256"],
        "source_files": list(context["source_sha256"]),
        "started_at_utc": (NOW - timedelta(seconds=4)).isoformat(),
        "finished_at_utc": (NOW - timedelta(seconds=3)).isoformat(),
        "bandit": {
            "status": "passed",
            "exit_code": 0,
            "LOW": 0,
            "MEDIUM": 0,
            "HIGH": 0,
            "blocking_findings": 0,
        },
        "dependencies": {
            "status": "passed",
            "exit_code": 0,
            "dependencies_audited": 1,
            "blocking_findings": 0,
        },
    }
    raw_image = {
        "SchemaVersion": 2,
        "Trivy": {"Version": TRIVY_VERSION},
        "ArtifactType": "container_image",
        "CreatedAt": (NOW - timedelta(seconds=1)).isoformat(),
        "Metadata": {
            "ImageID": image_id,
            "OS": {"Family": "alpine", "Name": "3.24.3"},
            "ImageConfig": {
                "os": "linux",
                "architecture": "amd64",
                "config": {
                    "User": "10001:10001",
                    "Labels": {"org.opencontainers.image.revision": REVISION},
                },
            },
        },
        "Results": [
            {"Class": "os-pkgs", "Type": "alpine", "Packages": [{"Name": "musl", "Version": "1"}]},
            {
                "Class": "lang-pkgs",
                "Type": "python-pkg",
                "Packages": [
                    {
                        "Name": name,
                        "Version": version,
                        "FilePath": (
                            f"opt/venv/lib/python3.14/site-packages/{name}.dist-info/METADATA"
                        ),
                    }
                    for name, version in [("sample", "1"), ("finsecure-pay", "0.3.0")]
                ],
            },
        ],
    }
    started = NOW - timedelta(seconds=2)
    image = {
        "status": "passed",
        "lock_sha256": context["lock_sha256"],
        "source_revision": REVISION,
        "image_id": image_id,
        "local_tag": TAG,
        "archive_sha256": context["archive_sha256"],
        "platform": "linux/amd64",
        "expected_platform": "linux/amd64",
        "trivy_version": TRIVY_VERSION,
        "trivy_sha256": TRIVY_SHA256,
        "database_repository": DB_REPOSITORY,
        "database_exit_code": 0,
        "temporary_cache_removed": True,
        "scan_exit_code": 0,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": NOW.isoformat(),
        **image_result(
            raw_image,
            0,
            image_id,
            REVISION,
            {"sample": "1", "finsecure-pay": "0.3.0"},
            started,
            NOW,
            platform="linux/amd64",
        ),
    }
    values = {
        "security-summary.json": source,
        "image-security-summary.json": image,
        "bandit.json": {
            "errors": [],
            "results": [],
            "metrics": {"src/finsecure_pay/main.py": {"loc": 1}},
        },
        "pip-audit.json": {
            "dependencies": [{"name": "sample", "version": "1", "vulns": []}],
            "fixes": [],
        },
        "trivy-db.json": {"Version": 2, "UpdatedAt": (NOW - timedelta(hours=1)).isoformat()},
        "trivy.json": raw_image,
        "buildkit-image.json": {"containerimage.config.digest": image_id},
    }
    for name, value in values.items():
        (root / "reports" / name).write_bytes(encoded(value))
    for name, text in {
        "runtime-requirements.txt": "sample==1 \\\n    --hash=sha256:" + "b" * 64 + "\n",
        "image-runtime-requirements.txt": "sample==1\n",
        "image.sha256": context["archive_sha256"] + "  images/finsecure-pay.tar.gz\n",
        "image-metadata.txt": (
            f"SOURCE_REVISION={REVISION}\nLOCAL_TAG={TAG}\nPLATFORM=linux/amd64\n"
        ),
        "build-metadata.txt": f"SOURCE_REVISION={REVISION}\n{context['lock_sha256']}  uv.lock\n",
    }.items():
        (root / "reports" / name).write_text(text)
    result = {"root": root, "control": control, "context": context, "members": members}
    refresh(result)
    return result


def test_complete_artifacts_verify_without_authorizing_publication(tree):
    result = verify_artifacts(tree["root"], tree["control"], NOW)
    assert result["status"] == "verified"
    assert result["publishing_authorized"] is False
    assert result["verified_files"] == 21
    assert result["database_age_seconds"] == 3600
    assert result["layers"] == 1


@mark.parametrize(
    "payload",
    [
        b'{"x":1,"x":2}',
        b'{"a":{"x":1,"x":2}}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b'{"x":1e999}',
        b"{}{}",
        b"\xff",
        b" " * (1024 * 1024 + 1),
    ],
)
def test_strict_json_rejects_ambiguous_invalid_or_oversized_input(payload):
    with raises((ValueError, UnicodeError)):
        strict_json(payload)


@mark.parametrize("name", sorted(FILES))
def test_every_transferred_file_requires_its_controller_hash(tree, name):
    path = tree["root"] / name
    path.write_bytes(path.read_bytes() + b"tampered")
    with raises(ValueError, match="TRANSFER_HASH_OR_SIZE_MISMATCH"):
        verify_artifacts(tree["root"], tree["control"], NOW)


@mark.parametrize(
    "kind",
    [
        "missing",
        "extra",
        "symlink",
        "hardlink",
        "directory-link",
        "public-root",
        "control-link",
        "bool-schema",
        "bool-build",
        "extra-receipt-field",
    ],
)
def test_receipt_and_filesystem_boundary_fail_closed(tree, kind):
    root, control = tree["root"], tree["control"]
    path = root / "reports/security-tools.txt"
    if kind == "missing":
        path.unlink()
    elif kind == "extra":
        (root / "unexpected.py").write_text("raise SystemExit()")
    elif kind == "symlink":
        path.unlink()
        path.symlink_to(control / "uv.lock")
    elif kind == "hardlink":
        path.unlink()
        path.hardlink_to(control / "uv.lock")
    elif kind == "directory-link":
        (root / "images").rename(root.parent / "outside")
        (root / "images").symlink_to(root.parent / "outside", target_is_directory=True)
    elif kind == "public-root":
        root.chmod(0o755)
    elif kind == "control-link":
        (control / "uv.lock").unlink()
        (control / "uv.lock").symlink_to(path)
    else:
        receipt = loads((control / "receipt.json").read_bytes())
        if kind == "bool-schema":
            receipt["schema_version"] = True
        elif kind == "bool-build":
            receipt["context"]["upstream_build"] = True
        else:
            receipt["extra"] = "not accepted"
        (control / "receipt.json").write_bytes(encoded(receipt))
    with raises((ValueError, OSError)):
        verify_artifacts(root, control, NOW)


@mark.parametrize(
    "name,changes",
    [
        ("security-summary.json", {"status": "failed"}),
        ("security-summary.json", {"source_files": []}),
        ("security-summary.json", {"source_sha256": {}}),
        ("security-summary.json", {"lock_sha256": "f" * 64}),
        ("security-summary.json", {"finished_at_utc": (NOW + timedelta(seconds=1)).isoformat()}),
        ("bandit.json", {"errors": ["synthetic failure"]}),
        ("bandit.json", {"metrics": {}}),
        ("pip-audit.json", {"dependencies": []}),
        ("image-security-summary.json", {"platform": "linux/arm64"}),
        ("image-security-summary.json", {"trivy_sha256": "f" * 64}),
        ("image-security-summary.json", {"database_repository": "unapproved"}),
        ("image-security-summary.json", {"database_exit_code": False}),
        ("image-security-summary.json", {"blocking_findings": False}),
        ("image-security-summary.json", {"local_tag": "different"}),
        ("image-security-summary.json", {"temporary_cache_removed": False}),
        ("trivy.json", {"Results": []}),
        ("trivy-db.json", {"Version": True}),
        ("buildkit-image.json", {"containerimage.config.digest": "sha256:" + "f" * 64}),
    ],
)
def test_recomputes_gate_contracts_after_valid_transfer(tree, name, changes):
    mutate_json(tree, name, changes)
    with raises(ValueError):
        verify_artifacts(tree["root"], tree["control"], NOW)


@mark.parametrize(
    "seconds,accepted", [(0, True), (86400, True), (86400.001, False), (-0.001, False)]
)
def test_database_freshness_is_checked_at_release_time(tree, seconds, accepted):
    mutate_json(tree, "trivy.json", {"CreatedAt": NOW.isoformat()})
    mutate_json(
        tree, "trivy-db.json", {"UpdatedAt": (NOW - timedelta(seconds=seconds)).isoformat()}
    )
    if accepted:
        assert (
            verify_artifacts(tree["root"], tree["control"], NOW)["database_age_seconds"] == seconds
        )
    else:
        with raises(ValueError, match="stale or from the future"):
            verify_artifacts(tree["root"], tree["control"], NOW)


@mark.parametrize("severity", ["HIGH", "CRITICAL"])
def test_raw_vulnerability_blocks_even_when_summary_claims_zero(tree, severity):
    path = tree["root"] / "reports/trivy.json"
    data = loads(path.read_bytes())
    data["Results"][0]["Vulnerabilities"] = [
        {
            "VulnerabilityID": "CVE-synthetic",
            "PkgName": "musl",
            "InstalledVersion": "1",
            "Severity": severity,
        }
    ]
    path.write_bytes(encoded(data))
    refresh(tree)
    with raises(ValueError, match="IMAGE_GATE_MISMATCH"):
        verify_artifacts(tree["root"], tree["control"], NOW)


def test_trusted_source_snapshot_is_not_replaced_by_artifact_claims(tree):
    (tree["control"] / "uv.lock").write_text("modified")
    with raises(ValueError, match="TRUSTED_SOURCE_HASH_MISMATCH"):
        verify_artifacts(tree["root"], tree["control"], NOW)


@mark.parametrize(
    "kind",
    [
        "duplicate",
        "absolute",
        "traversal",
        "link",
        "blob-hash",
        "tag",
        "size",
        "foreign-url",
        "unused-blob",
        "trailing",
    ],
)
def test_archive_rejects_unsafe_or_inconsistent_members(tree, kind):
    members = deepcopy(tree["members"])
    path = tree["root"] / "images/finsecure-pay.tar.gz"
    if kind == "duplicate":
        members.append(members[-1])
    elif kind == "absolute":
        members.append(("/outside", b"{}"))
    elif kind == "traversal":
        members.append(("../outside", b"{}"))
    elif kind == "blob-hash":
        name, data = members[0]
        members[0] = (name, data + b" ")
    elif kind == "unused-blob":
        members.append(("blobs/sha256/" + sha256(b"{}").hexdigest(), b"{}"))
    elif kind in {"tag", "size", "foreign-url"}:
        index = 3 if kind == "tag" else 4
        name, data = members[index]
        value = loads(data)
        if kind == "tag":
            value[0]["RepoTags"] = ["wrong:tag"]
        elif kind == "size":
            value["manifests"][0]["size"] += 1
        else:
            value["manifests"][0]["urls"] = ["https://example.invalid/never-fetch"]
        members[index] = (name, encoded(value))
    write_archive(path, members, link=kind == "link")
    if kind == "trailing":
        with path.open("ab") as stream:
            stream.write(compress(b"unexpected trailing bytes"))
    with raises((ValueError, OSError)):
        inspect_release_archive(path, REVISION, TAG, tree["context"]["image_id"], monotonic() + 10)


def test_layer_bytes_must_match_config_diff_ids_even_with_valid_blob_hashes(tree):
    members, image_id = export_members(diff_id="sha256:" + "f" * 64)
    path = tree["root"] / "images/finsecure-pay.tar.gz"
    write_archive(path, members)
    with raises(ValueError, match="LAYER_DIFF_IDS_MISMATCH"):
        inspect_release_archive(path, REVISION, TAG, image_id, monotonic() + 10)


def test_bounded_reader_stops_expansion_without_closing_borrowed_stream():
    stream = BytesIO(b"12345")
    reader = BoundedReader(stream, 4, monotonic() + 10)
    assert reader.read(2) == b"12"
    with raises(ValueError, match="ARCHIVE_EXPANSION_LIMIT"):
        reader.read(100)
    assert not stream.closed
    stream.close()


def test_bounded_reader_rejects_expired_budget_before_reading():
    with BytesIO(b"12345") as stream:
        reader = BoundedReader(stream, 10, monotonic() - 1)
        with raises(TimeoutError):
            reader.read(1)
        assert stream.tell() == 0


def test_database_cannot_postdate_the_report_that_claims_to_use_it(tree):
    mutate_json(tree, "trivy-db.json", {"UpdatedAt": NOW.isoformat()})
    with raises(ValueError, match="stale or from the future"):
        verify_artifacts(tree["root"], tree["control"], NOW)


@mark.parametrize("severity", ["LOW", "MEDIUM", "HIGH"])
def test_raw_source_findings_are_recomputed_and_low_findings_retained(tree, severity):
    reports = tree["root"] / "reports"
    raw = loads((reports / "bandit.json").read_bytes())
    raw["results"] = [
        {
            "issue_severity": severity,
            "issue_confidence": "HIGH",
            "test_id": "B101",
            "filename": "src/finsecure_pay/main.py",
        }
    ]
    (reports / "bandit.json").write_bytes(encoded(raw))
    summary = loads((reports / "security-summary.json").read_bytes())
    summary["bandit"]["exit_code"] = 1
    if severity == "LOW":
        summary["bandit"]["LOW"] = 1
    (reports / "security-summary.json").write_bytes(encoded(summary))
    refresh(tree)
    if severity == "LOW":
        assert verify_artifacts(tree["root"], tree["control"], NOW)["source_findings"]["LOW"] == 1
    else:
        with raises(ValueError, match="SOURCE_GATE_MISMATCH"):
            verify_artifacts(tree["root"], tree["control"], NOW)


def test_cli_failure_never_prints_untrusted_parser_content(tree, monkeypatch, capsys):
    (tree["control"] / "receipt.json").write_bytes(b'{"SYNTHETIC_NEVER_PRINT_THIS":')
    monkeypatch.setattr(
        "sys.argv",
        [
            "release-artifacts",
            "--input",
            str(tree["root"]),
            "--control",
            str(tree["control"]),
        ],
    )
    assert main() == 2
    captured = capsys.readouterr()
    assert loads(captured.out) == {"status": "failed", "error_type": "JSONDecodeError"}
    assert "SYNTHETIC_NEVER_PRINT_THIS" not in captured.out
    assert captured.err == ""


def test_controller_transfer_inventory_is_fixed_and_matches_verifier():
    source = (
        Path(__file__).resolve().parents[2] / "ops/jenkins/release-transfer.groovy"
    ).read_text()
    assert set(findall(r"'((?:reports|images)/[^']+)'", source)) == FILES
    assert "withCredentials" not in source
    assert "toExternalURL" not in source
    assert "LinkOption.NOFOLLOW_LINKS" in source


def test_json_comparison_does_not_treat_boolean_as_zero():
    assert not same_json({"HIGH": False}, {"HIGH": 0})
    assert not same_json([True], [1])
    assert same_json({"HIGH": 0}, {"HIGH": 0})
