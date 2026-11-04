from pathlib import Path
from runpy import run_path
from unittest.mock import Mock

from pytest import MonkeyPatch, fixture, mark, raises

ROOT = Path(__file__).resolve().parents[2]


@fixture
def helpers(monkeypatch: MonkeyPatch) -> dict:
    monkeypatch.syspath_prepend(str(ROOT / "ops/jenkins"))
    return run_path(str(ROOT / "ops/jenkins/verify_release.py"))


@fixture
def container(helpers: dict) -> dict:
    return {
        "Config": {
            "User": "jenkins",
            "Labels": {
                "com.docker.compose.project": "finsecure-jenkins",
                "com.docker.compose.service": "release-agent",
            },
            "Env": [],
            "Cmd": [],
        },
        "Args": [],
        "State": {"Running": True, "OOMKilled": False},
        "HostConfig": {
            "Privileged": False,
            "ReadonlyRootfs": True,
            "CapDrop": ["ALL"],
            "CapAdd": None,
            "SecurityOpt": ["no-new-privileges:true"],
            "NetworkMode": "finsecure-jenkins_default",
            "PidMode": "",
            "IpcMode": "private",
            "Memory": 512 * 1024**2,
            "NanoCpus": 500000000,
        },
        "Mounts": [
            {"Type": "volume", "Destination": path, "Name": name, "RW": writable}
            for path, (name, writable) in helpers["expected_mounts"]().items()
        ],
        "NetworkSettings": {"Networks": {"finsecure-jenkins_default": {}}},
    }


def test_process_probe_uses_python_instead_of_platform_specific_ps(helpers, monkeypatch):
    command = Mock(return_value='["java", "environment"]')
    monkeypatch.setitem(helpers["process_metadata"].__globals__, "command", command)
    assert helpers["process_metadata"]("worker") == ["java", "environment"]
    assert command.call_args.args[0][:5] == ["docker", "exec", "worker", "python", "-c"]


@mark.parametrize("response", ["[]", "{}", '["valid", 1]'])
def test_rejects_invalid_process_metadata(helpers, monkeypatch, response):
    monkeypatch.setitem(
        helpers["process_metadata"].__globals__, "command", Mock(return_value=response)
    )
    with raises(ValueError, match="PROCESS_METADATA_INVALID"):
        helpers["process_metadata"]("worker")


def test_accepts_approved_release_boundaries(helpers, container):
    helpers["check_container"](container, "1000", ["synthetic-secret"])


@mark.parametrize(
    ("field", "value"),
    [
        ("Privileged", True),
        ("ReadonlyRootfs", False),
        ("CapAdd", ["NET_ADMIN"]),
        ("CapDrop", []),
        ("SecurityOpt", []),
        ("NetworkMode", "host"),
        ("PidMode", "host"),
        ("IpcMode", "host"),
        ("Devices", [{"PathOnHost": "device"}]),
        ("PortBindings", {"8080/tcp": [{}]}),
        ("Memory", 0),
        ("NanoCpus", 0),
        ("Tmpfs", {"unexpected": "rw"}),
    ],
)
def test_rejects_release_isolation_or_resource_drift(helpers, container, field, value):
    container["HostConfig"][field] = value
    with raises(ValueError, match="BOUNDARY_INVALID"):
        helpers["check_container"](container, "1000", [])


@mark.parametrize("field", ["Env", "Cmd"])
def test_rejects_secret_content_in_container_configuration(helpers, container, field):
    container["Config"][field] = ["value=synthetic-secret"]
    with raises(ValueError, match="SECRET_IN_PROCESS_METADATA"):
        helpers["check_container"](container, "1000", ["synthetic-secret"])


def test_rejects_extra_shared_mount(helpers, container):
    container["Mounts"].append(
        {"Type": "volume", "Destination": "/other", "Name": "source-workspace", "RW": True}
    )
    with raises(ValueError, match="MOUNTS_INVALID"):
        helpers["check_container"](container, "1000", [])


def test_rejects_writable_remoting_secret_mount(helpers, container):
    next(m for m in container["Mounts"] if m["Destination"] == "/run/secrets")["RW"] = True
    with raises(ValueError, match="MOUNTS_INVALID"):
        helpers["check_container"](container, "1000", [])


def test_rejects_extra_network(helpers, container):
    container["NetworkSettings"]["Networks"]["unrelated"] = {}
    with raises(ValueError, match="NETWORK_INVALID"):
        helpers["check_container"](container, "1000", [])
