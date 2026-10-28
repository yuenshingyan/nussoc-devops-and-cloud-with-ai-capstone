"""Check the trusted local Jenkins credential boundaries without changing them."""

from argparse import ArgumentParser
from datetime import UTC, datetime
from json import dumps, loads
from os import getuid
from pathlib import Path
from re import fullmatch
from stat import S_IMODE, S_ISDIR, S_ISREG
from subprocess import TimeoutExpired
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener
from xml.etree.ElementTree import ParseError

from bootstrap import BASE_URL, COMPOSE, ROOT, SECRET_DIRECTORY, Jenkins, NoRedirect, command
from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring

MOUNTS = {
    "controller": {
        "/run/secrets": ("finsecure-jenkins-controller-secrets", False),
        "/var/jenkins_home": ("finsecure-jenkins_controller-home", True),
    },
    "agent": {
        "/run/secrets": ("finsecure-jenkins-agent-secrets", False),
        "/home/jenkins/agent": ("finsecure-jenkins_agent-workspace", True),
        "/run/buildkit": ("finsecure-jenkins_builder-socket", False),
    },
    "builder": {
        "/run/user/1000/buildkit": ("finsecure-jenkins_builder-socket", True),
        "/home/user/.local/share/buildkit": ("finsecure-jenkins_builder-state", True),
    },
}


def read_password(directory: Path) -> str:
    """Read only existing owned 0700/0600 files; never create or repair credentials."""
    for path, mode, directory_expected in (
        (directory, 0o700, True),
        (directory / "admin-password", 0o600, False),
    ):
        metadata = path.lstat()
        expected_type = (
            S_ISDIR(metadata.st_mode) if directory_expected else S_ISREG(metadata.st_mode)
        )
        if not expected_type or S_IMODE(metadata.st_mode) != mode or metadata.st_uid != getuid():
            raise ValueError("host_credential_boundary_invalid")
    password = (directory / "admin-password").read_text(encoding="utf-8")
    if not fullmatch(r"[A-Za-z0-9_-]{43}", password):
        raise ValueError("host_credential_format_invalid")
    return password


def check_container(service: str, info: dict, uid: str, secrets: list[str]) -> None:
    """Reject drift from the approved volume, network and privilege boundaries."""
    host = info["HostConfig"]
    labels = info["Config"]["Labels"]
    if (
        labels.get("com.docker.compose.project") != "finsecure-jenkins"
        or labels.get("com.docker.compose.service") != service
        or info["State"]["Running"] is not True
        or info["State"]["OOMKilled"] is not False
        or uid != "1000"
        or host["Privileged"] is not False
        or host["NetworkMode"] == "host"
        or host["NetworkMode"].startswith("container:")
        or host["PidMode"] == "host"
        or host["IpcMode"] == "host"
        or host.get("Devices")
    ):
        raise ValueError("container_identity_or_isolation_invalid")
    mounts = info["Mounts"]
    expected = MOUNTS[service]
    if (
        len(mounts) != len(expected)
        or any(
            mount["Type"] != "volume"
            or mount["Destination"] not in expected
            or (mount["Name"], mount["RW"]) != expected[mount["Destination"]]
            for mount in mounts
        )
        or len({mount["Destination"] for mount in mounts}) != len(expected)
    ):
        raise ValueError("container_mount_boundary_invalid")
    ports = (
        {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]}
        if service == "controller"
        else {}
    )
    if host["PortBindings"] != ports:
        raise ValueError("container_port_boundary_invalid")
    if host["CapDrop"] != ["ALL"]:
        raise ValueError("container_capability_boundary_invalid")
    if service == "builder":
        # Docker prefixes capabilities and expands systempaths=unconfined into
        # empty path restrictions instead of retaining that option in inspect output.
        if (
            {capability.removeprefix("CAP_") for capability in host["CapAdd"] or []}
            != {"SETUID", "SETGID"}
            or set(host["SecurityOpt"] or []) != {"seccomp=unconfined", "apparmor=unconfined"}
            or host["MaskedPaths"] != []
            or host["ReadonlyPaths"] != []
        ):
            raise ValueError("builder_exception_boundary_invalid")
    elif host["CapAdd"] or host["SecurityOpt"] != ["no-new-privileges:true"]:
        raise ValueError("container_privilege_boundary_invalid")
    runtime = dumps([info["Config"]["Cmd"], info["Config"]["Env"]])
    if any(secret in runtime for secret in secrets):
        raise ValueError("known_credential_in_runtime_configuration")
    if service == "agent":
        arguments = info["Config"]["Cmd"]
        if (
            arguments.count("-secret") != 1
            or arguments[arguments.index("-secret") + 1] != "@/run/secrets/agent_secret"
        ):
            raise ValueError("agent_secret_argument_invalid")


