"""Public Jenkins cause/count/configuration contracts for the isolated demonstration."""

from pathlib import Path
from runpy import run_path
from typing import Any
from xml.etree.ElementTree import fromstring

from defusedxml.common import EntitiesForbidden
from pytest import MonkeyPatch, fixture, mark, raises


@fixture
def trigger_helpers(monkeypatch: MonkeyPatch) -> dict[str, Any]:
    directory = Path(__file__).resolve().parents[2] / "ops/jenkins"
    monkeypatch.syspath_prepend(str(directory))
    return run_path(str(directory / "verify_trigger.py"))


@mark.parametrize(
    "causes",
    [
        [],
        ["hudson.model.Cause$UserIdCause"],
        ["hudson.triggers.TimerTrigger$TimerTriggerCause"],
        ["hudson.triggers.SCMTrigger$SCMTriggerCause", "hudson.model.Cause$UserIdCause"],
    ],
)
def test_non_scm_or_mixed_causes_are_rejected(trigger_helpers, causes):
    build = {"actions": [{"causes": [{"_class": item} for item in causes]}]}
    with raises(RuntimeError, match="exclusively triggered"):
        trigger_helpers["require_scm_cause"](build)


def test_real_scm_cause_is_accepted(trigger_helpers):
    cause = {"_class": trigger_helpers["SCM_CAUSE"], "shortDescription": "Started by an SCM change"}
    assert trigger_helpers["require_scm_cause"]({"actions": [{}, {"causes": [cause]}]}) == [cause]


@mark.parametrize("counts", [(245, 1, 0), (246, 0, 0)])
def test_exact_controlled_junit_results_are_accepted(trigger_helpers, counts):
    passed, failed, skipped = counts
    trigger_helpers["require_test_counts"](
        {"passCount": passed, "failCount": failed, "skipCount": skipped}, passed, failed
    )


@mark.parametrize(
    "counts", [(245, True, 0), (245, "1", 0), (245, None, 0), (244, 1, 0), (245, 0, 1)]
)
def test_bad_or_unexpected_junit_counts_are_rejected(trigger_helpers, counts):
    passed, failed, skipped = counts
    with raises(RuntimeError, match="JUnit counts"):
        trigger_helpers["require_test_counts"](
            {"passCount": passed, "failCount": failed, "skipCount": skipped}, 245, 1
        )


def source_config(repository: str, credential: str = "") -> bytes:
    """Synthetic defining SCM configuration, without actual secrets."""
    return f"""<flow-definition>
<definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition">
<scm class="hudson.plugins.git.GitSCM"><userRemoteConfigs><hudson.plugins.git.UserRemoteConfig>
<url>{repository}</url><credentialsId>{credential}</credentialsId>
</hudson.plugins.git.UserRemoteConfig></userRemoteConfigs><branches><hudson.plugins.git.BranchSpec>
<name>*/main</name></hudson.plugins.git.BranchSpec></branches></scm><scriptPath>Jenkinsfile</scriptPath>
<lightweight>true</lightweight></definition></flow-definition>""".encode()


def test_demo_starts_manual_and_selects_only_its_own_trusted_branch(trigger_helpers):
    original = source_config(trigger_helpers["REPOSITORY"])
    root = fromstring(trigger_helpers["demo_job_xml"](original))
    assert (
        root.findtext(".//branches/hudson.plugins.git.BranchSpec/name")
        == "*/demo/step-04-04-ci-gate"
    )
    assert root.findtext("definition/scriptPath") == "Jenkinsfile"
    assert root.find(".//hudson.triggers.SCMTrigger") is None
    assert root.find("definition/script") is None
    assert (
        fromstring(original).findtext(".//branches/hudson.plugins.git.BranchSpec/name") == "*/main"
    )


@mark.parametrize(
    "declaration",
    [
        '<!ENTITY payload "synthetic">',
        '<!ENTITY payload SYSTEM "file:///nonexistent-synthetic-file">',
        '<!ENTITY payload SYSTEM "https://example.invalid/synthetic">',
    ],
)
def test_demo_configuration_rejects_xml_entities(trigger_helpers, declaration):
    payload = (
        f"<!DOCTYPE flow-definition [{declaration}]>"
        "<flow-definition><description>&payload;</description></flow-definition>"
    ).encode()
    with raises(EntitiesForbidden):
        trigger_helpers["demo_job_xml"](payload)


@mark.parametrize("change", ["repository", "credential"])
def test_other_repository_or_credentials_are_not_copied(trigger_helpers, change):
    repository = (
        "https://example.invalid/other.git"
        if change == "repository"
        else trigger_helpers["REPOSITORY"]
    )
    config = source_config(repository, "synthetic-credential-id" if change == "credential" else "")
    with raises(RuntimeError, match="Unexpected SCM"):
        trigger_helpers["demo_job_xml"](config)
