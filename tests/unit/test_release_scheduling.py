from pathlib import Path
from runpy import run_path
from unittest.mock import Mock

from pytest import MonkeyPatch, mark, raises

ROOT = Path(__file__).resolve().parents[2]


def test_controller_installs_administrator_owned_startup_policy():
    dockerfile = (ROOT / "ops/jenkins/controller.Dockerfile").read_text()
    assert "!release-policy.groovy" in (ROOT / "ops/jenkins/.dockerignore").read_text().splitlines()
    assert "COPY --chown=jenkins:jenkins release-policy.groovy " in dockerfile
    assert "init.groovy.d/finsecure-release-policy.groovy.override" in dockerfile
    policy = (ROOT / "ops/jenkins/release-policy.groovy").read_text()
    assert "item.task.getOwnerTask()" in policy
    assert "owner instanceof Job" in policy
    assert "Queue.FlyweightTask" in policy
    assert "FINSECURE_RELEASE_OWNER_UNAVAILABLE" in policy
    assert "Collections.unmodifiableSet" in policy
    assert "'finsecure-release/verify-boundaries'" in policy
    assert "'finsecure-release/verify-scheduling'" in policy
    assert "'finsecure-release/delivery'" in policy
    assert "POLICY_VERSION = '2'" in policy


@mark.parametrize(
    "text",
    ["", "Exception: initialization failed", "FINSECURE_RELEASE_POLICY_VERIFIED\nunexpected"],
)
def test_policy_preflight_rejects_missing_or_ambiguous_guard(monkeypatch: MonkeyPatch, text):
    monkeypatch.syspath_prepend(str(ROOT / "ops/jenkins"))
    helpers = run_path(str(ROOT / "ops/jenkins/verify_release.py"))
    client = Mock()
    client.get.return_value.json.return_value = {"crumbRequestField": "crumb", "crumb": "synthetic"}
    client.post.return_value.text = text
    with raises(ValueError, match="SCHEDULING_POLICY_NOT_VERIFIED"):
        helpers["check_policy"](client)


def test_policy_preflight_accepts_verified_marker(monkeypatch: MonkeyPatch):
    monkeypatch.syspath_prepend(str(ROOT / "ops/jenkins"))
    helpers = run_path(str(ROOT / "ops/jenkins/verify_release.py"))
    client = Mock()
    client.get.return_value.json.return_value = {"crumbRequestField": "crumb", "crumb": "synthetic"}
    client.post.return_value.text = "FINSECURE_RELEASE_POLICY_VERIFIED\n"
    helpers["check_policy"](client)
    client.post.return_value.raise_for_status.assert_called_once()
