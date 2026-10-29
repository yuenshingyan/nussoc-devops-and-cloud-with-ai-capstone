"""Manage one private host credential and its owned, read-only Grafana secret volume."""

from argparse import ArgumentParser
from hmac import compare_digest
from json import loads
from os import getuid, stat_result
from pathlib import Path
from re import fullmatch
from secrets import token_urlsafe
from stat import S_IMODE, S_ISDIR, S_ISREG
from subprocess import TimeoutExpired, run

GRAFANA_IMAGE = (
    "grafana/grafana:13.3.0@sha256:488984b716c0862639f91a698adbe2862677a5a07bad42da5f03f3030883b205"
)
DATA_VOLUME = "finsecure-monitoring_grafana-data"
SECRET_VOLUME = "finsecure-monitoring-grafana-secrets"
PURPOSE = "finsecure-pay-grafana-secrets"
READ_SECRET = (
    "set -eu; test ! -L /out; test -d /out; "
    'test "$(stat -c %u:%g:%a /out)" = 472:472:700; '
    "test ! -L /out/grafana-admin-password; test -f /out/grafana-admin-password; "
    'test "$(stat -c %u:%g:%a:%h /out/grafana-admin-password)" = 472:472:400:1; '
    "cat /out/grafana-admin-password"
)
SEED_SECRET = (
    'set -eu; test -z "$(ls -A /out)"; umask 077; '
    "cat > /out/grafana-admin-password; chmod 400 /out/grafana-admin-password; "
    "chmod 700 /out; chown 472:472 /out/grafana-admin-password; chown 472:472 /out"
)


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
    """Require one private, regular host file owned by the current operator."""
    if (
        not S_ISREG(info.st_mode)
        or S_IMODE(info.st_mode) != 0o400
        or info.st_uid != getuid()
        or info.st_nlink != 1
    ):
        raise RuntimeError(
            "Grafana host password must be one operator-owned regular file, mode 0400"
        )


def docker(arguments: list[str], *, input_text: str | None = None) -> str:
    """Use bounded subprocesses; keep output and stdin secrets out of exceptions."""
    try:
        result = run(
            ["docker", *arguments], input=input_text, capture_output=True, text=True, timeout=30
        )
    except TimeoutExpired:
        raise RuntimeError("Owned Grafana credential operation timed out") from None
    if result.returncode:
        raise RuntimeError("Owned Grafana credential operation failed; do not expose its output")
    return result.stdout


def inspect_volume(name: str) -> dict | None:
    """Distinguish absent volumes from daemon failures; never infer absence from any error."""
    try:
        result = run(
            ["docker", "volume", "inspect", name], capture_output=True, text=True, timeout=30
        )
    except TimeoutExpired:
        raise RuntimeError("Could not inspect Grafana volume state") from None
    if result.returncode:
        if "no such volume" in result.stderr.lower():
            return None
        raise RuntimeError("Could not rule out existing Grafana volume state")
    values = loads(result.stdout)
    if len(values) != 1 or values[0].get("Name") != name:
        raise RuntimeError("Unexpected Grafana volume identity")
    return values[0]


def require_owned_volume() -> None:
    """Refuse a missing or unlabelled secret volume without changing it."""
    info = inspect_volume(SECRET_VOLUME)
    if info is None or (info.get("Labels") or {}).get("finsecure.purpose") != PURPOSE:
        raise RuntimeError("Grafana secret volume missing or not owned; do not replace it")


def secret_helper(*, seed: str | None = None) -> str:
    """Own a helper mounting only the labelled volume; seed only an empty new volume."""
    require_owned_volume()
    metadata = docker(
        ["image", "inspect", "--format", "{{.Config.User}} {{json .Config.Volumes}}", GRAFANA_IMAGE]
    ).strip()
    if metadata != "472 null":
        raise RuntimeError("Unexpected Grafana helper user or implicit volume configuration")
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
        "0:0" if seed is not None else "472:472",
        "--mount",
        f"type=volume,source={SECRET_VOLUME},target=/out"
        + ("" if seed is not None else ",readonly"),
    ]
    if seed is not None:
        arguments.extend(["--interactive", "--cap-add=CHOWN"])
    arguments.extend(
        [
            "--entrypoint=/bin/sh",
            GRAFANA_IMAGE,
            "-c",
            SEED_SECRET if seed is not None else READ_SECRET,
        ]
    )
    container = docker(arguments).strip()
    if not fullmatch(r"[a-f0-9]{64}", container):
        raise RuntimeError("Unexpected owned helper container identifier")
    try:
        start = ["start", "--attach"]
        if seed is not None:
            start.append("--interactive")
        return docker([*start, container], input_text=seed)
    finally:
        docker(["rm", "--force", "--volumes", container])


def read_password() -> str:
    """Read the existing private host file, without creating or rotating credentials."""
    private_directory()
    path = secret_path()
    validate_secret_metadata(path.lstat())
    value = path.read_text(encoding="utf-8")
    if not fullmatch(r"[A-Za-z0-9_-]{43}", value):
        raise RuntimeError("Unexpected Grafana credential format; do not replace it automatically")
    return value


def verify_secret() -> None:
    """Verify volume identity, internal permissions and exact host/volume agreement."""
    password = read_password()
    if not compare_digest(secret_helper(), password):
        raise RuntimeError("Grafana host/volume credentials differ; no automatic replacement")


def initialize_secret() -> Path:
    """Initialize once, preserving an existing private host credential and all volumes."""
    private_directory(create=True)
    path = secret_path()
    volume = inspect_volume(SECRET_VOLUME)
    if volume is not None:
        verify_secret()
        return path
    if inspect_volume(DATA_VOLUME) is not None:
        raise RuntimeError("Existing Grafana data found; recover credentials instead of reseeding")
    if not path.exists() and not path.is_symlink():
        with path.open("x", encoding="utf-8") as target:
            path.chmod(0o400)
            target.write(token_urlsafe(32))
    password = read_password()
    docker(["volume", "create", "--label", "finsecure.purpose=" + PURPOSE, SECRET_VOLUME])
    secret_helper(seed=password)
    verify_secret()
    return path


def main() -> None:
    """Expose initialization/verification, never a password-printing command."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "verify"])
    arguments = parser.parse_args()
    if arguments.action == "init":
        initialize_secret()
    else:
        verify_secret()
    print("Grafana credential verified; no secret values emitted")


if __name__ == "__main__":
    main()
