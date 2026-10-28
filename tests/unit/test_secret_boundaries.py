"""Verify local credential boundaries with synthetic data and mocked Docker/HTTP calls."""

from collections.abc import Iterator
from copy import deepcopy
from io import BytesIO
from json import dumps, loads
from pathlib import Path
from runpy import run_path
from typing import Any
from unittest.mock import Mock
from urllib.error import HTTPError

from pytest import MonkeyPatch, fixture, mark, raises


@fixture
def helpers(monkeypatch: MonkeyPatch) -> dict[str, Any]:
    directory = Path(__file__).resolve().parents[2] / "ops/jenkins"
    monkeypatch.syspath_prepend(str(directory))
    return run_path(str(directory / "verify_secrets.py"))


@fixture
def credential_directory(tmp_path: Path) -> Path:
    directory = tmp_path / "credentials"
    directory.mkdir(mode=0o700)
    password = directory / "admin-password"
    password.write_text("s" * 43)
    password.chmod(0o600)
    return directory


def test_private_existing_password_is_read_without_changes(helpers, credential_directory):
    before = (credential_directory / "admin-password").stat()
    assert helpers["read_password"](credential_directory) == "s" * 43
    after = (credential_directory / "admin-password").stat()
    assert (before.st_mtime_ns, before.st_mode) == (after.st_mtime_ns, after.st_mode)


def test_missing_credentials_are_not_created(helpers, tmp_path):
    directory = tmp_path / "missing"
    with raises(FileNotFoundError):
        helpers["read_password"](directory)
    assert not directory.exists()


@mark.parametrize(
    "problem",
    ["directory_mode", "file_mode", "file_symlink", "directory_symlink", "format", "owner"],
)
def test_host_credential_drift_is_rejected(helpers, credential_directory, monkeypatch, problem):
    directory = credential_directory
    password = directory / "admin-password"
    if problem == "directory_mode":
        directory.chmod(0o755)
    elif problem == "file_mode":
        password.chmod(0o644)
    elif problem == "file_symlink":
        target = directory / "target"
        password.rename(target)
        password.symlink_to(target)
    elif problem == "directory_symlink":
        link = directory.parent / "link"
        link.symlink_to(directory, target_is_directory=True)
        directory = link
    elif problem == "owner":
        monkeypatch.setitem(helpers["read_password"].__globals__, "getuid", lambda: -1)
    else:
        password.write_text("invalid synthetic password")
    with raises(ValueError):
        helpers["read_password"](directory)


def container_info(helpers: dict[str, Any], service: str) -> dict:
    """Supply expected Docker inspect fields without real host configuration."""
    return {
        "Config": {
            "Labels": {
                "com.docker.compose.project": "finsecure-jenkins",
                "com.docker.compose.service": service,
            },
            "Cmd": ["-secret", "@/run/secrets/agent_secret"] if service == "agent" else [],
            "Env": ["SAFE=synthetic"],
        },
        "State": {"Running": True, "OOMKilled": False},
        "Mounts": [
            {"Type": "volume", "Name": name, "Destination": destination, "RW": writable}
            for destination, (name, writable) in helpers["MOUNTS"][service].items()
        ],
        "HostConfig": {
            "Privileged": False,
            "NetworkMode": "finsecure-jenkins_default",
            "PidMode": "",
            "IpcMode": "private",
            "Devices": [],
            "PortBindings": {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]}
            if service == "controller"
            else {},
            "CapDrop": ["ALL"],
            "CapAdd": ["CAP_SETUID", "CAP_SETGID"] if service == "builder" else [],
            "MaskedPaths": [] if service == "builder" else ["/proc/kcore"],
            "ReadonlyPaths": [] if service == "builder" else ["/proc/sys"],
            "SecurityOpt": ["seccomp=unconfined", "apparmor=unconfined"]
            if service == "builder"
            else ["no-new-privileges:true"],
        },
    }


@mark.parametrize("service", ["controller", "agent", "builder"])
def test_expected_service_boundaries_pass(helpers, service):
    helpers["check_container"](
        service, container_info(helpers, service), "1000", ["synthetic-secret"]
    )


