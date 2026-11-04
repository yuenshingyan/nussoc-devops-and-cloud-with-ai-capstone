"""Independently verify transferred artifacts; this module never authorizes or executes delivery."""

from argparse import ArgumentParser
from datetime import UTC, datetime, timedelta
from hashlib import file_digest
from json import dumps
from os import getuid
from pathlib import Path
from re import fullmatch
from stat import S_ISDIR, S_ISREG
from time import monotonic
from tomllib import load

from scripts.image_scan import (
    DB_REPOSITORY,
    TRIVY_SHA256,
    TRIVY_VERSION,
    database_age,
    image_result,
    utc_time,
)
from scripts.release_archive import ARCHIVE_LIMIT, JSON_LIMIT, inspect_release_archive, strict_json
from scripts.security_scan import (
    bandit_result,
    dependency_result,
    hashed_runtime_pins,
    runtime_pins,
)

IMAGE_REPORTS = (
    "image-security-summary.json",
    "image-security-tools.txt",
    "image-security-export.txt",
    "image-runtime-requirements.txt",
    "trivy-db.json",
    "trivy-db.txt",
    "trivy.json",
    "trivy.txt",
)
FILES = frozenset(
    {
        "reports/security-summary.json",
        "reports/security-tools.txt",
        "reports/security-export.txt",
        "reports/runtime-requirements.txt",
        "reports/bandit.json",
        "reports/bandit.txt",
        "reports/pip-audit.json",
        "reports/pip-audit.txt",
        *("reports/" + name for name in IMAGE_REPORTS),
        "reports/build-metadata.txt",
        "reports/image-metadata.txt",
        "reports/buildkit-image.json",
        "reports/image.sha256",
        "images/finsecure-pay.tar.gz",
    }
)
VERIFICATION_SECONDS = 120
CONTEXT_FIELDS = {
    "upstream_job",
    "upstream_build",
    "revision",
    "local_tag",
    "image_id",
    "archive_sha256",
    "lock_sha256",
    "pyproject_sha256",
    "source_sha256",
}


def private_root(path: Path) -> None:
    """Borrow only an existing canonical private directory; never repair caller permissions."""
    info = path.lstat()
    if (
        not path.is_absolute()
        or path.resolve() != path
        or not S_ISDIR(info.st_mode)
        or (info.st_uid != getuid() or info.st_mode & 0o7777 != 0o700)
    ):
        raise ValueError("UNSAFE_INPUT_DIRECTORY")