def check_job(xml: bytes) -> None:
    """Require anonymous checkout of the approved public repository and trusted main."""
    job = fromstring(xml)
    definition = job.find("definition")
    if (
        definition is None
        or definition.get("class") != "org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition"
        or definition.findtext("scriptPath") != "Jenkinsfile"
        or [item.text for item in job.findall(".//branches/hudson.plugins.git.BranchSpec/name")]
        != ["*/main"]
        or [item.text for item in job.findall(".//hudson.plugins.git.UserRemoteConfig/url")]
        != ["https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone.git"]
        or any((item.text or "").strip() for item in job.findall(".//credentialsId"))
    ):
        raise ValueError("ci_checkout_boundary_invalid")


def check_anonymous_access() -> None:
    """Make one unauthenticated, proxy-free request without following redirects."""
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        with opener.open(BASE_URL + "/api/json", timeout=5):
            raise ValueError("anonymous_api_access_not_denied")
    except HTTPError as error:
        error.close()
        if error.code not in {401, 403}:
            raise ValueError("anonymous_api_status_unexpected") from None


def verify() -> dict:
    """Inspect existing services only; never trigger builds, restart or rotate secrets."""
    password = read_password(SECRET_DIRECTORY)
    client = Jenkins(password)
    jnlp = fromstring(client.request("/computer/finsecure-python/jenkins-agent.jnlp"))
    secret = jnlp.findtext(".//argument")
    if not isinstance(secret, str) or not fullmatch(r"[a-f0-9]{64}", secret):
        raise ValueError("agent_credential_format_invalid")
    secrets = [password, secret, client.authorization, client.authorization.removeprefix("Basic ")]
    check_anonymous_access()
    check_job(client.request("/job/finsecure-ci/config.xml"))
    for service in MOUNTS:
        identifier = command([*COMPOSE, "ps", "--quiet", service], timeout=15)
        if not fullmatch(r"[a-f0-9]{64}", identifier):
            raise ValueError("expected_service_missing")
        info = loads(command(["docker", "inspect", identifier], timeout=15))
        if len(info) != 1:
            raise ValueError("container_inspection_invalid")
        uid = command(["docker", "exec", identifier, "id", "-u"], timeout=15)
        check_container(service, info[0], uid, secrets)
        if service != "builder":
            filename = "admin_password" if service == "controller" else "agent_secret"
            metadata = command(
                [
                    "docker",
                    "exec",
                    identifier,
                    "stat",
                    "-c",
                    "%a %u %g %F",
                    "/run/secrets/" + filename,
                ],
                timeout=15,
            )
            if metadata != "400 1000 1000 regular file":
                raise ValueError("mounted_secret_metadata_invalid")
    return {
        "status": "passed",
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "host_credentials": "owned regular file 0600 in owned directory 0700",
        "containers": "expected volumes, read-only secret mounts, uid 1000, approved privileges",
        "network": "loopback-only controller; no agent/builder published ports",
        "anonymous_api": "denied",
        "checkout": "anonymous public repository, trusted main, Jenkinsfile from SCM",
        "known_credentials_in_argv_environment": False,
        "limitations": [
            "Trusted single-operator model; agent builds can read the agent secret.",
            "Does not verify account inventory, authorization strategy, token scopes or rotation.",
            "Does not scan source, history, logs or arbitrary unknown credentials.",
            "No registry, cloud, cluster, service restart or configuration changes.",
        ],
    }


def main() -> None:
    """Write only a safe status report; do not include raw errors/configuration/secrets."""
    ArgumentParser(description=__doc__).parse_args()
    report = ROOT / "reports/secret-boundaries.json"
    report.parent.mkdir(exist_ok=True)
    report.write_text('{"status":"incomplete"}\n', encoding="utf-8")
    try:
        result = verify()
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        TypeError,
        IndexError,
        TimeoutExpired,
        ParseError,
        DefusedXmlException,
    ) as error:
        if isinstance(error, HTTPError):
            error.close()
        # External errors may contain response bodies or configuration. Do not serialize them.
        report.write_text(
            '{"status":"failed","reason":"boundary_or_observation_failed"}\n', encoding="utf-8"
        )
        print("Secret boundary verification failed; inspect the local configuration privately.")
        raise SystemExit(1) from None
    report.write_text(dumps(result, indent=2) + "\n", encoding="utf-8")
    print(dumps(result, indent=2))


if __name__ == "__main__":
    main()
