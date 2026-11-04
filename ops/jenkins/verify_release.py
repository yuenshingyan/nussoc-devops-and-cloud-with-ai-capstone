"""Read-only checks for the isolated release worker and folder-scoped file credentials."""

from hashlib import sha256
from json import dumps, loads
from pathlib import Path

from bootstrap import BASE_URL, ROOT, Jenkins, admin_password, command
from defusedxml.ElementTree import fromstring
from httpx2 import BasicAuth, Client
from release_store import FILES, ReleaseStore, private_file
from yaml import safe_load


def expected_mounts() -> dict[str, tuple[str, bool]]:
    """Compare runtime mounts to the reviewed Compose contract, also covered by static tests."""
    config = safe_load((ROOT / "ops/jenkins/release.compose.yaml").read_text())
    names = {
        "release-workspace": "finsecure-jenkins_release-workspace",
        "release-temp": "finsecure-jenkins_release-temp",
        "release-agent-secrets": "finsecure-jenkins-release-agent-secrets",
    }
    result = {}
    specifications = config["services"]["release-agent"]["volumes"]
    if len(specifications) != len(names):
        raise ValueError("UNEXPECTED_RELEASE_MOUNT_CONTRACT")
    for specification in specifications:
        parts = specification.split(":")
        if len(parts) not in {2, 3} or parts[0] not in names:
            raise ValueError("UNEXPECTED_RELEASE_MOUNT_CONTRACT")
        readonly = parts[0] == "release-agent-secrets"
        if parts[2:] != (["ro"] if readonly else []):
            raise ValueError("UNEXPECTED_RELEASE_MOUNT_MODE")
        result[parts[1]] = (names[parts[0]], not readonly)
    if len(result) != len(names) or {item[0] for item in result.values()} != set(names.values()):
        raise ValueError("UNEXPECTED_RELEASE_MOUNT_IDENTITIES")
    return result


def check_container(info: dict, uid: str, secrets: list[str]) -> None:
    """Reject privilege, mount, resource or secret-bearing process-metadata drift."""
    host = info["HostConfig"]
    config = info["Config"]
    if (
        uid != "1000"
        or config["User"] != "jenkins"
        or not info["State"]["Running"]
        or info["State"]["OOMKilled"]
        or config["Labels"].get("com.docker.compose.project") != "finsecure-jenkins"
        or config["Labels"].get("com.docker.compose.service") != "release-agent"
        or host["Privileged"]
        or not host["ReadonlyRootfs"]
        or host.get("CapAdd")
        or host["CapDrop"] != ["ALL"]
        or host["SecurityOpt"] != ["no-new-privileges:true"]
        or host["NetworkMode"] != "finsecure-jenkins_default"
        or host["PidMode"] == "host"
        or host["IpcMode"] == "host"
        or host.get("Devices")
        or host.get("DeviceRequests")
        or host.get("PortBindings")
        or host["Memory"] != 512 * 1024**2
        or host["NanoCpus"] != 500000000
        or host.get("Tmpfs")
        or config.get("Volumes")
    ):
        raise ValueError("RELEASE_CONTAINER_BOUNDARY_INVALID")
    mounts = expected_mounts()
    if len(info["Mounts"]) != len(mounts):
        raise ValueError("RELEASE_MOUNTS_INVALID")
    for mount in info["Mounts"]:
        if mount["Type"] != "volume" or (mount.get("Name"), mount["RW"]) != mounts.get(
            mount["Destination"]
        ):
            raise ValueError("RELEASE_MOUNTS_INVALID")
    if set(info["NetworkSettings"]["Networks"]) != {"finsecure-jenkins_default"}:
        raise ValueError("RELEASE_NETWORK_INVALID")
    values = [*config.get("Env", []), *info.get("Args", []), *config.get("Cmd", [])]
    if any(secret and secret in value for secret in secrets for value in values):
        raise ValueError("RELEASE_SECRET_IN_PROCESS_METADATA")


def process_metadata(container: str) -> list[str]:
    """Read Linux proc metadata without relying on a particular container's ps options."""
    code = (
        "from pathlib import Path\nfrom json import dumps\nvalues=[]\n"
        "for process in Path('/proc').iterdir():\n"
        " if process.name.isdecimal():\n"
        "  for name in ('cmdline','environ'):\n"
        "   try: values.append((process/name).read_bytes().decode('utf-8','replace'))\n"
        "   except FileNotFoundError: pass\n"
        "print(dumps(values))\n"
    )
    values = loads(command(["docker", "exec", container, "python", "-c", code]))
    if not isinstance(values, list) or not values or any(not isinstance(v, str) for v in values):
        raise ValueError("RELEASE_PROCESS_METADATA_INVALID")
    return values


