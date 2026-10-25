"""Run locked source/runtime-dependency scans and fail closed before packaging."""

from argparse import ArgumentParser
from datetime import UTC, datetime
from hashlib import sha256
from importlib.metadata import version
from json import dumps, loads
from pathlib import Path
from re import fullmatch
from subprocess import STDOUT, TimeoutExpired, run
from sys import executable
from tempfile import TemporaryDirectory
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRECTORIES = ("src/finsecure_pay", "scripts", "ops/jenkins")
REPORT_NAMES = (
    "security-summary.json",
    "security-tools.txt",
    "security-export.txt",
    "runtime-requirements.txt",
    "bandit.json",
    "bandit.txt",
    "pip-audit.json",
    "pip-audit.txt",
)
SCAN_BUDGET_SECONDS = 300
ADVISORY_TIMEOUT_SECONDS = 15


def runtime_pins(text: str) -> dict[str, str]:
    """Accept only the current lock's plain exact pins, not URLs, markers or pip options."""
    pins = {}
    for line in text.splitlines():
        match = fullmatch(r"([a-z0-9]+(?:-[a-z0-9]+)*)==([0-9][A-Za-z0-9.!+_-]*)", line)
        if match is None or match[1] in pins:
            raise ValueError("Runtime export must contain unique canonical names and exact pins")
        pins[match[1]] = match[2]
    if not pins:
        raise ValueError("Runtime export is empty")
    return pins


def bandit_result(report: dict, returncode: int, expected_files: set[str]) -> dict[str, int]:
    """Retain LOW findings; block MEDIUM/HIGH and reject partial or inconsistent scans."""
    if not isinstance(report, dict) or report.get("errors") != []:
        raise ValueError("Bandit failed or skipped source files")
    results = report.get("results")
    metrics = report.get("metrics")
    if not isinstance(results, list) or not isinstance(metrics, dict):
        raise ValueError("Bandit report is missing results or file metrics")
    metric_files = {name.removeprefix("./") for name in metrics if name != "_totals"}
    if metric_files != expected_files or not expected_files:
        raise ValueError("Bandit did not scan the complete source inventory")
    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for finding in results:
        if (
            not isinstance(finding, dict)
            or finding.get("issue_severity") not in counts
            or finding.get("issue_confidence") not in counts
            or not isinstance(finding.get("filename"), str)
            or finding["filename"].removeprefix("./") not in expected_files
            or not isinstance(finding.get("test_id"), str)
        ):
            raise ValueError("Bandit returned an invalid finding")
        counts[finding["issue_severity"]] += 1
    if type(returncode) is not int or returncode != int(bool(results)):
        raise ValueError("Bandit exit status disagrees with the complete report")
    return {**counts, "blocking_findings": counts["MEDIUM"] + counts["HIGH"]}


def dependency_result(report: dict, returncode: int, pins: dict[str, str]) -> dict[str, int]:
    """Require every exported dependency/version to be audited without skips or ignores."""
    if not isinstance(report, dict) or not isinstance(report.get("dependencies"), list):
        raise ValueError("Dependency report is missing its dependency list")
    if report.get("fixes") != []:
        raise ValueError("Unexpected automatic fixes or incomplete dependency report")
    audited = {}
    findings = 0
    for dependency in report["dependencies"]:
        if not isinstance(dependency, dict) or "skip_reason" in dependency:
            raise ValueError("A runtime dependency was skipped or invalid")
        name = dependency.get("name")
        if not isinstance(name, str) or name in audited:
            raise ValueError("Invalid or duplicate audited dependency")
        vulnerabilities = dependency.get("vulns")
        if not isinstance(vulnerabilities, list):
            raise ValueError("Dependency vulnerability results are missing")
        for vulnerability in vulnerabilities:
            if (
                not isinstance(vulnerability, dict)
                or not isinstance(vulnerability.get("id"), str)
                or not vulnerability["id"]
            ):
                raise ValueError("Invalid vulnerability record")
        audited[name] = dependency.get("version")
        findings += len(vulnerabilities)
    if not pins or audited != pins:
        raise ValueError("Audit does not match every exact exported runtime pin")
    if type(returncode) is not int or returncode != int(bool(findings)):
        raise ValueError("pip-audit exit status disagrees with the complete report")
    return {"dependencies_audited": len(audited), "blocking_findings": findings}


def run_tool(arguments: list[str], log: Path, deadline: float, root: Path) -> int:
    """Run once with the remaining shared budget; keep diagnostics in the owned report."""
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise TimeoutError("Shared scan budget exhausted")
    with log.open("w", encoding="utf-8") as output:
        return run(
            arguments, cwd=root, stdout=output, stderr=STDOUT, timeout=remaining, check=False
        ).returncode