@mark.parametrize(
    "problem",
    [
        "project",
        "service",
        "stopped",
        "oom",
        "root",
        "privileged",
        "host_network",
        "host_pid",
        "host_ipc",
        "device",
        "host_bind",
        "wrong_volume",
        "writable_secret",
        "extra_mount",
        "missing_mount",
        "duplicate_mount",
        "port",
        "cap_drop",
        "cap_add",
        "security_opt",
        "secret_env",
        "secret_arg",
        "secret_file_argument",
    ],
)
def test_agent_boundary_drift_is_rejected(helpers, problem):
    info = container_info(helpers, "agent")
    host = info["HostConfig"]
    uid = "1000"
    if problem in {"project", "service"}:
        info["Config"]["Labels"]["com.docker.compose." + problem] = "other"
    elif problem == "stopped":
        info["State"]["Running"] = False
    elif problem == "oom":
        info["State"]["OOMKilled"] = True
    elif problem == "root":
        uid = "0"
    elif problem == "privileged":
        host["Privileged"] = True
    elif problem in {"host_network", "host_pid", "host_ipc"}:
        host[
            {"host_network": "NetworkMode", "host_pid": "PidMode", "host_ipc": "IpcMode"}[problem]
        ] = "host"
    elif problem == "device":
        host["Devices"] = [{"PathOnHost": "/dev/synthetic"}]
    elif problem == "host_bind":
        info["Mounts"][0]["Type"] = "bind"
    elif problem == "wrong_volume":
        info["Mounts"][0]["Name"] = "finsecure-jenkins-controller-secrets"
    elif problem == "writable_secret":
        info["Mounts"][0]["RW"] = True
    elif problem == "extra_mount":
        info["Mounts"].append(deepcopy(info["Mounts"][0]))
    elif problem == "missing_mount":
        info["Mounts"].pop()
    elif problem == "duplicate_mount":
        info["Mounts"][1] = deepcopy(info["Mounts"][0])
    elif problem == "port":
        host["PortBindings"] = {"8080/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}
    elif problem == "cap_drop":
        host["CapDrop"] = []
    elif problem == "cap_add":
        host["CapAdd"] = ["SYS_ADMIN"]
    elif problem == "security_opt":
        host["SecurityOpt"] = []
    elif problem == "secret_env":
        info["Config"]["Env"].append("PASSWORD=synthetic-secret")
    elif problem == "secret_arg":
        info["Config"]["Cmd"].append("synthetic-secret")
    else:
        info["Config"]["Cmd"] = ["-secret", "other-file"]
    with raises(ValueError):
        helpers["check_container"]("agent", info, uid, ["synthetic-secret"])


@mark.parametrize(
    "problem", ["port", "capability", "profile", "secret_mount", "masked_paths", "readonly_paths"]
)
def test_builder_cannot_expand_approved_exceptions(helpers, problem):
    info = container_info(helpers, "builder")
    if problem == "port":
        info["HostConfig"]["PortBindings"] = {"123/tcp": []}
    elif problem == "capability":
        info["HostConfig"]["CapAdd"].append("SYS_ADMIN")
    elif problem == "profile":
        info["HostConfig"]["SecurityOpt"].append("label=disable")
    elif problem in {"masked_paths", "readonly_paths"}:
        info["HostConfig"]["MaskedPaths" if problem == "masked_paths" else "ReadonlyPaths"] = [
            "/synthetic"
        ]
    else:
        info["Mounts"].append(container_info(helpers, "agent")["Mounts"][0])
    with raises(ValueError):
        helpers["check_container"]("builder", info, "1000", ["synthetic-secret"])


def test_builder_accepts_unprefixed_capability_names(helpers):
    info = container_info(helpers, "builder")
    info["HostConfig"]["CapAdd"] = ["SETUID", "SETGID"]
    helpers["check_container"]("builder", info, "1000", ["synthetic-secret"])


def job_xml() -> bytes:
    """Minimal synthetic SCM configuration for the approved public main checkout."""
    return b"""<flow-definition>
<definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition">
<scriptPath>Jenkinsfile</scriptPath><scm><branches><hudson.plugins.git.BranchSpec><name>*/main</name></hudson.plugins.git.BranchSpec></branches>
<userRemoteConfigs><hudson.plugins.git.UserRemoteConfig><url>https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone.git</url></hudson.plugins.git.UserRemoteConfig></userRemoteConfigs>
</scm></definition></flow-definition>"""


def test_trusted_anonymous_main_checkout_passes(helpers):
    helpers["check_job"](job_xml())


@mark.parametrize(
    "old,new",
    [
        (b"*/main", b"*/untrusted"),
        (b"Jenkinsfile", b"Otherfile"),
        (b"CpsScmFlowDefinition", b"CpsFlowDefinition"),
        (b"https://github.com/", b"https://user:synthetic-secret@github.com/"),
        (b"</scm>", b"<credentialsId>release-secret</credentialsId></scm>"),
    ],
)
def test_changed_checkout_boundary_is_rejected(helpers, old, new):
    with raises(ValueError):
        helpers["check_job"](job_xml().replace(old, new))


@mark.parametrize("status", [200, 302, 401, 403, 500])
def test_anonymous_probe_requires_denial(helpers, monkeypatch, status):
    opener = Mock()
    if status == 200:
        opener.open.return_value = BytesIO(b"synthetic response")
    else:
        opener.open.side_effect = HTTPError(
            "http://127.0.0.1:8080/api/json", status, "synthetic", {}, None
        )
    monkeypatch.setitem(
        helpers["check_anonymous_access"].__globals__, "build_opener", Mock(return_value=opener)
    )
    if status in {401, 403}:
        helpers["check_anonymous_access"]()
    else:
        with raises(ValueError):
            helpers["check_anonymous_access"]()
    assert opener.open.call_count == 1


@fixture
def live_boundaries(
    helpers: dict[str, Any], credential_directory: Path, monkeypatch: MonkeyPatch, tmp_path: Path
) -> Iterator[dict[str, Any]]:
    state = helpers["verify"].__globals__
    monkeypatch.setitem(state, "SECRET_DIRECTORY", credential_directory)
    monkeypatch.setitem(state, "ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["verify_secrets.py"])
    request = Mock(
        side_effect=lambda path: (
            b"<jnlp><argument>" + b"a" * 64 + b"</argument></jnlp>"
            if path.endswith("jnlp")
            else job_xml()
        )
    )
    monkeypatch.setattr(state["Jenkins"], "request", request)
    opener = Mock()
    denial = HTTPError("http://127.0.0.1:8080/api/json", 403, "denied", {}, None)
    opener.open.side_effect = denial
    monkeypatch.setitem(state, "build_opener", Mock(return_value=opener))
    identifiers = {
        service: str(index) * 64 for index, service in enumerate(helpers["MOUNTS"], start=1)
    }

    def docker(arguments: list[str], *, timeout: int) -> str:
        assert timeout == 15
        if "ps" in arguments:
            return identifiers[arguments[-1]]
        service = next(
            name for name, identifier in identifiers.items() if identifier == arguments[2]
        )
        if arguments[1] == "inspect":
            return dumps([container_info(helpers, service)])
        assert arguments[1] == "exec"
        if arguments[3:] == ["id", "-u"]:
            return "1000"
        assert arguments[3:6] == ["stat", "-c", "%a %u %g %F"]
        return "400 1000 1000 regular file"

    command = Mock(side_effect=docker)
    monkeypatch.setitem(state, "command", command)
    try:
        yield {"command": command, "request": request, "root": tmp_path}
    finally:
        # Some failures occur before the synthetic anonymous response is consumed.
        denial.close()
        if isinstance(request.side_effect, HTTPError):
            request.side_effect.close()


def test_full_verifier_uses_read_only_calls_and_safe_report(helpers, live_boundaries, capsys):
    helpers["main"]()
    report = loads((live_boundaries["root"] / "reports/secret-boundaries.json").read_text())
    assert report["status"] == "passed"
    assert len(live_boundaries["command"].call_args_list) == 11
    assert all(
        len(call.args) == 1 and not call.kwargs
        for call in live_boundaries["request"].call_args_list
    )
    output = capsys.readouterr().out
    assert "s" * 43 not in output and "a" * 64 not in output


@mark.parametrize("failure", ["docker", "http", "xml", "secret_mode"])
def test_observation_failure_replaces_stale_pass_without_leaking_errors(
    helpers, live_boundaries, capsys, failure
):
    report = live_boundaries["root"] / "reports/secret-boundaries.json"
    report.parent.mkdir()
    report.write_text('{"status":"passed"}')
    if failure == "docker":
        live_boundaries["command"].side_effect = RuntimeError("s" * 43)
    elif failure == "http":
        live_boundaries["request"].side_effect = HTTPError(
            "http://127.0.0.1:8080/", 500, "s" * 43, {}, None
        )
    elif failure == "xml":
        live_boundaries["request"].side_effect = None
        live_boundaries["request"].return_value = b"<invalid"
    else:
        original = live_boundaries["command"].side_effect

        def wrong_mode(arguments: list[str], *, timeout: int) -> str:
            return (
                "644 1000 1000 regular file"
                if "stat" in arguments
                else original(arguments, timeout=timeout)
            )

        live_boundaries["command"].side_effect = wrong_mode
    with raises(SystemExit) as error:
        helpers["main"]()
    assert error.value.code == 1
    if failure == "http":
        assert live_boundaries["request"].side_effect.closed
    assert loads(report.read_text()) == {
        "status": "failed",
        "reason": "boundary_or_observation_failed",
    }
    assert "s" * 43 not in report.read_text() + capsys.readouterr().out
