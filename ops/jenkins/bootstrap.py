"""Start the local Jenkins instance without printing or passing secrets on command lines."""

from argparse import ArgumentParser
from base64 import b64encode
from http.cookiejar import CookieJar
from json import dumps, loads
from os import umask
from pathlib import Path
from re import fullmatch
from secrets import token_urlsafe
from subprocess import run
from time import monotonic, sleep
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)
from xml.etree.ElementTree import fromstring

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ["docker", "compose", "-f", str(ROOT / "ops/jenkins/compose.yaml")]
BASE_URL = "http://127.0.0.1:8080"
SECRET_DIRECTORY = Path.home() / ".config/finsecure-pay/jenkins"
PURPOSE = "finsecure-pay-local-jenkins"


class NoRedirect(HTTPRedirectHandler):
    """Never forward administrative authentication to a redirect destination."""

    def redirect_request(
        self, req: Request, fp: BinaryIO, code: int, msg: str, headers: object, newurl: str
    ) -> None:
        fp.close()
        raise RuntimeError("Unexpected Jenkins redirect; credentials were not forwarded")


def command(arguments: list[str], *, input_text: str | None = None, timeout: int = 60) -> str:
    """Run local Docker commands, keeping captured output out of exception messages."""
    result = run(
        arguments, cwd=ROOT, input=input_text, capture_output=True, text=True, timeout=timeout
    )
    if result.returncode:
        raise RuntimeError(
            "Local Docker command failed; inspect the owned service without exposing secrets"
        )
    return result.stdout.strip()


def admin_password(*, create: bool = False) -> str:
    """Reuse a private credential; do not replace missing credentials for an existing instance."""
    umask(0o077)
    SECRET_DIRECTORY.mkdir(mode=0o700, parents=True, exist_ok=True)
    if SECRET_DIRECTORY.is_symlink() or SECRET_DIRECTORY.stat().st_mode & 0o077:
        raise RuntimeError("Jenkins credential directory must be private and not a symlink")
    path = SECRET_DIRECTORY / "admin-password"
    if not path.exists():
        if not create:
            raise RuntimeError("Local Jenkins password is missing; bootstrap or recover it first")
        existing = run(
            ["docker", "volume", "inspect", "finsecure-jenkins-controller-secrets"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if existing.returncode == 0:
            raise RuntimeError(
                "Existing Jenkins secret volume found; recover the password privately"
            )
        if "no such volume" not in existing.stderr.lower():
            raise RuntimeError("Unable to check for existing Jenkins credentials")
        with path.open("x", encoding="utf-8") as target:
            target.write(token_urlsafe(32))
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise RuntimeError("Jenkins password file must be private and not a symlink")
    password = path.read_text(encoding="utf-8")
    if not fullmatch(r"[A-Za-z0-9_-]{43}", password):
        raise RuntimeError("Unexpected local password format; refusing to replace it")
    return password


def seed_secret(volume: str, filename: str, value: str) -> None:
    """Populate only a purpose-labelled owned volume through stdin, not argv/environment."""
    exists = run(
        ["docker", "volume", "inspect", volume], capture_output=True, text=True, timeout=15
    )
    if exists.returncode == 0:
        labels = loads(exists.stdout)[0].get("Labels") or {}
        if labels.get("finsecure.purpose") != PURPOSE:
            raise RuntimeError(
                "Refusing to modify a secret volume without the expected ownership label"
            )
    else:
        if "no such volume" not in exists.stderr.lower():
            raise RuntimeError("Unable to inspect Docker secret volume")
        command(["docker", "volume", "create", "--label", "finsecure.purpose=" + PURPOSE, volume])
    code = (
        "from pathlib import Path; from os import chmod, chown; from sys import stdin, argv; "
        "p = Path('/out') / argv[1]; p.write_text(stdin.read()); "
        "chmod(p, 0o400); chown(p, 1000, 1000); "
        "chmod('/out', 0o700); chown('/out', 1000, 1000)"
    )
    command(
        [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--network=none",
            "--read-only",
            "--user=0:0",
            "--cap-drop=ALL",
            "--cap-add=CHOWN",
            "--cap-add=DAC_OVERRIDE",
            "--cap-add=FOWNER",
            "--security-opt=no-new-privileges:true",
            "--volume",
            volume + ":/out",
            "--interactive",
            "--entrypoint=python",
            "finsecure-jenkins-agent:step-04-01",
            "-c",
            code,
            filename,
        ],
        input_text=value,
    )


class Jenkins:
    """Loopback-only authenticated API client with cookies for CSRF protection."""

    def __init__(self, password: str) -> None:
        self.opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()), NoRedirect())
        self.authorization = "Basic " + b64encode(("admin:" + password).encode()).decode()

    def request(
        self, path: str, data: bytes | None = None, headers: dict[str, str] | None = None
    ) -> bytes:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Only local Jenkins API paths are accepted")
        request = Request(
            BASE_URL + path,
            data=data,
            headers={"Authorization": self.authorization, **(headers or {})},
        )
        with self.opener.open(request, timeout=5) as response:
            return response.read()

    def wait(self, path: str, key: str, expected: object, seconds: int, service: str) -> dict:
        """Poll startup state with a deadline; stop promptly if the owned container exits."""
        container = command([*COMPOSE, "ps", "--all", "--quiet", service])
        if not container:
            raise RuntimeError("Expected Jenkins service container is missing")
        deadline = monotonic() + seconds
        last_status = None
        while monotonic() < deadline:
            if (
                command(["docker", "inspect", "--format", "{{.State.Running}}", container])
                != "true"
            ):
                raise RuntimeError(
                    "Owned Jenkins service exited during startup; inspect sanitized logs"
                )
            try:
                value = loads(self.request(path))
                if value.get(key) == expected:
                    return value
            except HTTPError as error:
                error.close()
                last_status = error.code
                # Authentication/user state may not be ready during initialization.
                # Persistent errors still fail at the deadline; no build is retried.
                if error.code not in {401, 403, 404, 500, 503}:
                    raise RuntimeError(f"Jenkins startup API returned HTTP {error.code}") from None
            except URLError, TimeoutError, ConnectionError:
                pass
            sleep(2)
        raise TimeoutError(
            f"Jenkins did not reach the expected startup state; last HTTP status: {last_status}"
        )


