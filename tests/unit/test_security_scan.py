"""Scan policy and fail-closed reports; mock scanner processes, never network services."""

from copy import deepcopy
from json import dumps, loads
from pathlib import Path
from runpy import run_path
from subprocess import CompletedProcess, TimeoutExpired
from typing import Any
from unittest.mock import Mock

from pytest import fixture, mark, raises


@fixture
def scan_helpers() -> dict[str, Any]:
    return run_path(str(Path(__file__).resolve().parents[2] / "scripts/security_scan.py"))


@mark.parametrize(
    "text",
    [
        "",
        "sample>=1",
        "sample==1\nsample==1\n",
        "-e .",
        "sample @ https://example.invalid/x",
        "sample==1 ; python_version > '3'",
    ],
)
def test_runtime_export_rejects_non_exact_or_unhandled_requirements(scan_helpers, text):
    with raises(ValueError):
        scan_helpers["runtime_pins"](text)


def test_runtime_export_accepts_only_exact_unique_pins(scan_helpers):
    assert scan_helpers["runtime_pins"]("sample-package==1.0.0\nother==2.0rc1\n") == {
        "sample-package": "1.0.0",
        "other": "2.0rc1",
    }


def source_report(severity: str | None = None, confidence: str = "HIGH") -> dict:
    """Minimal synthetic output using the scanner's public JSON fields."""
    return {
        "errors": [],
        "metrics": {"src/finsecure_pay/main.py": {}, "_totals": {}},
        "results": []
        if severity is None
        else [
            {
                "issue_severity": severity,
                "issue_confidence": confidence,
                "filename": "src/finsecure_pay/main.py",
                "test_id": "B314",
            }
        ],
    }


@mark.parametrize("severity,blocking", [("LOW", 0), ("MEDIUM", 1), ("HIGH", 1)])
@mark.parametrize("confidence", ["LOW", "MEDIUM", "HIGH"])
def test_bandit_blocks_medium_high_at_every_confidence(
    scan_helpers, severity, blocking, confidence
):
    result = scan_helpers["bandit_result"](
        source_report(severity, confidence), 1, {"src/finsecure_pay/main.py"}
    )
    assert result[severity] == 1
    assert result["blocking_findings"] == blocking


@mark.parametrize(
    "problem",
    [
        "errors",
        "missing_files",
        "bad_severity",
        "bad_confidence",
        "missing_results",
        "exit_zero_with_finding",
        "exit_error",
        "boolean_exit",
    ],
)
def test_bandit_rejects_partial_or_inconsistent_results(scan_helpers, problem):
    report = source_report("MEDIUM")
    status = 1
    if problem == "errors":
        report["errors"] = [{"filename": "src/finsecure_pay/main.py", "reason": "syntax"}]
    elif problem == "missing_files":
        report["metrics"] = {"_totals": {}}
    elif problem == "bad_severity":
        report["results"][0]["issue_severity"] = "UNKNOWN"
    elif problem == "bad_confidence":
        report["results"][0]["issue_confidence"] = "UNKNOWN"
    elif problem == "missing_results":
        del report["results"]
    else:
        status = {"exit_zero_with_finding": 0, "exit_error": 2, "boolean_exit": True}[problem]
    with raises(ValueError):
        scan_helpers["bandit_result"](report, status, {"src/finsecure_pay/main.py"})


def audit_report(vulnerable: bool = False) -> dict:
    """A made-up advisory tests policy without installing a vulnerable package."""
    return {
        "dependencies": [
            {
                "name": "sample",
                "version": "1.0.0",
                "vulns": [{"id": "SYNTHETIC-ONLY"}] if vulnerable else [],
            }
        ],
        "fixes": [],
    }


def test_bandit_accepts_explicit_file_dot_prefix_without_broadening_scope(scan_helpers):
    report = source_report("LOW")
    report["metrics"]["./src/finsecure_pay/main.py"] = report["metrics"].pop(
        "src/finsecure_pay/main.py"
    )
    report["results"][0]["filename"] = "./src/finsecure_pay/main.py"
    result = scan_helpers["bandit_result"](report, 1, {"src/finsecure_pay/main.py"})
    assert result["LOW"] == 1
    assert result["blocking_findings"] == 0


def test_advisory_blocks_without_a_severity_or_available_fix(scan_helpers):
    assert scan_helpers["dependency_result"](audit_report(True), 1, {"sample": "1.0.0"}) == {
        "dependencies_audited": 1,
        "blocking_findings": 1,
    }


