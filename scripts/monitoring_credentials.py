"""Initialize or verify one local Grafana password without printing its value."""

from argparse import ArgumentParser
from os import getuid, stat_result
from pathlib import Path
from re import fullmatch
from secrets import token_urlsafe
from stat import S_IMODE, S_ISDIR, S_ISREG
from subprocess import TimeoutExpired, run

GRAFANA_IMAGE = (
    "grafana/grafana:13.3.0@sha256:488984b716c0862639f91a698adbe2862677a5a07bad42da5f03f3030883b205"
)
GRAFANA_UID = 472
DATA_VOLUME = "finsecure-monitoring_grafana-data"


def secret_path() -> Path:
    """Return the fixed external credential path, never a caller-selected mount."""
    return Path.home().resolve() / ".config/finsecure-pay/monitoring/grafana-admin-password"


def private_directory(*, create: bool = False) -> Path:
    """Reject symlink components or foreign ownership without changing existing modes."""
    home = Path.home().resolve()
    directory = secret_path().parent
    for path in (home / ".config", home / ".config/finsecure-pay", directory):
        if create:
            path.mkdir(mode=0o700, exist_ok=True)
        info = path.lstat()
        if not S_ISDIR(info.st_mode) or info.st_uid != getuid() or info.st_mode & 0o022:
            raise RuntimeError("Credential directory must be operator-owned and not a symlink")
    if S_IMODE(directory.stat().st_mode) != 0o700:
        raise RuntimeError("Grafana credential directory must have mode 0700")
    return directory


def validate_secret_metadata(info: stat_result) -> None:
    """Require one regular, owner-readable file belonging to the service UID."""
    if (
        not S_ISREG(info.st_mode)
        or S_IMODE(info.st_mode) != 0o400
        or info.st_uid != GRAFANA_UID
        or info.st_gid != GRAFANA_UID
        or info.st_nlink != 1
    ):
        raise RuntimeError("Grafana password must be a single regular UID/GID 472 file, mode 0400")


def docker(arguments: list[str]) -> str:
    """Capture Docker output; never include its possibly sensitive content in failures."""
    try:
        result = run(["docker", *arguments], capture_output=True, text=True, timeout=30)
    except TimeoutExpired:
        raise RuntimeError("Owned Grafana credential operation timed out") from None
    if result.returncode:
        raise RuntimeError("Owned Grafana credential operation failed; do not expose its output")
    return result.stdout.strip()


def secret_helper(path: Path, *, change_owner: bool = False) -> str:
    """Own and remove a network-isolated helper; only the one password file is mounted."""
    # Image metadata is checked before a helper receives the secret mount.
    metadata = docker(
        ["image", "inspect", "--format", "{{.Config.User}} {{json .Config.Volumes}}", GRAFANA_IMAGE]
    )
    if metadata != "472 null":
        raise RuntimeError("Unexpected Grafana helper user or implicit volume configuration")
    mount = f"type=bind,source={path},target=/secret"
    arguments = [
        "create",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--label",
        "finsecure.purpose=grafana-credential",
        "--user",
        "0:0" if change_owner else "472:472",
        "--mount",
        mount if change_owner else mount + ",readonly",
    ]
    if change_owner:
        arguments.extend(
            ["--cap-add=CHOWN", "--entrypoint=/bin/chown", GRAFANA_IMAGE, "472:472", "/secret"]
        )
    else:
        arguments.extend(["--entrypoint=/bin/cat", GRAFANA_IMAGE, "/secret"])
    container = docker(arguments)
    if not fullmatch(r"[a-f0-9]{64}", container):
        raise RuntimeError("Unexpected owned helper container identifier")
    try:
        return docker(["start", "--attach", container])
    finally:
        docker(["rm", "--force", "--volumes", container])


def initialize_secret() -> Path:
    """Create once, refuse recovery/rotation guesses, and return only the nonsecret path."""
    private_directory(create=True)
    path = secret_path()
    if path.exists() or path.is_symlink():
        read_password()
        return path
    result = run(
        ["docker", "volume", "inspect", DATA_VOLUME],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode == 0:
        raise RuntimeError(
            "Existing Grafana data found; recover its credential instead of replacing it"
        )
    if "no such volume" not in result.stderr.lower():
        raise RuntimeError("Could not rule out existing Grafana data; no credential created")
    with path.open("x", encoding="utf-8") as target:
        path.chmod(0o400)
        target.write(token_urlsafe(32))
    secret_helper(path, change_owner=True)
    validate_secret_metadata(path.lstat())
    return path


def read_password() -> str:
    """Read only the existing owned credential into operator memory, without rotation."""
    private_directory()
    path = secret_path()
    validate_secret_metadata(path.lstat())
    value = secret_helper(path)
    if not fullmatch(r"[A-Za-z0-9_-]{43}", value):
        raise RuntimeError("Unexpected Grafana credential format; do not replace it automatically")
    return value


def main() -> None:
    """Print only a validated mount path; never offer a password-printing CLI."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "verify"])
    arguments = parser.parse_args()
    if arguments.action == "init":
        path = initialize_secret()
    else:
        read_password()
        path = secret_path()
    print(path)


if __name__ == "__main__":
    main()
