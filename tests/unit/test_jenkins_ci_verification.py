"""Regression tests for JUnit API interpretation and safe review-job configuration."""

from json import dumps
from pathlib import Path
from runpy import run_path
from typing import Any
from xml.etree.ElementTree import fromstring

from pytest import MonkeyPatch, fixture, mark, raises


@fixture
def ci_helpers(monkeypatch: MonkeyPatch) -> dict[str, Any]:
    directory = Path(__file__).resolve().parents[2] / "ops/jenkins"
    monkeypatch.syspath_prepend(str(directory))
    return run_path(str(directory / "verify_ci.py"))


def test_junit_counts_use_the_published_api_fields(ci_helpers):
    report = {"passCount": 221, "failCount": 0, "skipCount": 0}
    assert ci_helpers["require_passing_tests"](report, 221) == 221


@mark.parametrize(
    "report",
    [
        {"passCount": 220, "failCount": 1, "skipCount": 0},
        {"passCount": 220, "failCount": 0, "skipCount": 1},
        {"passCount": 220, "failCount": 0, "skipCount": 0},
    ],
)
def test_unexpected_junit_results_are_not_accepted(ci_helpers, report):
    with raises(RuntimeError, match="expected passing suite"):
        ci_helpers["require_passing_tests"](report, 221)


@mark.parametrize("count", [None, True, "221", -1])
def test_invalid_junit_counts_are_not_coerced(ci_helpers, count):
    with raises(RuntimeError, match="missing or invalid counts"):
        ci_helpers["require_passing_tests"](
            {"passCount": count, "failCount": 0, "skipCount": 0}, 221
        )


def test_review_job_is_sandboxed_manual_and_preserves_script(ci_helpers):
    script = "echo('<synthetic> & safe')"
    root = fromstring(ci_helpers["job_xml"](script, "Synthetic review"))
    assert root.findtext("definition/script") == script
    assert root.findtext("definition/sandbox") == "true"
    assert root.findtext("description") == "Synthetic review"
    assert len(root.find("triggers")) == 0


def test_security_reports_are_absent_after_an_earlier_test_failure(ci_helpers, tmp_path):
    assert ci_helpers["require_security_reports"](tmp_path, set(), True) is None
    with raises(RuntimeError, match="after the injected"):
        ci_helpers["require_security_reports"](tmp_path, {"reports/bandit.json"}, True)


@mark.parametrize("problem", [None, "missing", "incomplete", "blocking", "boolean", "lock"])
def test_security_verification_requires_complete_pass_and_matching_lock(
    ci_helpers, tmp_path, problem
):
    reports = tmp_path / "reports"
    reports.mkdir()
    digest = "a" * 64
    record = {
        "status": "passed",
        "lock_sha256": digest,
        "bandit": {"status": "passed", "blocking_findings": 0},
        "dependencies": {"status": "passed", "blocking_findings": 0},
    }
    paths = ci_helpers["SECURITY_ARTIFACTS"].copy()
    if problem == "missing":
        paths.remove("reports/bandit.json")
    elif problem == "incomplete":
        record["status"] = "incomplete"
    elif problem in {"blocking", "boolean"}:
        record["bandit"]["blocking_findings"] = 1 if problem == "blocking" else False
    elif problem == "lock":
        record["lock_sha256"] = "b" * 64
    (reports / "security-summary.json").write_text(dumps(record))
    (reports / "build-metadata.txt").write_text(digest + "  uv.lock\n")
    if problem is None:
        assert ci_helpers["require_security_reports"](tmp_path, paths, False) == record
    else:
        with raises(RuntimeError):
            ci_helpers["require_security_reports"](tmp_path, paths, False)