@mark.parametrize(
    "problem",
    [
        "skipped",
        "missing",
        "duplicate",
        "different_version",
        "missing_vulns",
        "missing_id",
        "exit_zero_with_finding",
        "exit_error",
        "automatic_fix",
        "boolean_exit",
    ],
)
def test_dependency_audit_fails_closed(scan_helpers, problem):
    report = audit_report(True)
    dependency = report["dependencies"][0]
    status = 1
    if problem == "skipped":
        dependency["skip_reason"] = "not found"
    elif problem == "missing":
        report["dependencies"] = []
    elif problem == "duplicate":
        report["dependencies"].append(deepcopy(dependency))
    elif problem == "different_version":
        dependency["version"] = "2.0.0"
    elif problem == "missing_vulns":
        del dependency["vulns"]
    elif problem == "missing_id":
        dependency["vulns"] = [{}]
    elif problem == "automatic_fix":
        report["fixes"] = [{"name": "sample"}]
    else:
        status = {"exit_zero_with_finding": 0, "exit_error": 2, "boolean_exit": True}[problem]
    with raises(ValueError):
        scan_helpers["dependency_result"](report, status, {"sample": "1.0.0"})


@mark.parametrize(
    "mode,exit_code",
    [
        ("pass", 0),
        ("low", 0),
        ("source_block", 1),
        ("dependency_block", 1),
        ("missing_report", 2),
        ("invalid_report", 2),
        ("timeout", 2),
        ("tool_error", 2),
        ("export_error", 2),
    ],
)
def test_scan_retains_reports_blocks_errors_and_never_retries(
    monkeypatch, tmp_path, mode, exit_code
):
    for directory in ["src/finsecure_pay", "scripts", "ops/jenkins"]:
        (tmp_path / directory).mkdir(parents=True)
    (tmp_path / "src/finsecure_pay/main.py").write_text('"""Synthetic source."""\n')
    (tmp_path / "uv.lock").write_text("synthetic lock\n")
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "bandit.json").write_text(dumps(source_report()))
    (reports / "unrelated.txt").write_text("retain")
    commands = []

    def scanner(arguments: list[str], **kwargs: Any) -> CompletedProcess:
        commands.append(arguments)
        assert 0 < kwargs["timeout"] <= 300
        kwargs["stdout"].write("Synthetic diagnostic\n")
        if "bandit" in arguments:
            assert "--ignore-nosec" in arguments
            if mode == "timeout":
                raise TimeoutExpired(arguments, kwargs["timeout"])
            if mode == "missing_report":
                return CompletedProcess(arguments, 0)
            if mode == "invalid_report":
                (reports / "bandit.json").write_text("not json")
                return CompletedProcess(arguments, 0)
            severity = "MEDIUM" if mode == "source_block" else "LOW" if mode == "low" else None
            (reports / "bandit.json").write_text(dumps(source_report(severity)))
            return CompletedProcess(arguments, int(severity is not None))
        if arguments[0] == "uv":
            assert all(
                flag in arguments
                for flag in ["--locked", "--offline", "--no-dev", "--no-emit-project"]
            )
            (reports / "runtime-requirements.txt").write_text("sample==1.0.0\n")
            return CompletedProcess(arguments, 2 if mode == "export_error" else 0)
        assert "pip_audit" in arguments
        assert arguments[arguments.index("--timeout") + 1] == "15"
        assert all(flag in arguments for flag in ["--disable-pip", "--no-deps", "--strict"])
        assert "--ignore-vuln" not in arguments and "--fix" not in arguments
        (reports / "pip-audit.json").write_text(dumps(audit_report(mode == "dependency_block")))
        return CompletedProcess(
            arguments, 2 if mode == "tool_error" else int(mode == "dependency_block")
        )

    monkeypatch.setattr("subprocess.run", scanner)
    helpers = run_path(str(Path(__file__).resolve().parents[2] / "scripts/security_scan.py"))
    assert helpers["scan"](tmp_path) == exit_code
    summary = loads((reports / "security-summary.json").read_text())
    assert summary["status"] == {0: "passed", 1: "blocked", 2: "error"}[exit_code]
    assert len(commands) == (2 if mode == "export_error" else 3)
    assert (reports / "unrelated.txt").read_text() == "retain"
    assert (reports / "security-tools.txt").exists()
    if mode == "missing_report":
        assert not (reports / "bandit.json").exists(), "A stale passing report must not survive"
    if mode == "source_block":
        assert summary["dependencies"]["status"] == "passed"


def test_exhausted_shared_budget_does_not_start_a_process(monkeypatch, scan_helpers, tmp_path):
    process = Mock()
    monkeypatch.setattr("subprocess.run", process)
    with raises(TimeoutError, match="budget exhausted"):
        scan_helpers["run_tool"](["unused"], tmp_path / "log", 0, tmp_path)
    process.assert_not_called()
