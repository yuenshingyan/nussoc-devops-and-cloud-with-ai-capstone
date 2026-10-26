"""Gate one exact CI export using pinned Trivy, a fresh DB and complete OS/Python reports."""

from argparse import ArgumentParser
from datetime import UTC, datetime, timedelta
from hashlib import file_digest
from json import dumps, loads
from os import environ
from pathlib import Path
from re import fullmatch, sub
from subprocess import STDOUT, TimeoutExpired, run
from tarfile import TarError
from tempfile import TemporaryDirectory
from time import monotonic
from tomllib import load

from ops.jenkins.image_archive import inspect_image_archive
from scripts.security_scan import runtime_pins

ROOT = Path(__file__).resolve().parents[1]
TRIVY = Path("/usr/local/bin/trivy")
TRIVY_VERSION = "0.76.1"
TRIVY_SHA256 = "b422130ea54e53e142e65c838662e48919ce9c3f23f17d80066b43e70550cb85"
DB_REPOSITORY = "ghcr.io/aquasecurity/trivy-db:2"
OPERATION_SECONDS = 300
MAX_DB_AGE_SECONDS = 86400
SEVERITIES = ("UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL")
REPORT_NAMES = (
    "image-security-summary.json",
    "image-security-tools.txt",
    "image-security-export.txt",
    "image-runtime-requirements.txt",
    "trivy-db.json",
    "trivy-db.txt",
    "trivy.json",
    "trivy.txt",
)


def checksum(path: Path) -> str:
    """Hash an owned file without loading an image archive into memory."""
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    """Reject ambiguous duplicate JSON keys instead of trusting the last value."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def read_json(path: Path) -> dict:
    """Read a UTF-8 object with unambiguous keys; reject non-object reports."""
    result = loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object")
    return result


def utc_time(value: str) -> datetime:
    """Require an explicitly UTC timestamp, not a local/naive time."""
    if not isinstance(value, str):
        raise ValueError("Missing timestamp")
    timestamp = datetime.fromisoformat(value)
    if timestamp.utcoffset() != timedelta(0):
        raise ValueError("Timestamp must be UTC")
    return timestamp


def database_age(metadata: dict, now: datetime) -> float:
    """Reject wrong-schema, future and stale vulnerability databases."""
    if type(metadata.get("Version")) is not int or metadata["Version"] != 2:
        raise ValueError("Unsupported database schema")
    age = (now - utc_time(metadata.get("UpdatedAt"))).total_seconds()
    if not 0 <= age <= MAX_DB_AGE_SECONDS:
        raise ValueError("Database is stale or from the future")
    return age


def installed_version(package: dict, kind: str) -> str:
    """Reassemble Debian's split epoch/upstream/revision fields without dropping identity."""
    version = package.get("Version")
    if not isinstance(version, str) or not version:
        raise ValueError("Invalid installed package version")
    if kind == "debian":
        epoch = package.get("Epoch", 0)
        release = package.get("Release", "")
        if type(epoch) is not int or epoch < 0 or not isinstance(release, str):
            raise ValueError("Invalid Debian epoch or release")
        version = (f"{epoch}:" if epoch else "") + version + (f"-{release}" if release else "")
    return version


