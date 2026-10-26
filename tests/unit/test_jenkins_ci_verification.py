"""Regression tests for JUnit API interpretation and safe review-job configuration."""

from hashlib import sha256
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


def test_image_reports_must_not_exist_after_an_earlier_failed_stage(ci_helpers, tmp_path):
    assert ci_helpers["require_image_security_reports"](tmp_path, set(), True, "a" * 40) is None
    with raises(RuntimeError):
        ci_helpers["require_image_security_reports"](
            tmp_path, {"reports/trivy.json"}, True, "a" * 40
        )


@mark.parametrize(
    "problem",
    [
        None,
        "missing",
        "blocked",
        "incomplete",
        "boolean",
        "revision",
        "eol",
        "cleanup",
        "hashes",
        "modified-report",
        "archive",
        "lock",
        "image",
    ],
)
def test_image_verification_requires_bound_reports_and_archive(ci_helpers, tmp_path, problem):
    reports = tmp_path / "reports"
    reports.mkdir()
    (tmp_path / "images").mkdir()
    archive = tmp_path / "images/finsecure-pay.tar.gz"
    archive.write_bytes(b"synthetic archive")
    paths = ci_helpers["IMAGE_SECURITY_ARTIFACTS"].copy()
    for name in paths:
        (tmp_path / name).write_text("synthetic diagnostic")
    (reports / "trivy.json").write_text(dumps({"Metadata": {"ImageID": "sha256:test"}}))
    record = {
        "status": "passed",
        "source_revision": "a" * 40,
        "blocking_findings": 0,
        "end_of_life": False,
        "temporary_cache_removed": True,
        "image_id": "sha256:test",
        "archive_sha256": sha256(archive.read_bytes()).hexdigest(),
        "lock_sha256": "b" * 64,
        "report_sha256": {
            Path(name).name: sha256((tmp_path / name).read_bytes()).hexdigest()
            for name in paths
            if not name.endswith("image-security-summary.json")
        },
    }
    (reports / "build-metadata.txt").write_text("b" * 64 + "  uv.lock\n")
    if problem == "missing":
        paths.remove("reports/trivy.json")
    elif problem in {"blocked", "incomplete"}:
        record["status"] = problem
    elif problem == "boolean":
        record["blocking_findings"] = False
    elif problem == "revision":
        record["source_revision"] = "c" * 40
    elif problem == "eol":
        record["end_of_life"] = True
    elif problem == "cleanup":
        record["temporary_cache_removed"] = False
    elif problem == "hashes":
        record["report_sha256"].pop("trivy.json")
    elif problem == "modified-report":
        (reports / "trivy.txt").write_text("changed")
    elif problem == "archive":
        archive.write_bytes(b"changed")
    elif problem == "lock":
        record["lock_sha256"] = "c" * 64
    elif problem == "image":
        record["image_id"] = "sha256:other"
    (reports / "image-security-summary.json").write_text(dumps(record))
    if problem is None:
        assert (
            ci_helpers["require_image_security_reports"](tmp_path, paths, False, "a" * 40) == record
        )
    else:
        with raises(RuntimeError):
            ci_helpers["require_image_security_reports"](tmp_path, paths, False, "a" * 40)
