"""Start the explicitly approved, separately credentialed local release worker once."""

from argparse import ArgumentParser
from json import dumps, loads
from re import fullmatch
from subprocess import run
from time import monotonic, sleep

from bootstrap import ROOT, Jenkins, admin_password, command
from defusedxml.ElementTree import fromstring

IMAGE = "finsecure-jenkins-release-agent:step-04-03"
VOLUME = "finsecure-jenkins-release-agent-secrets"
PURPOSE = "finsecure-pay-release-agent"
COMPOSE = [
    "docker",
    "compose",
    "-f",
    str(ROOT / "ops/jenkins/compose.yaml"),
    "-f",
    str(ROOT / "ops/jenkins/notifications.compose.yaml"),
    "-f",
    str(ROOT / "ops/jenkins/release.compose.yaml"),
]
SEED = (
    "from pathlib import Path; from os import chmod,chown,umask; from sys import stdin; "
    "from re import fullmatch; umask(0o077); p=Path('/out'); "
    "assert not list(p.iterdir()); s=stdin.read(65); "
    "assert fullmatch(r'[a-f0-9]{64}',s); f=p/'agent_secret'; "
    "f.write_text(s); chmod(f,0o400); chown(f,1000,1000); "
    "chmod(p,0o700); chown(p,1000,1000)"
)


def initialize_secret(secret: str) -> None:
    """Refuse any existing secret volume; seed only this new empty, labelled volume."""
    if fullmatch(r"[a-f0-9]{64}", secret) is None:
        raise ValueError("Invalid release agent identity")
    result = run(
        ["docker", "volume", "inspect", VOLUME],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode == 0 or "no such volume" not in result.stderr.lower():
        raise RuntimeError(
            "Release secret volume exists or cannot be checked; inspect, do not retry"
        )
    command(["docker", "volume", "create", "--label", "finsecure.purpose=" + PURPOSE, VOLUME])
    container = command(
        [
            "docker",
            "create",
            "--pull=never",
            "--interactive",
            "--network=none",
            "--read-only",
            "--user=0:0",
            "--cap-drop=ALL",
            "--cap-add=CHOWN",
            "--security-opt=no-new-privileges:true",
            "--label",
            "finsecure.purpose=" + PURPOSE,
            "--mount",
            f"type=volume,source={VOLUME},target=/out",
            "--entrypoint=python",
            IMAGE,
            "-c",
            SEED,
        ]
    )
    if fullmatch(r"[a-f0-9]{64}", container) is None:
        raise RuntimeError("Unexpected owned helper identity")
    try:
        command(
            ["docker", "start", "--attach", "--interactive", container],
            input_text=secret,
            timeout=30,
        )
    finally:
        command(["docker", "rm", "--force", "--volumes", container])


def start() -> dict:
    """Connect one worker; do not create/import registry or Google credentials or jobs."""
    image = loads(command(["docker", "image", "inspect", IMAGE]))[0]
    if image["Config"]["User"] != "jenkins" or image["Config"].get("Volumes"):
        raise RuntimeError("Unexpected release image user or implicit volumes")
    client = Jenkins(admin_password())
    agent = loads(client.request("/computer/finsecure-release/api/json"))
    if not agent["offline"] or len(agent["executors"]) != 1:
        raise RuntimeError("Expected an offline, single-executor release node")
    xml = fromstring(client.request("/computer/finsecure-release/jenkins-agent.jnlp"))
    secret = xml.find(".//argument").text
    source = fromstring(client.request("/computer/finsecure-python/jenkins-agent.jnlp"))
    if secret == source.find(".//argument").text:
        raise RuntimeError("Release and source agent identities must differ")
    initialize_secret(secret)
    command([*COMPOSE, "up", "--detach", "--no-build", "--no-deps", "release-agent"], timeout=60)
    container = command([*COMPOSE, "ps", "--all", "--quiet", "release-agent"])
    if fullmatch(r"[a-f0-9]{64}", container) is None:
        raise RuntimeError("Unexpected release worker container")
    deadline = monotonic() + 120
    while monotonic() < deadline:
        info = loads(command(["docker", "inspect", container]))[0]
        if not info["State"]["Running"] or info["State"]["OOMKilled"]:
            raise RuntimeError("Release worker exited; preserve logs and inspect")
        agent = loads(client.request("/computer/finsecure-release/api/json"))
        if not agent["offline"]:
            return {
                "release_agent_online": True,
                "image_id": info["Image"],
                "executors": len(agent["executors"]),
                "registry_or_cloud_credentials_imported": False,
                "release_job_enabled": False,
            }
        sleep(2)
    raise TimeoutError("Release worker did not connect within 120 seconds")


def main() -> None:
    """Require explicit approval for creating the owned secret volume and worker."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--approve-release-agent", action="store_true")
    if not parser.parse_args().approve_release_agent:
        parser.error("Explicit release-agent approval is required")
    print(dumps(start(), indent=2))


if __name__ == "__main__":
    main()