def check_data_volume_ownership() -> bool:
    """Reject unrelated volumes and report whether controller state already exists."""
    controller_exists = False
    for suffix in ["controller-home", "agent-workspace"]:
        result = run(
            ["docker", "volume", "inspect", "finsecure-jenkins_" + suffix],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            labels = loads(result.stdout)[0].get("Labels") or {}
            if labels.get("com.docker.compose.project") != "finsecure-jenkins":
                raise RuntimeError(
                    "Refusing to reuse a data volume without the expected project label"
                )
            controller_exists = controller_exists or suffix == "controller-home"
        elif "no such volume" not in result.stderr.lower():
            raise RuntimeError("Unable to inspect existing Jenkins data volumes")
    return controller_exists


def start() -> dict[str, object]:
    """Start only this Compose project, configure its inbound agent, and check isolation."""
    controller_exists = check_data_volume_ownership()
    password = admin_password(create=not controller_exists)
    seed_secret("finsecure-jenkins-controller-secrets", "admin_password", password)
    command([*COMPOSE, "up", "--detach", "--no-build", "controller"])
    client = Jenkins(password)
    root = client.wait("/api/json", "numExecutors", 0, 180, "controller")
    anonymous = build_opener(ProxyHandler({}), NoRedirect())
    try:
        with anonymous.open(BASE_URL + "/api/json", timeout=5):
            raise RuntimeError("Anonymous Jenkins API access must be denied")
    except HTTPError as error:
        error.close()
        if error.code not in {401, 403}:
            raise RuntimeError("Unexpected anonymous-access response") from None
    jnlp = fromstring(client.request("/computer/finsecure-python/jenkins-agent.jnlp"))
    arguments = [item.text for item in jnlp.findall(".//argument")]
    secret = arguments[0] if arguments else None
    if not secret or not fullmatch(r"[a-f0-9]{64}", secret):
        raise RuntimeError("Agent secret response did not match the expected format")
    seed_secret("finsecure-jenkins-agent-secrets", "agent_secret", secret)
    command([*COMPOSE, "up", "--detach", "--no-build", "agent"])
    agent = client.wait("/computer/finsecure-python/api/json", "offline", False, 120, "agent")
    for name in ["finsecure-checkout", "finsecure-ci"]:
        client.wait(f"/job/{name}/api/json", "name", name, 60, "controller")
    return {
        "url": BASE_URL,
        "controller_executors": root["numExecutors"],
        "agent_online": not agent["offline"],
        "anonymous_api_access": "denied",
        "configured_jobs_visible": ["finsecure-checkout", "finsecure-ci"],
        "password_file": str(SECRET_DIRECTORY / "admin-password"),
    }


def main() -> None:
    """Bootstrap the prebuilt local stack; never print password or agent secret values."""
    ArgumentParser(description=__doc__).parse_args()
    print(dumps(start(), indent=2))


if __name__ == "__main__":
    main()