def check_policy(client: Client) -> None:
    """Require the exact reviewed scheduler policy before starting or inspecting this worker."""
    script = """
    def guards = hudson.ExtensionList.lookup(hudson.model.queue.QueueTaskDispatcher.class)
        .findAll { it.class.name == 'FinsecureReleaseDispatcher' }
    assert guards.size() == 1
    def guard = guards[0]
    assert guard.POLICY_VERSION == '1'
    assert guard.TRUSTED_JOBS == ([
        'finsecure-release/verify-boundaries', 'finsecure-release/verify-scheduling'
    ] as Set)
    assert guard.rejection('finsecure-release', 'finsecure-ci', false) != null
    assert guard.rejection('finsecure-python', 'finsecure-release/verify-boundaries', false) != null
    assert guard.rejection('finsecure-release', null, false) != null
    assert guard.rejection(
        'finsecure-release', 'finsecure-release/verify-boundaries', false) == null
    println('FINSECURE_RELEASE_POLICY_VERIFIED')
    """
    crumb_response = client.get(BASE_URL + "/crumbIssuer/api/json")
    crumb_response.raise_for_status()
    crumb = crumb_response.json()
    response = client.post(
        BASE_URL + "/scriptText",
        data={"script": script},
        headers={crumb["crumbRequestField"]: crumb["crumb"]},
    )
    response.raise_for_status()
    if response.text.strip() != "FINSECURE_RELEASE_POLICY_VERIFIED":
        raise ValueError("RELEASE_SCHEDULING_POLICY_NOT_VERIFIED")


def main() -> None:
    """Verify existing resources only; do not start jobs, rotate credentials or configure IAM."""
    password = admin_password()
    jenkins = Jenkins(password)
    agent = loads(jenkins.request("/computer/finsecure-release/api/json"))
    if agent["offline"] or len(agent["executors"]) != 1:
        raise RuntimeError("RELEASE_NODE_NOT_READY")
    directory = Path.home() / ".config/finsecure-pay/release"
    values = {
        identifier: private_file(directory / filename) for identifier, filename in FILES.items()
    }
    key = loads(values["finsecure-gke-deployer"])
    node_secret = (
        fromstring(jenkins.request("/computer/finsecure-release/jenkins-agent.jnlp"))
        .find(".//argument")
        .text
    )
    secrets = [
        password,
        node_secret,
        values["finsecure-dockerhub"].decode(),
        key["private_key"],
        key["private_key"].replace("\n", "\\n"),
    ]
    container = "finsecure-jenkins-release-agent-1"
    info = loads(command(["docker", "inspect", container]))[0]
    check_container(info, command(["docker", "exec", container, "id", "-u"]), secrets)
    processes = process_metadata(container)
    if any(secret in value for secret in secrets for value in processes):
        raise ValueError("RELEASE_SECRET_IN_PROCESS_ARGUMENTS")
    volume = loads(
        command(["docker", "volume", "inspect", "finsecure-jenkins-release-agent-secrets"])
    )[0]
    if volume["Labels"].get("finsecure.purpose") != "finsecure-pay-release-agent":
        raise ValueError("RELEASE_SECRET_VOLUME_NOT_OWNED")
    actual = command(
        [
            "docker",
            "exec",
            container,
            "python",
            "-c",
            "from pathlib import Path; from stat import S_IMODE; "
            "p=Path('/run/secrets'); f=p/'agent_secret'; s=f.stat(); "
            "assert S_IMODE(p.stat().st_mode)==0o700 and S_IMODE(s.st_mode)==0o400 "
            "and s.st_uid==1000 and s.st_nlink==1; print(f.read_text(),end='')",
        ]
    )
    if actual != node_secret:
        raise ValueError("RELEASE_REMOTING_IDENTITY_MISMATCH")
    with Client(
        auth=BasicAuth("admin", password), timeout=20, trust_env=False, follow_redirects=False
    ) as client:
        check_policy(client)
        scoped = ReleaseStore(client).snapshot()
        expected = {
            identifier: {"fileName": FILES[identifier], "sha256": sha256(value).hexdigest()}
            for identifier, value in values.items()
        }
        if scoped != expected:
            raise ValueError("RELEASE_FOLDER_CREDENTIAL_MISMATCH")
    print(
        dumps(
            {
                "release_node_online": True,
                "scheduling_policy_verified": True,
                "release_container_boundaries": "passed",
                "secrets_absent_from_process_arguments_and_environment": True,
                "remoting_secret_verified": True,
                "folder_file_credentials_match_private_sources": True,
                "source_job_lookup_denied": True,
                "cpu_limit": 0.5,
                "memory_limit_mib": 512,
                "readonly_root": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
