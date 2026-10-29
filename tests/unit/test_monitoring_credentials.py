"""Exercise credential boundaries with real temporary files and mocked Docker only."""

from collections.abc import Iterator
from os import stat_result
from pathlib import Path
from runpy import run_path
from stat import S_IFDIR, S_IFLNK, S_IFREG, S_IMODE
from subprocess import CompletedProcess, TimeoutExpired
from typing import Any
from unittest.mock import Mock

from pytest import MonkeyPatch, fixture, mark, raises


@fixture
def credentials(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> Iterator[tuple[dict[str, Any], Mock, Path]]:
    monkeypatch.setenv("HOME", str(tmp_path))
    command = Mock()
    monkeypatch.setattr("subprocess.run", command)
    helpers = run_path(
        str(Path(__file__).resolve().parents[2] / "scripts/monitoring_credentials.py")
    )
    yield helpers, command, tmp_path / ".config/finsecure-pay/monitoring/grafana-admin-password"


def metadata(
    mode: int = S_IFREG | 0o400, uid: int = 472, gid: int = 472, links: int = 1
) -> stat_result:
    """Construct public POSIX metadata without requiring host root privileges."""
    return stat_result((mode, 1, 1, links, uid, gid, 43, 0, 0, 0))


def result(output: str = "", code: int = 0, error: str = "") -> CompletedProcess[str]:
    """Represent a subprocess boundary result without starting Docker."""
    return CompletedProcess([], code, output, error)


def service_owned_file(monkeypatch: MonkeyPatch, path: Path) -> None:
    """Simulate Docker's ownership change only in lstat, retaining real file contents/modes."""
    original = Path.lstat

    def lstat(actual: Path) -> stat_result:
        value = original(actual)
        if actual == path:
            fields = list(value)
            fields[4:6] = [472, 472]
            return stat_result(fields)
        return value

    monkeypatch.setattr(Path, "lstat", lstat)


@mark.parametrize(
    "info",
    [
        metadata(mode=S_IFREG | 0o600),
        metadata(mode=S_IFREG | 0o444),
        metadata(mode=S_IFDIR | 0o400),
        metadata(mode=S_IFLNK | 0o400),
        metadata(uid=0),
        metadata(gid=0),
        metadata(links=2),
    ],
)
def test_secret_rejects_unsafe_permissions_type_ownership_or_links(credentials, info):
    helpers, command, _ = credentials
    with raises(RuntimeError, match="single regular"):
        helpers["validate_secret_metadata"](info)
    command.assert_not_called()


def test_secret_accepts_only_expected_regular_metadata(credentials):
    helpers, _, _ = credentials
    helpers["validate_secret_metadata"](metadata())


def test_read_does_not_create_a_missing_credential(credentials):
    helpers, command, path = credentials
    with raises(FileNotFoundError):
        helpers["read_password"]()
    assert not path.parent.exists()
    command.assert_not_called()


@mark.parametrize(
    "component", [".config", ".config/finsecure-pay", ".config/finsecure-pay/monitoring"]
)
def test_initialization_rejects_symlink_directories(credentials, tmp_path, component):
    helpers, command, _ = credentials
    target = tmp_path / "unrelated"
    target.mkdir()
    link = tmp_path / component
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target, target_is_directory=True)
    with raises(RuntimeError, match="not a symlink"):
        helpers["initialize_secret"]()
    assert list(target.iterdir()) == []
    command.assert_not_called()


def test_initialization_rejects_nonprivate_directory_without_chmod(credentials):
    helpers, command, path = credentials
    path.parent.mkdir(parents=True)
    path.parent.chmod(0o755)
    with raises(RuntimeError, match="0700"):
        helpers["initialize_secret"]()
    assert S_IMODE(path.parent.stat().st_mode) == 0o755
    command.assert_not_called()


@mark.parametrize("response", [result("[]"), result(code=1, error="daemon unavailable")])
def test_initialization_does_not_guess_credentials_for_existing_or_unknown_data(
    credentials, response
):
    helpers, command, path = credentials
    command.return_value = response
    with raises(RuntimeError):
        helpers["initialize_secret"]()
    assert not path.exists()
    assert command.call_count == 1


def test_initialization_creates_once_with_chown_only_and_no_secret_in_arguments(
    credentials, monkeypatch
):
    helpers, command, path = credentials
    service_owned_file(monkeypatch, path)
    command.side_effect = [
        result(code=1, error="no such volume"),
        result("472 null"),
        result("a" * 64),
        result(),
        result(),
    ]
    assert helpers["initialize_secret"]() == path
    assert S_IMODE(path.stat().st_mode) == 0o400
    # Host ownership is simulated, but content generation and private writes are real.
    value = path.read_text()
    assert len(value) == 43
    calls = command.call_args_list
    creation = calls[2].args[0]
    assert "--cap-add=CHOWN" in creation and "--user" in creation
    assert creation[creation.index("--user") + 1] == "0:0"
    assert "--entrypoint=/bin/chown" in creation
    assert "--network=none" in creation and "--read-only" in creation
    assert "--cap-drop=ALL" in creation and "--security-opt=no-new-privileges:true" in creation
    assert sum("type=bind" in item for item in creation) == 1
    assert not any(value in str(call) for call in calls)
    assert calls[-1].args[0] == ["docker", "rm", "--force", "--volumes", "a" * 64]


def test_existing_credential_is_read_only_and_not_regenerated(credentials, monkeypatch):
    helpers, command, path = credentials
    helpers["private_directory"](create=True)
    path.write_text("x" * 43)
    path.chmod(0o400)
    service_owned_file(monkeypatch, path)
    command.side_effect = [result("472 null"), result("a" * 64), result("x" * 43), result()]
    assert helpers["initialize_secret"]() == path
    assert path.read_text() == "x" * 43
    creation = command.call_args_list[1].args[0]
    assert "--entrypoint=/bin/cat" in creation
    assert creation[creation.index("--user") + 1] == "472:472"
    assert creation[creation.index("--mount") + 1].endswith(",readonly")
    assert not any(item.startswith("--cap-add") for item in creation)


@mark.parametrize("value", ["admin", "x" * 42, "x" * 44, "x" * 42 + "!"])
def test_malformed_existing_credential_fails_without_replacement(credentials, monkeypatch, value):
    helpers, command, path = credentials
    helpers["private_directory"](create=True)
    path.write_text(value)
    path.chmod(0o400)
    service_owned_file(monkeypatch, path)
    command.side_effect = [result("472 null"), result("a" * 64), result(value), result()]
    with raises(RuntimeError, match="do not replace"):
        helpers["initialize_secret"]()
    assert path.read_text() == value


@mark.parametrize("image_metadata", ["0 null", '472 {"/data":{}}'])
def test_unexpected_helper_image_metadata_receives_no_secret_mount(credentials, image_metadata):
    helpers, command, path = credentials
    command.return_value = result(image_metadata)
    with raises(RuntimeError, match="Unexpected Grafana helper"):
        helpers["secret_helper"](path)
    assert command.call_count == 1
    assert str(path) not in str(command.call_args)


@mark.parametrize(
    "failure",
    [result(code=1, error="private-output"), TimeoutExpired("docker", 30, output="private-output")],
)
def test_helper_cleanup_runs_on_failure_without_exposing_output(credentials, failure):
    helpers, command, path = credentials
    command.side_effect = [result("472 null"), result("a" * 64), failure, result()]
    with raises(RuntimeError) as error:
        helpers["secret_helper"](path)
    assert "private-output" not in str(error.value)
    assert command.call_args.args[0] == ["docker", "rm", "--force", "--volumes", "a" * 64]
