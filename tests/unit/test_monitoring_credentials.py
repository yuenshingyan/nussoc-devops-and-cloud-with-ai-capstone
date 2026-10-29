"""Credential tests use real private temporary files and mock only Docker boundaries."""

from collections.abc import Iterator
from json import dumps
from os import getuid, stat_result
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
) -> Iterator[tuple[dict[str, Any], Mock, Path, dict]]:
    monkeypatch.setenv("HOME", str(tmp_path))
    state = {"volumes": {}, "value": "x" * 43, "metadata": "472 null"}

    def boundary(arguments: list[str], **kwargs: Any) -> CompletedProcess[str]:
        if arguments[1:3] == ["volume", "inspect"]:
            volume = state["volumes"].get(arguments[3])
            return CompletedProcess(
                arguments,
                0 if volume else 1,
                dumps([volume]) if volume else "",
                "" if volume else "no such volume",
            )
        if arguments[1:3] == ["volume", "create"]:
            state["volumes"][arguments[-1]] = {
                "Name": arguments[-1],
                "Labels": {"finsecure.purpose": "finsecure-pay-grafana-secrets"},
            }
        if arguments[1:3] == ["image", "inspect"]:
            return CompletedProcess(arguments, 0, state["metadata"], "")
        if arguments[1] == "create":
            return CompletedProcess(arguments, 0, "a" * 64, "")
        if arguments[1] == "start":
            if kwargs.get("input") is not None:
                state["value"] = kwargs["input"]
            else:
                return CompletedProcess(arguments, 0, state["value"], "")
        return CompletedProcess(arguments, 0, "", "")

    command = Mock(side_effect=boundary)
    monkeypatch.setattr("subprocess.run", command)
    helpers = run_path(
        str(Path(__file__).resolve().parents[2] / "scripts/monitoring_credentials.py")
    )
    yield (
        helpers,
        command,
        tmp_path / ".config/finsecure-pay/monitoring/grafana-admin-password",
        state,
    )


def metadata(mode: int = S_IFREG | 0o400, uid: int | None = None, links: int = 1) -> stat_result:
    """Construct public POSIX metadata without host root privileges."""
    return stat_result((mode, 1, 1, links, getuid() if uid is None else uid, 20, 43, 0, 0, 0))


def host_secret(helpers: dict, path: Path, value: str = "x" * 43) -> None:
    """Make a private synthetic credential through real filesystem operations."""
    helpers["private_directory"](create=True)
    path.write_text(value)
    path.chmod(0o400)


def volume_record(
    helpers: dict, state: dict, *, purpose: str = "finsecure-pay-grafana-secrets"
) -> None:
    """Supply simulated Docker volume metadata, not application internals."""
    name = helpers["SECRET_VOLUME"]
    state["volumes"][name] = {"Name": name, "Labels": {"finsecure.purpose": purpose}}


@mark.parametrize(
    "info",
    [
        metadata(mode=S_IFREG | 0o600),
        metadata(mode=S_IFREG | 0o444),
        metadata(mode=S_IFDIR | 0o400),
        metadata(mode=S_IFLNK | 0o400),
        metadata(uid=getuid() + 1),
        metadata(links=2),
    ],
)
def test_host_secret_rejects_unsafe_type_permissions_owner_or_links(credentials, info):
    helpers, command, _, _ = credentials
    with raises(RuntimeError, match="operator-owned regular"):
        helpers["validate_secret_metadata"](info)
    command.assert_not_called()


def test_host_secret_accepts_operator_owner_without_requiring_container_uid(credentials):
    helpers, _, path, _ = credentials
    host_secret(helpers, path)
    assert helpers["read_password"]() == "x" * 43
    helpers["validate_secret_metadata"](metadata())


def test_read_never_creates_missing_credential(credentials):
    helpers, command, path, _ = credentials
    with raises(FileNotFoundError):
        helpers["read_password"]()
    assert not path.parent.exists()
    command.assert_not_called()


@mark.parametrize(
    "component", [".config", ".config/finsecure-pay", ".config/finsecure-pay/monitoring"]
)
def test_initialization_rejects_symlink_directories(credentials, tmp_path, component):
    helpers, command, _, _ = credentials
    target = tmp_path / "unrelated"
    target.mkdir()
    link = tmp_path / component
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target, target_is_directory=True)
    with raises(RuntimeError, match="not a symlink"):
        helpers["initialize_secret"]()
    assert list(target.iterdir()) == []
    command.assert_not_called()


def test_nonprivate_directory_is_not_silently_chmodded(credentials):
    helpers, command, path, _ = credentials
    path.parent.mkdir(parents=True)
    path.parent.chmod(0o755)
    with raises(RuntimeError, match="0700"):
        helpers["initialize_secret"]()
    assert S_IMODE(path.parent.stat().st_mode) == 0o755
    command.assert_not_called()


def test_existing_data_without_secret_volume_is_not_reseeded(credentials):
    helpers, command, path, state = credentials
    name = helpers["DATA_VOLUME"]
    state["volumes"][name] = {"Name": name}
    with raises(RuntimeError, match="recover credentials"):
        helpers["initialize_secret"]()
    assert not path.exists()
    assert all(call.args[0][1:3] == ["volume", "inspect"] for call in command.call_args_list)


def test_daemon_failure_is_not_interpreted_as_missing_volume(credentials):
    helpers, command, path, _ = credentials
    command.side_effect = None
    command.return_value = CompletedProcess([], 1, "", "daemon unavailable")
    with raises(RuntimeError, match="Could not rule out"):
        helpers["initialize_secret"]()
    assert not path.exists()