def scan(root: Path = ROOT) -> int:
    """Write reports on findings/errors; return 0 pass, 1 policy block, or 2 scanner error."""
    started = monotonic()
    deadline = started + SCAN_BUDGET_SECONDS
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    # Only replace this tool's named outputs, never another build's history or workspace.
    for name in REPORT_NAMES:
        (reports / name).unlink(missing_ok=True)
    summary = {
        "started_at_utc": datetime.now(UTC).isoformat(),
        "status": "incomplete",
        "budget_seconds": SCAN_BUDGET_SECONDS,
        "advisory_request_timeout_seconds": ADVISORY_TIMEOUT_SECONDS,
        "bandit": {"status": "not_run"},
        "dependencies": {"status": "not_run"},
    }
    summary_path = reports / "security-summary.json"
    summary_path.write_text(dumps(summary, indent=2) + "\n", encoding="utf-8")
    tools = {name: version(name) for name in ("bandit", "pip-audit", "defusedxml")}
    (reports / "security-tools.txt").write_text(
        "".join(f"{name}=={value}\n" for name, value in tools.items()), encoding="utf-8"
    )
    files = sorted(
        path.relative_to(root).as_posix()
        for directory in SCAN_DIRECTORIES
        for path in (root / directory).rglob("*.py")
    )
    summary["source_files"] = files
    summary["source_sha256"] = {
        name: sha256((root / name).read_bytes()).hexdigest() for name in files
    }
    summary["lock_sha256"] = sha256((root / "uv.lock").read_bytes()).hexdigest()
    try:
        # Explicit files and nosec override prevent silent scope/suppression changes.
        status = run_tool(
            [
                executable,
                "-m",
                "bandit",
                "--severity-level",
                "all",
                "--confidence-level",
                "all",
                "--ignore-nosec",
                "--format",
                "json",
                "--output",
                "reports/bandit.json",
                *files,
            ],
            reports / "bandit.txt",
            deadline,
            root,
        )
        result = bandit_result(
            loads((reports / "bandit.json").read_text(encoding="utf-8")), status, set(files)
        )
        summary["bandit"] = {
            "status": "blocked" if result["blocking_findings"] else "passed",
            "exit_code": status,
            **result,
        }
    except OSError, ValueError, TimeoutError, TimeoutExpired:
        summary["bandit"] = {"status": "error", "reason": "execution_or_report_invalid"}
    # Still attempt the dependency audit after source findings, within the same budget.
    try:
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
                "reports/runtime-requirements.txt",
            ],
            reports / "security-export.txt",
            deadline,
            root,
        )
        if status != 0:
            raise ValueError("Locked dependency export failed")
        pins = runtime_pins((reports / "runtime-requirements.txt").read_text(encoding="utf-8"))
        with TemporaryDirectory(prefix="finsecure-audit-") as cache:
            status = run_tool(
                [
                    executable,
                    "-m",
                    "pip_audit",
                    "--requirement",
                    "reports/runtime-requirements.txt",
                    "--no-deps",
                    "--disable-pip",
                    "--strict",
                    "--vulnerability-service",
                    "pypi",
                    "--timeout",
                    str(ADVISORY_TIMEOUT_SECONDS),
                    "--cache-dir",
                    cache,
                    "--progress-spinner",
                    "off",
                    "--format",
                    "json",
                    "--output",
                    "reports/pip-audit.json",
                ],
                reports / "pip-audit.txt",
                deadline,
                root,
            )
        result = dependency_result(
            loads((reports / "pip-audit.json").read_text(encoding="utf-8")), status, pins
        )
        summary["dependencies"] = {
            "status": "blocked" if result["blocking_findings"] else "passed",
            "exit_code": status,
            **result,
        }
    except OSError, ValueError, TimeoutError, TimeoutExpired:
        summary["dependencies"] = {"status": "error", "reason": "execution_or_report_invalid"}
    statuses = {summary[name]["status"] for name in ("bandit", "dependencies")}
    exit_code = 2 if "error" in statuses else 1 if "blocked" in statuses else 0
    summary["status"] = {0: "passed", 1: "blocked", 2: "error"}[exit_code]
    summary["finished_at_utc"] = datetime.now(UTC).isoformat()
    summary["elapsed_seconds"] = monotonic() - started
    summary_path.write_text(dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Security gate: {summary['status']}; see reports/security-summary.json")
    return exit_code


def main() -> None:
    """Scan this checkout without fixing, ignoring, publishing, or deploying anything."""
    ArgumentParser(description=__doc__).parse_args()
    raise SystemExit(scan())


if __name__ == "__main__":
    main()
