"""Save one operator-provided Docker Hub CI token outside the repository, without echo."""

from getpass import GetPassWarning, getpass
from os import O_CREAT, O_EXCL, O_NOFOLLOW, O_WRONLY, fchmod, fdopen, getuid, open
from pathlib import Path
from stat import S_IMODE, S_ISDIR
from sys import stdin
from warnings import catch_warnings, simplefilter


def validate_token(value: str) -> None:
    """Treat the token as opaque; reject whitespace/control characters without trimming."""
    if not 1 <= len(value) <= 4096 or any(not 33 <= ord(char) <= 126 for char in value):
        raise ValueError("Token must contain 1–4096 printable ASCII characters without whitespace")


def private_directory() -> Path:
    """Create only the fixed private directory; reject unsafe existing path components."""
    home = Path.home().resolve()
    paths = [home, home / ".config", home / ".config/finsecure-pay"]
    directory = home / ".config/finsecure-pay/release"
    for path in [*paths, directory]:
        if path != home:
            path.mkdir(mode=0o700, exist_ok=True)
        info = path.lstat()
        if not S_ISDIR(info.st_mode) or info.st_uid != getuid() or info.st_mode & 0o022:
            raise ValueError("Credential directories must be operator-owned, without symlinks")
    if S_IMODE(directory.stat().st_mode) != 0o700:
        raise ValueError("Existing release credential directory must have mode 0700")
    return directory


def save_token(value: str) -> None:
    """Create a mode-0600 file once; never overwrite or rotate an existing credential."""
    validate_token(value)
    path = private_directory() / "dockerhub-ci-token"
    descriptor = open(path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0o600)
    with fdopen(descriptor, "w", encoding="utf-8") as target:
        fchmod(target.fileno(), 0o600)
        target.write(value)


def main() -> int:
    """Require a terminal and fail before an unprotected getpass fallback can echo input."""
    if not stdin.isatty():
        print("A local interactive terminal is required; do not pass tokens as arguments or stdin")
        return 2
    try:
        with catch_warnings():
            simplefilter("error", GetPassWarning)
            value = getpass("Docker Hub CI token (hidden): ")
        save_token(value)
    except OSError, ValueError, GetPassWarning, EOFError:
        print("Token was not safely saved; check local file state. Existing files are not replaced")
        return 2
    except KeyboardInterrupt:
        print("Credential setup cancelled")
        return 130
    print("Token saved privately. Registry permissions and Jenkins import are not yet verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
