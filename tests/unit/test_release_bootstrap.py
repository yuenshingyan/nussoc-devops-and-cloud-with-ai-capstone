from pathlib import Path
from runpy import run_path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, Mock

from pytest import MonkeyPatch, fixture, mark, raises

ROOT = Path(__file__).resolve().parents[2]


@fixture
def helpers(monkeypatch: MonkeyPatch) -> dict:
    monkeypatch.syspath_prepend(str(ROOT / "ops/jenkins"))
    return run_path(str(ROOT / "ops/jenkins/release_bootstrap.py"))


@mark.parametrize("value", ["", "x" * 64, "a" * 63, "a" * 65, "a" * 64 + "\n"])
def test_rejects_invalid_remoting_identity_before_commands(helpers, monkeypatch, value):
    command = Mock()
    monkeypatch.setitem(helpers["initialize_secret"].__globals__, "run", command)
    with raises(ValueError):
        helpers["initialize_secret"](value)
    command.assert_not_called()


@mark.parametrize(("code", "stderr"), [(0, ""), (1, "daemon unavailable")])
def test_existing_or_uncertain_volume_is_not_replaced(helpers, monkeypatch, code, stderr):
    state = helpers["initialize_secret"].__globals__
    monkeypatch.setitem(state, "run", Mock(return_value=CompletedProcess([], code, "[]", stderr)))
    command = Mock()
    monkeypatch.setitem(state, "command", command)
    with raises(RuntimeError):
        helpers["initialize_secret"]("a" * 64)
    command.assert_not_called()


@mark.parametrize("fail_seed", [False, True])
def test_seed_uses_stdin_and_removes_only_owned_helper(helpers, monkeypatch, fail_seed):
    state = helpers["initialize_secret"].__globals__
    monkeypatch.setitem(
        state, "run", Mock(return_value=CompletedProcess([], 1, "", "no such volume"))
    )

    def boundary(arguments: list[str], **kwargs: object) -> str:
        if arguments[:2] == ["docker", "create"]:
            return "c" * 64
        if fail_seed and arguments[:2] == ["docker", "start"]:
            raise RuntimeError("Synthetic failure")
        return ""

    command = Mock(side_effect=boundary)
    monkeypatch.setitem(state, "command", command)
    if fail_seed:
        with raises(RuntimeError):
            helpers["initialize_secret"]("a" * 64)
    else:
        helpers["initialize_secret"]("a" * 64)
    calls = command.call_args_list
    assert calls[-1].args[0] == ["docker", "rm", "--force", "--volumes", "c" * 64]
    assert calls[2].kwargs["input_text"] == "a" * 64
    assert all("a" * 64 not in " ".join(call.args[0]) for call in calls)
    creation = calls[1].args[0]
    assert "--cap-add=CHOWN" in creation
    assert "--cap-add=DAC_OVERRIDE" not in creation
    assert "--network=none" in creation


def test_missing_scheduling_policy_prevents_bootstrap_mutations(helpers, monkeypatch):
    state = helpers["start"].__globals__
    monkeypatch.setitem(state, "admin_password", Mock(return_value="synthetic"))
    monkeypatch.setitem(state, "Client", MagicMock())
    monkeypatch.setitem(state, "check_policy", Mock(side_effect=ValueError("POLICY_MISSING")))
    command = Mock()
    seed = Mock()
    monkeypatch.setitem(state, "command", command)
    monkeypatch.setitem(state, "initialize_secret", seed)
    with raises(ValueError, match="POLICY_MISSING"):
        helpers["start"]()
    command.assert_not_called()
    seed.assert_not_called()


def test_cli_requires_explicit_approval(helpers, monkeypatch):
    monkeypatch.setattr("sys.argv", ["release_bootstrap.py"])
    start = Mock()
    monkeypatch.setitem(helpers["main"].__globals__, "start", start)
    with raises(SystemExit) as error:
        helpers["main"]()
    assert error.value.code == 2
    start.assert_not_called()
