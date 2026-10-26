"""Image gate contracts, real archive validation and mocked external tool failures."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from json import dumps, loads
from pathlib import Path
from runpy import run_path
from subprocess import CompletedProcess, TimeoutExpired
from tarfile import TarFile, TarInfo
from typing import Any

from pytest import MonkeyPatch, fixture, mark, raises

REVISION = "a" * 40
TAG = "finsecure-pay-ci:jenkins-test-1"
IMAGE = "sha256:" + "b" * 64
NOW = datetime(2026, 10, 25, 12, tzinfo=UTC)


@fixture
def helpers(monkeypatch: MonkeyPatch) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root))
    return run_path(str(root / "scripts/image_scan.py"))


def package(name: str, version: str) -> dict:
    return {
        "Name": name,
        "Version": version,
        "FilePath": f"opt/venv/lib/python3.14/site-packages/{name}.dist-info/METADATA",
    }


def report() -> dict:
    return {
        "SchemaVersion": 2,
        "Trivy": {"Version": "0.76.1"},
        "ArtifactType": "container_image",
        "CreatedAt": NOW.isoformat(),
        "Metadata": {
            "ImageID": IMAGE,
            "OS": {"Family": "alpine", "Name": "3.24.3"},
            "ImageConfig": {
                "os": "linux",
                "architecture": "arm64",
                "config": {
                    "User": "10001:10001",
                    "Labels": {"org.opencontainers.image.revision": REVISION},
                },
            },
        },
        "Results": [
            {"Class": "os-pkgs", "Type": "alpine", "Packages": [package("libc", "1")]},
            {
                "Class": "lang-pkgs",
                "Type": "python-pkg",
                "Packages": [package("sample", "1"), package("finsecure-pay", "0.2.0")],
            },
        ],
    }


def evaluate(helpers: dict, data: dict, status: int = 0) -> dict:
    return helpers["image_result"](
        data, status, IMAGE, REVISION, {"sample": "1", "finsecure-pay": "0.2.0"}, NOW, NOW
    )


@mark.parametrize(
    "severity,blocking", [("UNKNOWN", 0), ("LOW", 0), ("MEDIUM", 0), ("HIGH", 1), ("CRITICAL", 1)]
)
@mark.parametrize("fixed", ["", "2"])
def test_gate_reports_all_severities_and_blocks_high_critical_including_unfixed(
    helpers, severity, blocking, fixed
):
    data = report()
    data["Results"][0]["Vulnerabilities"] = [
        {
            "VulnerabilityID": "CVE-synthetic",
            "PkgName": "libc",
            "InstalledVersion": "1",
            "Severity": severity,
            "FixedVersion": fixed,
        }
    ]
    result = evaluate(helpers, data)
    assert result["blocking_findings"] == blocking
    assert result["severities"][severity] == 1


@mark.parametrize(
    "key,value",
    [
        ("SchemaVersion", True),
        ("SchemaVersion", 3),
        ("Trivy", {"Version": "other"}),
        ("ArtifactType", "filesystem"),
        ("CreatedAt", "2026-10-24T12:00:00Z"),
        ("CreatedAt", "2026-10-25T12:00:01Z"),
        ("CreatedAt", "2026-10-25T12:00:00"),
        ("Results", []),
        ("Results", None),
    ],
)
def test_gate_rejects_wrong_stale_or_incomplete_reports(helpers, key, value):
    data = report()
    data[key] = value
    with raises((ValueError, TypeError)):
        evaluate(helpers, data)


@mark.parametrize(
    "mutation",
    [
        "image",
        "root-user",
        "revision",
        "architecture",
        "unknown-os",
        "unknown-release",
        "missing-version",
        "bad-eol",
        "missing-os-target",
        "duplicate-target",
        "empty-packages",
        "missing-package",
        "wrong-version",
        "wrong-location",
        "duplicate-runtime",
        "modified-findings",
        "invalid-severity",
        "unknown-affected-package",
        "malformed-findings",
    ],
)
def test_gate_fails_closed_on_identity_inventory_and_findings_gaps(helpers, mutation):
    data = report()
    metadata = data["Metadata"]
    config = metadata["ImageConfig"]
    target = data["Results"][0]
    python = data["Results"][1]
    if mutation == "image":
        metadata["ImageID"] = "sha256:" + "c" * 64
    elif mutation == "root-user":
        config["config"]["User"] = "0"
    elif mutation == "revision":
        config["config"]["Labels"] = {}
    elif mutation == "architecture":
        config["architecture"] = "amd64"
    elif mutation == "unknown-os":
        metadata["OS"]["Family"] = "unknown"
    elif mutation == "unknown-release":
        metadata["OS"]["Name"] = "99.1"
    elif mutation == "missing-version":
        metadata["OS"].pop("Name")
    elif mutation == "bad-eol":
        metadata["OS"]["EOSL"] = "false"
    elif mutation == "missing-os-target":
        data["Results"].pop(0)
    elif mutation == "duplicate-target":
        data["Results"] = [target, deepcopy(target)]
    elif mutation == "empty-packages":
        target["Packages"] = []
    elif mutation == "missing-package":
        python["Packages"].pop(0)
    elif mutation == "wrong-version":
        python["Packages"][0]["Version"] = "2"
    elif mutation == "wrong-location":
        python["Packages"][0]["FilePath"] = "other/METADATA"
    elif mutation == "duplicate-runtime":
        python["Packages"].append(deepcopy(python["Packages"][0]))
    elif mutation == "modified-findings":
        target["ExperimentalModifiedFindings"] = [{"Status": "ignored"}]
    elif mutation == "malformed-findings":
        target["Vulnerabilities"] = None
    else:
        target["Vulnerabilities"] = [
            {
                "VulnerabilityID": "CVE-synthetic",
                "PkgName": "libc",
                "InstalledVersion": "1",
                "Severity": "HIGH",
            }
        ]
        if mutation == "invalid-severity":
            target["Vulnerabilities"][0]["Severity"] = "high"
        else:
            target["Vulnerabilities"][0]["PkgName"] = "absent"
    with raises(ValueError):
        evaluate(helpers, data)


@mark.parametrize("status", [1, 2, 3, -9, True])
def test_gate_rejects_scanner_errors_even_with_complete_no_finding_report(helpers, status):
    with raises(ValueError):
        evaluate(helpers, report(), status)


def test_end_of_life_is_blocking_even_without_vulnerabilities(helpers):
    data = report()
    data["Metadata"]["OS"]["EOSL"] = True
    assert evaluate(helpers, data, 2)["end_of_life"] is True
    with raises(ValueError):
        evaluate(helpers, data, 0)


@mark.parametrize("age,accepted", [(0, True), (86400, True), (86400.001, False), (-0.001, False)])
def test_database_freshness_boundaries(helpers, age, accepted):
    metadata = {"Version": 2, "UpdatedAt": (NOW - timedelta(seconds=age)).isoformat()}
    if accepted:
        assert helpers["database_age"](metadata, NOW) == age
    else:
        with raises(ValueError):
            helpers["database_age"](metadata, NOW)


@mark.parametrize(
    "metadata",
    [
        {},
        {"Version": True},
        {"Version": 3},
        {"Version": 2, "UpdatedAt": "2026-10-25T12:00:00"},
        {"Version": 2, "UpdatedAt": "2026-10-25T13:00:00+01:00"},
    ],
)
def test_database_rejects_unsupported_schema_or_non_utc_timestamp(helpers, metadata):
    with raises(ValueError):
        helpers["database_age"](metadata, NOW)


def test_duplicate_json_keys_are_not_last_value_wins(helpers, tmp_path):
    path = tmp_path / "report.json"
    path.write_text('{"Results":[],"Results":[]}')
    with raises(ValueError):
        helpers["read_json"](path)


@mark.parametrize(
    "epoch,release,expected",
    [(0, "", "1"), (0, "2+b1", "1-2+b1"), (1, "2+deb12u3", "1:1-2+deb12u3")],
)
def test_debian_findings_match_full_epoch_and_release(helpers, epoch, release, expected):
    data = report()
    data["Metadata"]["OS"] = {"Family": "debian", "Name": "12.15"}
    target = data["Results"][0]
    target["Type"] = "debian"
    target["Packages"][0].update(Epoch=epoch, Release=release)
    target["Vulnerabilities"] = [
        {
            "VulnerabilityID": "CVE-synthetic",
            "PkgName": "libc",
            "InstalledVersion": expected,
            "Severity": "CRITICAL",
        }
    ]
    assert evaluate(helpers, data)["blocking_findings"] == 1


@mark.parametrize("epoch,release", [(True, "1"), (-1, "1"), ("1", "1"), (1, None), (1, 1)])
def test_invalid_debian_version_components_fail_closed(helpers, epoch, release):
    with raises(ValueError):
        helpers["installed_version"]({"Version": "1", "Epoch": epoch, "Release": release}, "debian")


def create_export(root: Path) -> str:
    """Use a real tiny Docker archive to exercise provenance checks without Docker."""
    config = report()["Metadata"]["ImageConfig"]
    content = dumps(config).encode()
    digest = "sha256:" + sha256(content).hexdigest()
    (root / "images").mkdir()
    (root / "reports").mkdir()
    path = root / "images/finsecure-pay.tar.gz"
    with TarFile.open(path, "w:gz") as archive:
        for name, body in [
            ("config.json", content),
            (
                "manifest.json",
                dumps([{"Config": "config.json", "RepoTags": [TAG], "Layers": []}]).encode(),
            ),
        ]:
            member = TarInfo(name)
            member.size = len(body)
            archive.addfile(member, BytesIO(body))
    (root / "reports/image.sha256").write_text(
        sha256(path.read_bytes()).hexdigest() + "  images/finsecure-pay.tar.gz\n"
    )
    (root / "reports/buildkit-image.json").write_text(
        dumps({"containerimage.config.digest": digest})
    )
    (root / "uv.lock").write_text("synthetic lock")
    (root / "pyproject.toml").write_text('[project]\nname="finsecure-pay"\nversion="0.2.0"\n')
    return digest


@mark.parametrize(
    "mode,expected",
    [
        ("passed", 0),
        ("high-unfixed", 1),
        ("eol", 1),
        ("bad-checksum", 2),
        ("bad-tool", 2),
        ("missing-tool", 2),
        ("bad-version", 2),
        ("version-exit", 2),
        ("export-exit", 2),
        ("db-exit", 2),
        ("db-stale", 2),
        ("db-timeout", 2),
        ("scan-timeout", 2),
        ("scan-exit", 2),
        ("missing-report", 2),
        ("bad-report", 2),
        ("changed-archive", 2),
        ("changed-lock", 2),
    ],
)
def test_orchestration_retains_diagnostics_and_never_retries(
    helpers, monkeypatch, tmp_path, mode, expected
):
    digest = create_export(tmp_path)
    fake = tmp_path / "trivy"
    fake.write_bytes(b"synthetic executable")
    globals_ = helpers["scan"].__globals__
    monkeypatch.setitem(globals_, "TRIVY", fake)
    monkeypatch.setitem(globals_, "TRIVY_SHA256", sha256(fake.read_bytes()).hexdigest())
    monkeypatch.setenv("TRIVY_IGNORE_UNFIXED", "true")
    monkeypatch.setenv("TRIVY_SEVERITY", "LOW")
    if mode == "bad-tool":
        fake.write_bytes(b"changed executable")
    if mode == "missing-tool":
        fake.unlink()
    if mode == "bad-checksum":
        (tmp_path / "reports/image.sha256").write_text("invalid")
    # A previous passing result must never survive a new error.
    (tmp_path / "reports/image-security-summary.json").write_text('{"status":"passed"}')
    calls = []
    scratch = []

    def process(args: list[str], **kwargs: Any) -> CompletedProcess:
        calls.append(args)
        assert kwargs["timeout"] > 0 and kwargs["timeout"] <= 300
        assert not any(key.startswith("TRIVY_") for key in kwargs["env"])
        scratch.append(Path(kwargs["env"]["DOCKER_CONFIG"]).parent)
        assert not list(Path(kwargs["env"]["DOCKER_CONFIG"]).iterdir())
        kwargs["stdout"].write("synthetic diagnostic\n")
        if "--version" in args:
            kwargs["stdout"].write(
                "Version: " + ("other" if mode == "bad-version" else "0.76.1") + "\n"
            )
            return CompletedProcess(args, 1 if mode == "version-exit" else 0)
        if args[0] == "uv":
            Path(args[-1]).write_text("sample==1\n")
            return CompletedProcess(args, 1 if mode == "export-exit" else 0)
        assert args[args.index("--db-repository") + 1] == "ghcr.io/aquasecurity/trivy-db:2"
        if "--download-db-only" in args:
            if mode == "db-timeout":
                raise TimeoutExpired(args, 300)
            cache = Path(args[args.index("--cache-dir") + 1]) / "db"
            cache.mkdir(parents=True)
            now = datetime.now(UTC) - timedelta(days=2 if mode == "db-stale" else 0)
            (cache / "metadata.json").write_text(
                dumps({"Version": 2, "UpdatedAt": now.isoformat()})
            )
            return CompletedProcess(args, 1 if mode == "db-exit" else 0)
        assert (
            "--ignore-unfixed" not in args
            and "--skip-db-update" in args
            and "--offline-scan" in args
        )
        assert Path(args[args.index("--ignorefile") + 1]).read_text() == ""
        if mode == "scan-timeout":
            raise TimeoutExpired(args, 300)
        data = report()
        data["CreatedAt"] = datetime.now(UTC).isoformat()
        data["Metadata"]["ImageID"] = digest
        if mode == "high-unfixed":
            data["Results"][0]["Vulnerabilities"] = [
                {
                    "VulnerabilityID": "CVE-synthetic",
                    "PkgName": "libc",
                    "InstalledVersion": "1",
                    "Severity": "HIGH",
                }
            ]
        if mode == "eol":
            data["Metadata"]["OS"]["EOSL"] = True
        if mode != "missing-report":
            Path(args[-1]).write_text("bad JSON" if mode == "bad-report" else dumps(data))
        if mode == "changed-archive":
            (tmp_path / "images/finsecure-pay.tar.gz").write_bytes(b"changed")
        if mode == "changed-lock":
            (tmp_path / "uv.lock").write_text("changed")
        return CompletedProcess(args, 2 if mode == "eol" else 1 if mode == "scan-exit" else 0)

    monkeypatch.setitem(globals_, "run", process)
    assert helpers["scan"](tmp_path, REVISION, TAG) == expected
    summary = loads((tmp_path / "reports/image-security-summary.json").read_text())
    assert summary["status"] == {0: "passed", 1: "blocked", 2: "error"}[expected]
    assert all(not path.exists() for path in scratch)
    assert sum("--download-db-only" in args for args in calls) <= 1
    assert sum("--input" in args for args in calls) <= 1
    for name, checksum in summary["report_sha256"].items():
        assert sha256((tmp_path / "reports" / name).read_bytes()).hexdigest() == checksum