def image_result(
    report: dict,
    returncode: int,
    image_id: str,
    revision: str,
    pins: dict[str, str],
    started: datetime,
    finished: datetime,
) -> dict:
    """Validate image identity, complete inventories and findings before applying policy."""
    if (
        type(report.get("SchemaVersion")) is not int
        or report["SchemaVersion"] != 2
        or report.get("Trivy") != {"Version": TRIVY_VERSION}
        or report.get("ArtifactType") != "container_image"
        or not started <= utc_time(report.get("CreatedAt")) <= finished
    ):
        raise ValueError("Wrong scanner/schema/artifact or stale report")
    metadata = report["Metadata"]
    config = metadata["ImageConfig"]
    if (
        metadata.get("ImageID") != image_id
        or (config.get("os"), config.get("architecture")) != ("linux", "arm64")
        or config["config"].get("User") != "10001:10001"
        or config["config"].get("Labels", {}).get("org.opencontainers.image.revision") != revision
    ):
        raise ValueError("Scan does not describe this exact non-root ARM64 export")
    os_info = metadata["OS"]
    # These are the explicitly tested image families; other families need a scope review.
    if os_info.get("Family") not in {"alpine", "debian"} or not fullmatch(
        r"[0-9]+(?:\.[0-9]+)*", os_info.get("Name", "")
    ):
        raise ValueError("Unsupported or unidentified operating system")
    release = os_info["Name"].split(".")
    if (os_info["Family"] == "alpine" and release[:2] != ["3", "24"]) or (
        os_info["Family"] == "debian" and release[0] not in {"12", "13"}
    ):
        raise ValueError("Unverified OS release; scanner support must be reviewed")
    eol = os_info.get("EOSL", False)
    if type(eol) is not bool or type(returncode) is not int or returncode != (2 if eol else 0):
        raise ValueError("Scanner error or inconsistent end-of-life status")
    targets = report.get("Results")
    if not isinstance(targets, list) or len(targets) != 2:
        raise ValueError("Expected complete OS and Python inventories")
    expected_targets = {(os_info["Family"], "os-pkgs"), ("python-pkg", "lang-pkgs")}
    seen = set()
    counts = dict.fromkeys(SEVERITIES, 0)
    inventory = {}
    runtime = {}
    for target in targets:
        identity = (target.get("Type"), target.get("Class"))
        if identity not in expected_targets or identity in seen or target.get("Misconfigurations"):
            raise ValueError("Unexpected, duplicate or incomplete scanner target")
        if target.get("ExperimentalModifiedFindings"):
            raise ValueError("Ignored/modified findings are not allowed")
        seen.add(identity)
        packages = target.get("Packages")
        if not isinstance(packages, list) or not packages:
            raise ValueError("Missing package inventory")
        installed = set()
        for package in packages:
            name, version = package.get("Name"), package.get("Version")
            if not isinstance(name, str) or not name or not isinstance(version, str) or not version:
                raise ValueError("Invalid package inventory entry")
            installed.add((name, installed_version(package, identity[0])))
            if identity[0] == "python-pkg" and package.get("FilePath", "").lstrip("/").startswith(
                "opt/venv/lib/python3.14/site-packages/"
            ):
                name = sub(r"[-_.]+", "-", name).lower()
                if name in runtime:
                    raise ValueError("Ambiguous application environment inventory")
                runtime[name] = version
        inventory[identity[0]] = len(packages)
        vulnerabilities = target.get("Vulnerabilities", [])
        if not isinstance(vulnerabilities, list):
            raise ValueError("Malformed vulnerability list")
        for finding in vulnerabilities:
            if (
                not isinstance(finding.get("VulnerabilityID"), str)
                or not finding["VulnerabilityID"]
                or finding.get("Severity") not in counts
                or (finding.get("PkgName"), finding.get("InstalledVersion")) not in installed
            ):
                raise ValueError("Invalid finding or missing affected package")
            counts[finding["Severity"]] += 1
    if not pins or any(runtime.get(name) != version for name, version in pins.items()):
        raise ValueError("Scanned runtime does not contain every locked dependency and project")
    return {
        "os": os_info,
        "end_of_life": eol,
        "packages_by_type": inventory,
        "runtime_packages": runtime,
        "severities": counts,
        "blocking_findings": counts["HIGH"] + counts["CRITICAL"],
    }


def run_tool(arguments: list[str], log: Path, deadline: float, cwd: Path, env: dict) -> int:
    """Run once inside the current operation's remaining budget and retain diagnostics."""
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise TimeoutError("Image scan operation budget exhausted")
    with log.open("w", encoding="utf-8") as stream:
        return run(
            arguments,
            cwd=cwd,
            env=env,
            stdout=stream,
            stderr=STDOUT,
            timeout=remaining,
            check=False,
        ).returncode


