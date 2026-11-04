from getpass import GetPassWarning
from io import StringIO
from pathlib import Path
from runpy import run_path
from stat import S_IMODE
from warnings import warn

from pytest import MonkeyPatch, fixture, mark, raises

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/release_credentials.py"
HELPERS = run_path(str(SCRIPT))
save_token = HELPERS["save_token"]
validate_token = HELPERS["validate_token"]


def main() -> int:
    """Load the standalone CLI after patching its external terminal boundaries."""
    return run_path(str(SCRIPT))["main"]()


class Terminal:
    def isatty(self) -> bool:
        return True


@fixture
def private_home(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def token_path(home: Path) -> Path:
    return home / ".config/finsecure-pay/release/dockerhub-ci-token"


@mark.parametrize("value", ["x", "synthetic-token!", "x" * 4096])
def test_accepts_bounded_opaque_printable_tokens(value):
    validate_token(value)


@mark.parametrize(
    "value", ["", "x" * 4097, " x", "x ", "a\nb", "a\rb", "a\tb", "é", "\x00", "\x7f"]
)
def test_rejects_invalid_token_without_normalization(value):
    with raises(ValueError):
        validate_token(value)


def test_creates_private_file_with_exact_value(private_home):
    save_token("synthetic-token!")
    path = token_path(private_home)
    assert path.read_bytes() == b"synthetic-token!"
    assert S_IMODE(path.stat().st_mode) == 0o600
    assert S_IMODE(path.parent.stat().st_mode) == 0o700
    assert path.stat().st_nlink == 1


def test_rejects_existing_file_without_rotation(private_home):
    save_token("original-synthetic-token")
    with raises(FileExistsError):
        save_token("different-synthetic-token")
    assert token_path(private_home).read_text() == "original-synthetic-token"


def test_invalid_input_creates_no_directories(private_home):
    with raises(ValueError):
        save_token(" bad-token")
    assert not (private_home / ".config").exists()


@mark.parametrize(
    "component", [".config", ".config/finsecure-pay", ".config/finsecure-pay/release"]
)
def test_rejects_directory_symlinks(private_home, component):
    external = private_home / "external"
    external.mkdir(mode=0o700)
    path = private_home / component
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.symlink_to(external, target_is_directory=True)
    with raises(ValueError):
        save_token("synthetic-token")
    assert not list(external.iterdir())


@mark.parametrize("mode", [0o755, 0o750, 0o777])
def test_rejects_nonprivate_release_directory_without_chmod(private_home, mode):
    directory = token_path(private_home).parent
    directory.mkdir(parents=True, mode=mode)
    directory.chmod(mode)
    with raises(ValueError):
        save_token("synthetic-token")
    assert S_IMODE(directory.stat().st_mode) == mode
    assert not list(directory.iterdir())


def test_rejects_writable_ancestor(private_home):
    (private_home / ".config").mkdir(mode=0o700)
    (private_home / ".config").chmod(0o777)
    with raises(ValueError):
        save_token("synthetic-token")
    assert not token_path(private_home).exists()


@mark.parametrize("link_type", ["symlink", "hardlink"])
def test_rejects_existing_link_without_modifying_target(private_home, link_type):
    path = token_path(private_home)
    path.parent.mkdir(parents=True, mode=0o700)
    other = private_home / "existing"
    other.write_text("preserve-this-value")
    if link_type == "symlink":
        path.symlink_to(other)
    else:
        path.hardlink_to(other)
    with raises(FileExistsError):
        save_token("synthetic-token")
    assert other.read_text() == "preserve-this-value"


def test_noninteractive_input_is_rejected_before_prompt(private_home, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", StringIO("synthetic-token"))
    assert main() == 2
    assert not token_path(private_home).exists()
    assert "synthetic-token" not in capsys.readouterr().out


def test_interactive_setup_does_not_print_secret(private_home, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", Terminal())
    monkeypatch.setattr("getpass.getpass", lambda _: "synthetic-token")
    assert main() == 0
    assert token_path(private_home).read_text() == "synthetic-token"
    assert "synthetic-token" not in capsys.readouterr().out


def unsafe_prompt(prompt: str) -> str:
    warn("synthetic-secret-in-warning", GetPassWarning, stacklevel=1)
    raise AssertionError("An echoing fallback must not be reached")


def test_echo_fallback_fails_closed(private_home, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", Terminal())
    monkeypatch.setattr("getpass.getpass", unsafe_prompt)
    assert main() == 2
    assert not token_path(private_home).exists()
    captured = capsys.readouterr()
    assert "synthetic-secret" not in captured.out + captured.err


@mark.parametrize("error", [EOFError, KeyboardInterrupt, OSError])
def test_prompt_failures_are_safe(private_home, monkeypatch, capsys, error):
    def fail(prompt: str) -> str:
        raise error("synthetic-secret")

    monkeypatch.setattr("sys.stdin", Terminal())
    monkeypatch.setattr("getpass.getpass", fail)
    assert main() == (130 if error is KeyboardInterrupt else 2)
    assert not token_path(private_home).exists()
    captured = capsys.readouterr()
    assert "synthetic-secret" not in captured.out + captured.err
