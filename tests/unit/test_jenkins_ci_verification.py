"""Regression tests for JUnit API interpretation and safe review-job configuration."""

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