def test_fresh_initialization_seeds_only_owned_volume_through_stdin(credentials):
    helpers, command, path, state = credentials
    assert helpers["initialize_secret"]() == path
    password = path.read_text()
    assert len(password) == 43 and state["value"] == password
    assert S_IMODE(path.stat().st_mode) == 0o400 and path.stat().st_uid == getuid()
    creations = [call.args[0] for call in command.call_args_list if call.args[0][1] == "create"]
    assert len(creations) == 2
    seed, verify = creations
    assert "--cap-add=CHOWN" in seed and seed[seed.index("--user") + 1] == "0:0"
    assert "--interactive" in seed
    assert verify[verify.index("--user") + 1] == "472:472"
    assert verify[verify.index("--mount") + 1].endswith(",readonly")
    assert not any(item.startswith("--cap-add") for item in verify)
    for arguments in creations:
        assert "--network=none" in arguments and "--read-only" in arguments
        assert "--cap-drop=ALL" in arguments
        assert "--security-opt=no-new-privileges:true" in arguments
        assert (
            "type=volume,source=" + helpers["SECRET_VOLUME"]
            in arguments[arguments.index("--mount") + 1]
        )
        assert not any("type=bind" in item or password in item for item in arguments)
    assert sum(call.kwargs.get("input") == password for call in command.call_args_list) == 1
    assert sum(call.args[0][1] == "rm" for call in command.call_args_list) == 2


def test_regression_preserves_host_password_from_failed_bind_mount_setup(credentials):
    helpers, _, path, state = credentials
    host_secret(helpers, path)
    inode = path.stat().st_ino
    helpers["initialize_secret"]()
    assert path.read_text() == state["value"] == "x" * 43
    assert path.stat().st_ino == inode and path.stat().st_uid == getuid()


def test_existing_matching_volume_is_read_only_without_rotation(credentials):
    helpers, command, path, state = credentials
    host_secret(helpers, path)
    volume_record(helpers, state)
    helpers["initialize_secret"]()
    assert path.read_text() == state["value"] == "x" * 43
    assert not any(call.args[0][1:3] == ["volume", "create"] for call in command.call_args_list)
    assert not any("--cap-add=CHOWN" in call.args[0] for call in command.call_args_list)
    assert all(call.kwargs.get("input") is None for call in command.call_args_list)


@mark.parametrize("problem", ["unowned", "mismatch", "missing_host", "bad_permissions"])
def test_existing_invalid_state_is_not_replaced(credentials, problem):
    helpers, command, path, state = credentials
    host_secret(helpers, path)
    volume_record(helpers, state, purpose="other" if problem == "unowned" else helpers["PURPOSE"])
    if problem == "mismatch":
        state["value"] = "y" * 43
    if problem == "missing_host":
        path.unlink()
    if problem == "bad_permissions":
        path.chmod(0o600)
    with raises((RuntimeError, FileNotFoundError)):
        helpers["initialize_secret"]()
    assert not any(call.args[0][1:3] == ["volume", "create"] for call in command.call_args_list)
    assert not any("--cap-add=CHOWN" in call.args[0] for call in command.call_args_list)
    if problem == "missing_host":
        assert not path.exists()
    else:
        assert path.read_text() == "x" * 43


@mark.parametrize("value", ["admin", "x" * 42, "x" * 44, "x" * 42 + "!", "x" * 43 + "\n"])
def test_bad_host_format_never_seeds_a_volume(credentials, value):
    helpers, command, path, _ = credentials
    host_secret(helpers, path, value)
    with raises(RuntimeError, match="do not replace"):
        helpers["initialize_secret"]()
    assert path.read_text() == value
    assert not any(call.args[0][1:3] == ["volume", "create"] for call in command.call_args_list)


@mark.parametrize("image_metadata", ["0 null", '472 {"/data":{}}'])
def test_unexpected_helper_image_never_receives_secret_mount(credentials, image_metadata):
    helpers, command, path, state = credentials
    host_secret(helpers, path)
    volume_record(helpers, state)
    state["metadata"] = image_metadata
    with raises(RuntimeError, match="Unexpected Grafana helper"):
        helpers["verify_secret"]()
    assert not any(call.args[0][1] == "create" for call in command.call_args_list)


@mark.parametrize("timeout", [False, True])
def test_failed_helper_is_removed_without_exposing_output(credentials, timeout):
    helpers, command, path, state = credentials
    host_secret(helpers, path)
    volume_record(helpers, state)
    original = command.side_effect

    def fail(arguments: list[str], **kwargs: Any) -> CompletedProcess[str]:
        if arguments[1] == "start":
            if timeout:
                raise TimeoutExpired("docker", 30, output="private-output")
            return CompletedProcess(arguments, 1, "private-output", "private-output")
        return original(arguments, **kwargs)

    command.side_effect = fail
    with raises(RuntimeError) as caught:
        helpers["verify_secret"]()
    assert "private-output" not in str(caught.value)
    assert command.call_args.args[0] == ["docker", "rm", "--force", "--volumes", "a" * 64]


def test_volume_reader_checks_private_metadata_and_rejects_symlinks(credentials):
    helpers, _, _, _ = credentials
    script = helpers["READ_SECRET"]
    assert "472:472:700" in script and "472:472:400:1" in script
    assert "test ! -L /out;" in script and "test ! -L /out/grafana-admin-password;" in script
    assert "test -f /out/grafana-admin-password" in script
    assert 'test -z "$(ls -A /out)"' in helpers["SEED_SECRET"]