def regular_file(path: Path, limit: int) -> None:
    """Reject links, foreign ownership, writable-by-others files and oversized input."""
    info = path.lstat()
    if (
        not S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_uid != getuid()
        or (info.st_mode & 0o022 or not 0 <= info.st_size <= limit)
    ):
        raise ValueError("UNSAFE_INPUT_FILE")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def object_file(path: Path) -> dict:
    regular_file(path, JSON_LIMIT)
    value = strict_json(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("EXPECTED_JSON_OBJECT")
    return value


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def same_json(actual: object, expected: object) -> bool:
    """Compare JSON values without Python's boolean/integer equality coercion."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            same_json(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            same_json(left, right) for left, right in zip(actual, expected, strict=True)
        )
    return actual == expected


def verify_artifacts(root: Path, control: Path, now: datetime) -> dict:
    """Recompute gates from fixed inputs and controller-owned receipt/source snapshots.

    The receipt and source snapshots must come from the trusted controller, never from
    upstream artifacts. Eligibility, latest-main checks and publication remain separate.
    """
    deadline = monotonic() + VERIFICATION_SECONDS
    require(now.utcoffset() == timedelta(0), "UTC_CLOCK_REQUIRED")
    private_root(root)
    private_root(control)
    require(
        root != control and root not in control.parents and control not in root.parents,
        "OVERLAPPING_INPUT_CONTROL",
    )
    receipt = object_file(control / "receipt.json")
    require(
        set(receipt) == {"schema_version", "context", "artifacts"}
        and type(receipt["schema_version"]) is int
        and receipt["schema_version"] == 1,
        "INVALID_TRANSFER_RECEIPT",
    )
    context, files = receipt["context"], receipt["artifacts"]
    require(isinstance(context, dict) and set(context) == CONTEXT_FIELDS, "INVALID_CONTEXT")
    require(isinstance(files, dict) and set(files) == FILES, "INVALID_ARTIFACT_INVENTORY")
    for key, pattern in {
        "revision": r"[a-f0-9]{40}",
        "image_id": r"sha256:[a-f0-9]{64}",
        "archive_sha256": r"[a-f0-9]{64}",
        "lock_sha256": r"[a-f0-9]{64}",
        "pyproject_sha256": r"[a-f0-9]{64}",
        "upstream_job": r"[A-Za-z0-9_.-]{1,128}",
    }.items():
        require(
            isinstance(context[key], str) and fullmatch(pattern, context[key]) is not None,
            "INVALID_CONTEXT_IDENTITY",
        )
    require(
        type(context["upstream_build"]) is int and context["upstream_build"] > 0,
        "INVALID_CONTEXT_BUILD",
    )
    tag = f"finsecure-pay-ci:jenkins-{context['upstream_job']}-{context['upstream_build']}"
    require(context["local_tag"] == tag, "INVALID_CONTEXT_TAG")
    observed = set()
    for path in root.rglob("*"):
        name = path.relative_to(root).as_posix()
        if name in {"images", "reports"}:
            require(S_ISDIR(path.lstat().st_mode), "UNSAFE_ARTIFACT_DIRECTORY")
        else:
            require(name in FILES, "UNEXPECTED_ARTIFACT")
            observed.add(name)
    require(observed == FILES, "MISSING_ARTIFACT")
    for name in sorted(FILES):
        path = root / name
        regular_file(path, ARCHIVE_LIMIT if name.startswith("images/") else JSON_LIMIT)
        entry = files[name]
        require(
            isinstance(entry, dict)
            and set(entry) == {"size", "sha256"}
            and type(entry["size"]) is int
            and entry["size"] == path.stat().st_size
            and entry["sha256"] == digest(path),
            "TRANSFER_HASH_OR_SIZE_MISMATCH",
        )
        require(monotonic() < deadline, "VERIFICATION_BUDGET_EXCEEDED")
    for name, key in [("uv.lock", "lock_sha256"), ("pyproject.toml", "pyproject_sha256")]:
        regular_file(control / name, JSON_LIMIT)
        require(digest(control / name) == context[key], "TRUSTED_SOURCE_HASH_MISMATCH")
    with (control / "uv.lock").open("rb") as stream:
        lock = load(stream)
    with (control / "pyproject.toml").open("rb") as stream:
        project = load(stream)["project"]
    require(project["name"] == "finsecure-pay", "WRONG_PROJECT")
    reports = root / "reports"
    source = object_file(reports / "security-summary.json")
    image = object_file(reports / "image-security-summary.json")
    require(source.get("status") == image.get("status") == "passed", "GATE_NOT_PASSED")
    require(
        source.get("lock_sha256") == image.get("lock_sha256") == context["lock_sha256"],
        "GATE_LOCK_MISMATCH",
    )
    source_files = context["source_sha256"]
    require(isinstance(source_files, dict) and bool(source_files), "EMPTY_SOURCE_INVENTORY")
    for name, value in source_files.items():
        require(
            isinstance(name, str)
            and name.endswith(".py")
            and name.startswith(("src/finsecure_pay/", "scripts/", "ops/jenkins/"))
            and ".." not in name.split("/")
            and isinstance(value, str)
            and fullmatch(r"[a-f0-9]{64}", value) is not None,
            "INVALID_SOURCE_INVENTORY",
        )
    require(
        source.get("source_sha256") == source_files
        and isinstance(source.get("source_files"), list)
        and len(source["source_files"]) == len(source_files)
        and set(source["source_files"]) == set(source_files),
        "SOURCE_INVENTORY_MISMATCH",
    )
    pins = hashed_runtime_pins(
        (reports / "runtime-requirements.txt").read_text(encoding="utf-8"), lock
    )
    require(
        pins
        == runtime_pins((reports / "image-runtime-requirements.txt").read_text(encoding="utf-8")),
        "EXPORTS_DISAGREE",
    )
    for tool in ("bandit", "dependencies"):
        require(source.get(tool, {}).get("status") == "passed", "SOURCE_GATE_INVALID")
    bandit = bandit_result(
        object_file(reports / "bandit.json"), source["bandit"]["exit_code"], set(source_files)
    )
    dependencies = dependency_result(
        object_file(reports / "pip-audit.json"), source["dependencies"]["exit_code"], pins
    )
    for computed, declared in [(bandit, source["bandit"]), (dependencies, source["dependencies"])]:
        require(
            computed["blocking_findings"] == 0
            and all(type(declared.get(k)) is int and declared[k] == v for k, v in computed.items()),
            "SOURCE_GATE_MISMATCH",
        )
    require(
        image.get("source_revision") == context["revision"]
        and image.get("local_tag") == tag
        and image.get("image_id") == context["image_id"]
        and image.get("archive_sha256") == context["archive_sha256"]
        and image.get("platform") == image.get("expected_platform") == "linux/amd64",
        "IMAGE_IDENTITY_MISMATCH",
    )
    require(
        image.get("trivy_version") == TRIVY_VERSION
        and image.get("trivy_sha256") == TRIVY_SHA256
        and image.get("database_repository") == DB_REPOSITORY
        and type(image.get("database_exit_code")) is int
        and image["database_exit_code"] == 0
        and image.get("temporary_cache_removed") is True,
        "SCANNER_IDENTITY_INVALID",
    )
    checksums = image.get("report_sha256")
    expected = set(IMAGE_REPORTS) - {"image-security-summary.json"}
    require(
        isinstance(checksums, dict) and set(checksums) == expected, "IMAGE_REPORT_INVENTORY_INVALID"
    )
    for name in expected:
        require(checksums[name] == files["reports/" + name]["sha256"], "IMAGE_REPORT_HASH_MISMATCH")
    started, finished = utc_time(image["started_at_utc"]), utc_time(image["finished_at_utc"])
    require(
        utc_time(source["started_at_utc"])
        <= utc_time(source["finished_at_utc"])
        <= started
        <= finished
        <= now,
        "INVALID_GATE_TIME_ORDER",
    )
    database = object_file(reports / "trivy-db.json")
    raw_image = object_file(reports / "trivy.json")
    age = database_age(database, now)
    # A fresh-looking DB must also have existed when this particular report was produced.
    database_age(database, utc_time(raw_image.get("CreatedAt")))
    inventory = image_result(
        raw_image,
        image["scan_exit_code"],
        context["image_id"],
        context["revision"],
        {**pins, project["name"]: project["version"]},
        started,
        finished,
        platform="linux/amd64",
    )
    require(
        inventory["blocking_findings"] == 0
        and inventory["end_of_life"] is False
        and inventory["runtime_packages"] == {**pins, project["name"]: project["version"]}
        and all(same_json(image.get(k), v) for k, v in inventory.items()),
        "IMAGE_GATE_MISMATCH",
    )
    require(
        files["images/finsecure-pay.tar.gz"]["sha256"] == context["archive_sha256"],
        "ARCHIVE_HASH_MISMATCH",
    )
    require(
        (reports / "image.sha256").read_text()
        == context["archive_sha256"] + "  images/finsecure-pay.tar.gz\n",
        "ARCHIVE_CHECKSUM_FILE_MISMATCH",
    )
    require(
        object_file(reports / "buildkit-image.json").get("containerimage.config.digest")
        == context["image_id"],
        "BUILDKIT_IDENTITY_MISMATCH",
    )
    require(
        (reports / "image-metadata.txt").read_text()
        == f"SOURCE_REVISION={context['revision']}\nLOCAL_TAG={tag}\nPLATFORM=linux/amd64\n",
        "BUILD_METADATA_MISMATCH",
    )
    build_lines = (reports / "build-metadata.txt").read_text().splitlines()
    require(
        [line for line in build_lines if line.startswith("SOURCE_REVISION=")]
        == ["SOURCE_REVISION=" + context["revision"]]
        and [line for line in build_lines if line.endswith("  uv.lock")]
        == [context["lock_sha256"] + "  uv.lock"],
        "SOURCE_METADATA_MISMATCH",
    )
    archive = inspect_release_archive(
        root / "images/finsecure-pay.tar.gz",
        context["revision"],
        tag,
        context["image_id"],
        deadline,
    )
    return {
        "status": "verified",
        "publishing_authorized": False,
        "revision": context["revision"],
        "archive_sha256": context["archive_sha256"],
        "database_age_seconds": age,
        "verified_files": len(FILES),
        "source_findings": bandit,
        **archive,
    }


def main() -> int:
    """Emit only safe identity/results; untrusted parser errors are never printed."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify_artifacts(args.input, args.control, datetime.now(UTC))
    except Exception as error:
        print(dumps({"status": "failed", "error_type": type(error).__name__}))
        return 2
    print(dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
