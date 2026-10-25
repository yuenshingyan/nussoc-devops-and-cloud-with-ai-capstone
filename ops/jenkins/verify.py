"""Run one checkout-only Jenkins build and save secret-sanitized local evidence."""

from argparse import ArgumentParser
from datetime import UTC, datetime
from json import dumps, loads
from re import fullmatch
from time import monotonic, sleep
from urllib.parse import urlencode
from urllib.request import Request
from xml.etree.ElementTree import fromstring

from bootstrap import BASE_URL, COMPOSE, ROOT, Jenkins, admin_password, command


def verify(revision: str) -> dict[str, object]:
    """Verify the queued build's identity, result, agent, tools, and Docker boundaries."""
    if not fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Expected a full lowercase Git commit SHA")
    password = admin_password()
    client = Jenkins(password)
    crumb = loads(client.request("/crumbIssuer/api/json"))
    request = Request(
        BASE_URL + "/job/finsecure-checkout/buildWithParameters",
        data=urlencode({"EXPECTED_REVISION": revision}).encode(),
        headers={
            "Authorization": client.authorization,
            crumb["crumbRequestField"]: crumb["crumb"],
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with client.opener.open(request, timeout=10) as response:
        location = response.headers["Location"]
    if not location.startswith(BASE_URL + "/queue/item/"):
        raise RuntimeError("Unexpected build queue origin; refusing authenticated follow-up")
    queue_path = location.removeprefix(BASE_URL)
    if not fullmatch(r"/queue/item/[0-9]+/", queue_path):
        raise RuntimeError("Unexpected build queue path")
    deadline = monotonic() + 360
    number = None
    while monotonic() < deadline:
        queued = loads(client.request(queue_path + "api/json"))
        if queued.get("cancelled"):
            raise RuntimeError("Checkout build was cancelled")
        if "executable" in queued:
            number = queued["executable"]["number"]
            break
        sleep(2)
    if number is None:
        raise TimeoutError("Checkout build did not start within the verification allowance")
    build_path = f"/job/finsecure-checkout/{number}/"
    while monotonic() < deadline:
        build = loads(client.request(build_path + "api/json"))
        if not build["building"]:
            break
        sleep(2)
    else:
        raise TimeoutError("Checkout build did not finish within the verification allowance")

    console = client.request(build_path + "consoleText").decode()
    secret_xml = fromstring(client.request("/computer/finsecure-python/jenkins-agent.jnlp"))
    agent_secret = secret_xml.find(".//argument").text
    for value in [
        password,
        client.authorization,
        client.authorization.removeprefix("Basic "),
        agent_secret,
    ]:
        if value:
            console = console.replace(value, "<redacted>")
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / f"jenkins-checkout-{number}.txt").write_text(console, encoding="utf-8")
    if build["result"] != "SUCCESS":
        raise RuntimeError("Checkout build failed; inspect its sanitized report")
    for expected in [
        "SOURCE_REVISION=" + revision,
        "Running on finsecure-python",
        "uv 0.9.21",
        "Python 3.14.7",
        "CHECKOUT_ONLY:",
    ]:
        if expected not in console:
            raise RuntimeError(
                "Successful build did not include all expected checkout/tool evidence"
            )
    job = fromstring(client.request("/job/finsecure-checkout/config.xml"))
    poll = job.find(".//hudson.triggers.SCMTrigger/spec")
    if poll is not None:
        raise RuntimeError("Checkout-only job must remain manual")
    application_job = fromstring(client.request("/job/finsecure-ci/config.xml"))
    if application_job.findtext(".//hudson.triggers.SCMTrigger/spec") != "H/5 * * * *":
        raise RuntimeError("Application SCM polling was not configured as expected")
    controller = loads(client.request("/api/json"))
    agent = loads(client.request("/computer/finsecure-python/api/json"))
    if controller["numExecutors"] != 0 or agent["offline"] or len(agent["executors"]) != 1:
        raise RuntimeError("Controller/agent executor separation was not confirmed")
    runtime = {}
    for service in ["controller", "agent"]:
        identifier = command([*COMPOSE, "ps", "--quiet", service])
        container = loads(command(["docker", "inspect", identifier]))[0]
        host = container["HostConfig"]
        if not container["State"]["Running"] or container["State"]["OOMKilled"]:
            raise RuntimeError("Jenkins service is not running normally")
        if any(
            "docker.sock" in mount["Source"] or mount["Type"] == "bind"
            for mount in container["Mounts"]
        ):
            raise RuntimeError("Unexpected host bind or Docker socket mount")
        if host["CapDrop"] != ["ALL"] or "no-new-privileges:true" not in host["SecurityOpt"]:
            raise RuntimeError("Container privilege restrictions did not match configuration")
        uid = command([*COMPOSE, "exec", "-T", service, "id", "-u"])
        if uid != "1000":
            raise RuntimeError("Jenkins service is not using the expected non-root user")
        if service == "controller":
            if host["PortBindings"] != {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]}:
                raise RuntimeError("Controller port must be loopback-only")
        elif host["PortBindings"]:
            raise RuntimeError("Agent must not publish a host port")
        runtime[service] = {
            "image_id": container["Image"],
            "uid": uid,
            "memory_limit_bytes": host["Memory"],
            "nano_cpus": host["NanoCpus"],
            "host_bind_mounts": False,
            "docker_socket_mounted": False,
        }
    return {
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "jenkins_url_local_only": BASE_URL,
        "job": "finsecure-checkout",
        "build_number": number,
        "result": build["result"],
        "source_commit": revision,
        "controller_executors": 0,
        "agent_executors": 1,
        "agent_online": True,
        "source_trigger": "Checkout diagnostic is manual; finsecure-ci owns H/5 SCM polling",
        "runtime": runtime,
        "application_tests_in_jenkins": "Not run by this diagnostic; use finsecure-ci",
        "security_and_delivery_stages": "pending",
        "cloud_resources_created": False,
    }


def main() -> None:
    """Verify a particular reviewed revision without leaking Jenkins authentication."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--expected-revision", required=True)
    arguments = parser.parse_args()
    summary = verify(arguments.expected_revision)
    (ROOT / "reports/jenkins-verification.json").write_text(dumps(summary, indent=2) + "\n")
    print(dumps(summary, indent=2))


if __name__ == "__main__":
    main()
