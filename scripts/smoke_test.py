"""Run bounded local HTTP checks against an existing image and clean up the container."""

from argparse import ArgumentParser
from datetime import UTC, datetime
from json import dumps, loads
from subprocess import CalledProcessError, run
from sys import stderr
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


def docker(*arguments: str, timeout: float = 30) -> str:
    """Run one Docker command with a bounded wait and propagate failures."""
    try:
        result = run(
            ["docker", *arguments], check=True, capture_output=True, text=True, timeout=timeout
        )
    except CalledProcessError as error:
        raise RuntimeError(f"Docker command failed: {error.stderr.strip()}") from error
    return result.stdout.strip()


def request_json(
    url: str, payload: dict[str, str | float] | None = None, *, timeout: float = 2
) -> tuple[int, object]:
    """Send a local request without using proxy environment variables."""
    request = Request(
        url,
        data=dumps(payload).encode("utf-8") if payload is not None else None,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    opener = build_opener(ProxyHandler({}))
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        return response.status, loads(response.read())


def wait_for_health(container: str, base_url: str) -> None:
    """Poll the owned container for up to 30 seconds; stop if its process exits."""
    deadline = monotonic() + 30
    while (remaining := deadline - monotonic()) > 0:
        state = loads(docker("inspect", container, timeout=remaining))[0]["State"]
        if not state["Running"]:
            raise RuntimeError(f"Container exited before becoming healthy: {state['ExitCode']}")
        remaining = deadline - monotonic()
        if remaining <= 0:
            break
        try:
            if request_json(base_url + "/health", timeout=min(2, remaining)) == (
                200,
                {"status": "healthy"},
            ):
                return
        except URLError, TimeoutError, ConnectionError:
            pass
        sleep(min(0.2, max(0, deadline - monotonic())))
    raise TimeoutError("Container health check did not succeed within 30 seconds")


def validate_image(image: str) -> dict[str, object]:
    """Check a local image using an owned, loopback-only container and remove it afterward."""
    metadata = loads(docker("image", "inspect", image))[0]
    # Resolve the tag once so checks cannot silently switch images mid-run.
    image_id = metadata["Id"]
    container = docker(
        "create",
        "--pull=never",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--tmpfs=/tmp:rw,noexec,nosuid,size=16m",
        "--publish=127.0.0.1::8000",
        image_id,
    )
    print(f"Smoke-test container: {container}", file=stderr)
    try:
        docker("start", container)
        inspection = loads(docker("inspect", container))[0]
        bindings = inspection["NetworkSettings"]["Ports"]["8000/tcp"]
        if len(bindings) != 1 or bindings[0]["HostIp"] != "127.0.0.1":
            raise RuntimeError("Expected exactly one loopback-only published port")
        base_url = f"http://127.0.0.1:{bindings[0]['HostPort']}"
        wait_for_health(container, base_url)

        identity = loads(
            docker(
                "exec",
                container,
                "/opt/venv/bin/python",
                "-c",
                "from pathlib import Path; from json import dumps; "
                "print(dumps({line.split(':')[0]: line.split()[1:] "
                "for line in Path('/proc/1/status').read_text().splitlines() "
                "if line.startswith(('Uid:', 'Gid:'))}))",
            )
        )
        if identity != {"Uid": ["10001"] * 4, "Gid": ["10001"] * 4}:
            raise RuntimeError(f"Unexpected PID 1 identity: {identity}")

        payload: dict[str, str | float] = {
            "transaction_id": "txn_001",
            "sender_id": "account_001",
            "recipient_id": "account_002",
            "amount": "125.50",
            "currency": "SGD",
        }
        results = [{"case": "health", "status": 200, "body": {"status": "healthy"}}]
        cases = [
            ("accepted", payload, 200, {"valid": True, "errors": []}),
            (
                "business_rejection",
                {**payload, "amount": "0"},
                200,
                {"valid": False, "errors": ["AMOUNT_NOT_POSITIVE"]},
            ),
            (
                "malformed_amount",
                {**payload, "amount": 125.50},
                422,
                {
                    "detail": [
                        {
                            "loc": ["body", "amount"],
                            "type": "string_type",
                            "msg": "Invalid request value. Check the API contract.",
                        }
                    ]
                },
            ),
        ]
        for name, body, expected_status, expected_body in cases:
            status, result = request_json(base_url + "/validate", body)
            if (status, result) != (expected_status, expected_body):
                raise RuntimeError(f"{name}: unexpected response {status}: {result}")
            results.append({"case": name, "status": status, "body": result})

        docker("stop", "--timeout=10", container)
        state = loads(docker("inspect", container))[0]["State"]
        if state["Running"] or state["OOMKilled"] or state["ExitCode"] != 0:
            raise RuntimeError(f"Container did not shut down cleanly: {state}")
        summary = {
            "verified_at_utc": datetime.now(UTC).isoformat(),
            "image_tag": image,
            "image_id": image_id,
            "platform": metadata["Os"] + "/" + metadata["Architecture"],
            "container_id": container,
            "base_url": base_url,
            "pid_1_identity": identity,
            "read_only_root_filesystem": inspection["HostConfig"]["ReadonlyRootfs"],
            "dropped_capabilities": inspection["HostConfig"]["CapDrop"],
            "security_options": inspection["HostConfig"]["SecurityOpt"],
            "tmpfs": inspection["HostConfig"]["Tmpfs"],
            "http_checks": results,
            "shutdown_exit_code": state["ExitCode"],
            "oom_killed": state["OOMKilled"],
        }
    finally:
        # Remove only the container this invocation created, even when a check fails.
        docker("rm", "--force", container)
    summary["container_removed"] = True
    return summary


def main() -> None:
    """Run the smoke test; print success evidence only after checks and cleanup succeed."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="finsecure-pay:task-02-step-01")
    arguments = parser.parse_args()
    print(dumps(validate_image(arguments.image), indent=2))


if __name__ == "__main__":
    main()
