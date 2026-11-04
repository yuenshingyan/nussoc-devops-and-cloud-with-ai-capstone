from pathlib import Path
from runpy import run_path
from unittest.mock import Mock

from pytest import MonkeyPatch, fixture, mark, raises

ROOT = Path(__file__).resolve().parents[2]


@fixture
def helpers(monkeypatch: MonkeyPatch) -> dict:
    monkeypatch.syspath_prepend(str(ROOT / "ops/jenkins"))
    return run_path(str(ROOT / "ops/jenkins/release_job.py"))


def test_definition_stays_disabled_serialized_and_exact(helpers):
    script = "echo 'fixed <source> & no upstream execution'"
    helpers["verify_definition"](helpers["job_xml"](script).encode(), script)


@mark.parametrize(
    ("old", "new"),
    [
        ("<disabled>true", "<disabled>false"),
        ("<sandbox>false", "<sandbox>true"),
        ("<triggers/>", "<triggers><unreviewed/></triggers>"),
        ("<properties>", "<properties><unreviewed/>"),
        ("<script>fixed", "<script>changed"),
        (
            "DisableConcurrentBuildsJobProperty/>",
            "DisableConcurrentBuildsJobProperty><abortPrevious>true</abortPrevious></org.jenkinsci.plugins.workflow.job.properties.DisableConcurrentBuildsJobProperty>",
        ),
    ],
)
def test_rejects_definition_drift(helpers, old, new):
    xml = helpers["job_xml"]("fixed").replace(old, new)
    with raises(ValueError, match="DEFINITION_MISMATCH"):
        helpers["verify_definition"](xml.encode(), "fixed")


@mark.parametrize("status", [200, 401, 403, 500])
def test_existing_or_uncertain_job_prevents_creation(helpers, monkeypatch, status):
    state = helpers["create_disabled_job"].__globals__
    monkeypatch.setitem(state, "check_policy", Mock())
    client = Mock()
    folder = Mock()
    folder.json.return_value = {"description": state["DESCRIPTION"]}
    client.get.side_effect = [folder, Mock(status_code=status)]
    with raises(ValueError, match="EXISTS_OR_UNCERTAIN"):
        helpers["create_disabled_job"](client, "fixed")
    client.post.assert_not_called()


def test_missing_policy_prevents_job_creation(helpers, monkeypatch):
    state = helpers["create_disabled_job"].__globals__
    monkeypatch.setitem(state, "check_policy", Mock(side_effect=ValueError("missing")))
    client = Mock()
    with raises(ValueError, match="missing"):
        helpers["create_disabled_job"](client, "fixed")
    client.post.assert_not_called()


def test_cli_requires_approval(helpers, monkeypatch):
    monkeypatch.setattr("sys.argv", ["release_job.py"])
    create = Mock()
    monkeypatch.setitem(helpers["main"].__globals__, "create_disabled_job", create)
    with raises(SystemExit):
        helpers["main"]()
    create.assert_not_called()


def test_job_cannot_publish_or_execute_upstream_artifacts():
    script = (ROOT / "ops/jenkins/release-job.groovy").read_text()
    assert "timeout(time: 10, unit: 'MINUTES')" in script
    assert "RELEASE_DISABLED_ARTIFACT_TRANSFER_AND_DEPLOYMENT_NOT_IMPLEMENTED" in script
    assert "withCredentials(" not in script
    assert "node(" not in script
    assert "connection.instanceFollowRedirects = false" in script
    assert "Proxy.NO_PROXY" in script
    assert "RELEASE_UPSTREAM_CAUSE_REQUIRED" in script