def scan(root: Path, revision: str, tag: str) -> int:
    """Return 0 only for a complete pass, 1 for policy findings/EOL, 2 for handled errors."""
    started = monotonic()
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    for name in REPORT_NAMES:
        (reports / name).unlink(missing_ok=True)
    summary = {
        "started_at_utc": datetime.now(UTC).isoformat(),
        "status": "incomplete",
        "source_revision": revision,
        "local_tag": tag,
        "database_repository": DB_REPOSITORY,
        "operation_budget_seconds": OPERATION_SECONDS,
        "max_database_age_seconds": MAX_DB_AGE_SECONDS,
        "phase": "input",
        "trivy_version": TRIVY_VERSION,
    }
    summary_path = reports / REPORT_NAMES[0]
    summary_path.write_text(dumps(summary, indent=2) + "\n", encoding="utf-8")
    exit_code = 2
    try:
        if not fullmatch(r"[a-f0-9]{40}", revision) or not fullmatch(
            r"finsecure-pay-ci:[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag
        ):
            raise ValueError("Invalid build identity")
        archive = root / "images/finsecure-pay.tar.gz"
        digest = checksum(archive)
        if (reports / "image.sha256").read_text() != digest + "  images/finsecure-pay.tar.gz\n":
            raise ValueError("Export checksum mismatch")
        metadata = read_json(reports / "buildkit-image.json")
        image = inspect_image_archive(
            archive, revision, tag, metadata["containerimage.config.digest"]
        )
        summary.update(image)
        summary["archive_sha256"] = digest
        summary["lock_sha256"] = checksum(root / "uv.lock")
        deadline = monotonic() + OPERATION_SECONDS
        with TemporaryDirectory(prefix="finsecure-image-scan-") as temporary:
            scratch = Path(temporary)
            (scratch / "config.yaml").write_text("{}\n")
            (scratch / "ignore").write_text("")
            (scratch / "docker").mkdir()
            env = {key: value for key, value in environ.items() if not key.startswith("TRIVY_")}
            env["DOCKER_CONFIG"] = str(scratch / "docker")
            summary["phase"] = "tool"
            if checksum(TRIVY) != TRIVY_SHA256:
                raise ValueError("Scanner executable differs from verified release")
            summary["trivy_sha256"] = TRIVY_SHA256
            status = run_tool(
                [str(TRIVY), "--version"],
                reports / "image-security-tools.txt",
                deadline,
                scratch,
                env,
            )
            if (
                status != 0
                or f"Version: {TRIVY_VERSION}\n"
                not in (reports / "image-security-tools.txt").read_text()
            ):
                raise ValueError("Scanner version command failed")
            summary["phase"] = "export"
            status = run_tool(
                [
                    "uv",
                    "export",
                    "--locked",
                    "--offline",
                    "--no-dev",
                    "--no-emit-project",
                    "--no-hashes",
                    "--no-annotate",
                    "--no-header",
                    "--output-file",
                    str(reports / "image-runtime-requirements.txt"),
                ],
                reports / "image-security-export.txt",
                deadline,
                root,
                env,
            )
            if status != 0:
                raise ValueError("Runtime export failed")
            pins = runtime_pins((reports / "image-runtime-requirements.txt").read_text())
            with (root / "pyproject.toml").open("rb") as source:
                project = load(source)["project"]
            pins[project["name"]] = project["version"]
            common = [
                str(TRIVY),
                "--config",
                str(scratch / "config.yaml"),
                "image",
                "--cache-dir",
                str(scratch / "cache"),
                "--db-repository",
                DB_REPOSITORY,
                "--no-progress",
                "--timeout",
                "5m",
                "--skip-version-check",
            ]
            summary["phase"] = "database"
            status = run_tool(
                [*common, "--download-db-only"], reports / "trivy-db.txt", deadline, scratch, env
            )
            summary["database_exit_code"] = status
            if status != 0:
                raise ValueError("Database download failed")
            db = read_json(scratch / "cache/db/metadata.json")
            (reports / "trivy-db.json").write_text(dumps(db, indent=2) + "\n")
            summary["database_age_seconds"] = database_age(db, datetime.now(UTC))
            summary["phase"] = "scan"
            scan_started = datetime.now(UTC)
            status = run_tool(
                [
                    *common,
                    "--input",
                    str(archive),
                    "--skip-db-update",
                    "--skip-java-db-update",
                    "--offline-scan",
                    "--scanners",
                    "vuln",
                    "--pkg-types",
                    "os,library",
                    "--parallel",
                    "1",
                    "--list-all-pkgs",
                    "--ignorefile",
                    str(scratch / "ignore"),
                    "--severity",
                    ",".join(SEVERITIES),
                    "--exit-code",
                    "0",
                    "--exit-on-eol",
                    "2",
                    "--format",
                    "json",
                    "--output",
                    str(reports / "trivy.json"),
                ],
                reports / "trivy.txt",
                monotonic() + OPERATION_SECONDS,
                scratch,
                env,
            )
            summary["scan_exit_code"] = status
            summary["phase"] = "report"
            result = image_result(
                read_json(reports / "trivy.json"),
                status,
                image["image_id"],
                revision,
                pins,
                scan_started,
                datetime.now(UTC),
            )
            summary["database_age_at_finish_seconds"] = database_age(db, datetime.now(UTC))
            if checksum(archive) != digest or checksum(root / "uv.lock") != summary["lock_sha256"]:
                raise ValueError("Scan inputs changed during execution")
            summary.update(result)
            exit_code = int(bool(result["blocking_findings"] or result["end_of_life"]))
        summary["temporary_cache_removed"] = True
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        TypeError,
        AttributeError,
        IndexError,
        TimeoutError,
        TimeoutExpired,
        TarError,
    ):
        exit_code = 2
        summary["reason"] = "execution_identity_or_report_invalid"
    summary["status"] = {0: "passed", 1: "blocked", 2: "error"}[exit_code]
    summary["finished_at_utc"] = datetime.now(UTC).isoformat()
    summary["elapsed_seconds"] = monotonic() - started
    summary["report_sha256"] = {
        name: checksum(reports / name) for name in REPORT_NAMES[1:] if (reports / name).is_file()
    }
    summary_path.write_text(dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Image gate: {summary['status']}; see reports/{REPORT_NAMES[0]}")
    return exit_code


def main() -> None:
    """Gate this checkout's export; never publish, load, run or deploy an image."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    raise SystemExit(scan(ROOT, args.revision, args.tag))


if __name__ == "__main__":
    main()
