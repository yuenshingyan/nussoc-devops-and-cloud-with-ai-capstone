from collections.abc import Iterator
from contextlib import contextmanager
from json import loads
from pathlib import Path
from runpy import run_path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import Mock

from pytest import MonkeyPatch, fixture, mark, raises

ROOT = Path(__file__).resolve().parents[2]


@fixture
def helpers(monkeypatch: MonkeyPatch) -> dict:
    monkeypatch.syspath_prepend(str(ROOT))
    return run_path(str(ROOT / "ops/jenkins/release_probe.py"))


@mark.parametrize("mode", [0o400, 0o600])
def test_accepts_private_binding(helpers, tmp_path, mode):
    path = tmp_path / "credential"
    path.write_bytes(b"synthetic-value")
    path.chmod(mode)
    assert helpers["private_binding"](path) == b"synthetic-value"


@mark.parametrize("mode", [0o644, 0o640])
def test_rejects_readable_binding(helpers, tmp_path, mode):
    path = tmp_path / "credential"
    path.write_bytes(b"synthetic-value")
    path.chmod(mode)
    with raises(ValueError):
        helpers["private_binding"](path)


def test_rejects_secret_contents_in_environment(helpers, tmp_path, monkeypatch):
    path = tmp_path / "credential"
    path.write_bytes(b"synthetic-value")
    path.chmod(0o400)
    monkeypatch.setenv("BAD_SECRET", "synthetic-value")
    with raises(ValueError, match="SECRET_CONTENT_IN_ENVIRONMENT"):
        helpers["private_binding"](path)


def test_private_client_state_stays_in_workspace_and_is_removed(helpers, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "credential"
    path.write_bytes(b"synthetic-value")
    path.chmod(0o400)
    observed = []

    def prepare(key: Path, directory: Path) -> dict:
        assert key == path
        assert directory.parent == tmp_path
        assert directory.stat().st_mode & 0o777 == 0o700
        observed.append(directory)
        return {}

    state = helpers["cluster"].__globals__

    @contextmanager
    def inherited_directory(**kwargs: Any) -> Iterator[str]:
        with TemporaryDirectory(**kwargs) as name:
            Path(name).chmod(0o2700)
            yield name

    monkeypatch.setitem(state, "TemporaryDirectory", inherited_directory)
    monkeypatch.setitem(state, "prepare_client", prepare)
    monkeypatch.setitem(
        state,
        "run",
        Mock(
            side_effect=[
                CompletedProcess([], 0, '{"status":{"availableReplicas":2}}', ""),
                CompletedProcess([], 1, "", "Forbidden: cannot list resource"),
            ]
        ),
    )
    assert helpers["cluster"](path)["status"] == "verified"
    assert len(observed) == 1 and not observed[0].exists()


@mark.parametrize(
    ("message", "code"),
    [
        ("UNSAFE_CLIENT_DIRECTORY", "UNSAFE_CLIENT_DIRECTORY"),
        ("sensitive-provider-value", "UNEXPECTED_FAILURE"),
    ],
)
def test_only_fixed_failure_codes_are_reported(helpers, tmp_path, monkeypatch, message, code):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["release_probe.py", "cluster"])
    monkeypatch.setenv("RELEASE_CREDENTIAL_FILE", "/private/credential")
    monkeypatch.setitem(
        helpers["main"].__globals__, "cluster", Mock(side_effect=ValueError(message))
    )
    assert helpers["main"]() == 2
    assert loads((tmp_path / "reports/cluster-probe.json").read_text())["failure_code"] == code


@mark.parametrize("action", ["registry", "cluster"])
def test_provider_error_details_are_not_reported(helpers, tmp_path, monkeypatch, capsys, action):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["release_probe.py", action])
    monkeypatch.setenv("RELEASE_CREDENTIAL_FILE", "/private/credential")
    monkeypatch.setitem(
        helpers["main"].__globals__,
        action,
        Mock(side_effect=RuntimeError("sensitive-provider-details")),
    )
    assert helpers["main"]() == 2
    assert "sensitive-provider-details" not in capsys.readouterr().out
    assert (
        "sensitive-provider-details"
        not in (tmp_path / "reports" / (action + "-probe.json")).read_text()
    )
