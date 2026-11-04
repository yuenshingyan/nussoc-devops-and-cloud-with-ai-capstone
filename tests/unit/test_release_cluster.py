from io import BytesIO
from json import dumps, loads
from pathlib import Path
from runpy import run_path
from subprocess import CompletedProcess, TimeoutExpired
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.request import Request

from pytest import fixture, mark, raises

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/release_cluster.py"
PROJECT = "finsecure-pay-capstone-abcdef"


@fixture
def helpers() -> dict:
    return run_path(str(SCRIPT))


@fixture
def key_file(tmp_path: Path) -> Path:
    path = tmp_path / "key.json"
    path.write_text(
        dumps(
            {
                "type": "service_account",
                "project_id": PROJECT,
                "client_email": f"finsecure-gke-deployer@{PROJECT}.iam.gserviceaccount.com",
                "token_uri": "https://oauth2.googleapis.com/token",
                "private_key": "synthetic",
            }
        )
    )
    path.chmod(0o600)
    return path


def cluster_data() -> dict:
    return {
        "name": "finsecure-pay-demo",
        "location": "asia-southeast1-a",
        "status": "RUNNING",
        "controlPlaneEndpointsConfig": {"dnsEndpointConfig": {"endpoint": "test.asia.gke.goog"}},
    }


class Response(BytesIO):
    def __init__(self, payload: bytes, status: int = 200) -> None:
        super().__init__(payload)
        self.status = status


@mark.parametrize("mode", [0o400, 0o600])
def test_accepts_private_deployer_file(helpers, key_file, mode):
    key_file.chmod(mode)
    assert helpers["credential_project"](key_file) == PROJECT


@mark.parametrize("mode", [0o644, 0o640, 0o777])
def test_rejects_exposed_credential_file(helpers, key_file, mode):
    key_file.chmod(mode)
    with raises(ValueError, match="UNSAFE_DEPLOYER_FILE"):
        helpers["credential_project"](key_file)


@mark.parametrize("link", ["symbolic", "hard"])
def test_rejects_linked_credential_file(helpers, key_file, link):
    other = key_file.with_name("other")
    if link == "symbolic":
        other.symlink_to(key_file)
    else:
        other.hardlink_to(key_file)
    with raises(ValueError, match="UNSAFE_DEPLOYER_FILE"):
        helpers["credential_project"](other)


@mark.parametrize(
    ("field", "value"),
    [
        ("type", "authorized_user"),
        ("project_id", "unrelated-project"),
        ("client_email", "other@example.test"),
        ("token_uri", "https://attacker.example/token"),
        ("universe_domain", "attacker.example"),
        ("project_id", None),
    ],
)
def test_rejects_wrong_identity_or_token_destination(helpers, key_file, field, value):
    data = loads(key_file.read_text())
    data[field] = value
    key_file.write_text(dumps(data))
    with raises(ValueError):
        helpers["credential_project"](key_file)


def test_client_environment_removes_other_credentials(helpers, key_file, tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/unrelated")
    monkeypatch.setenv("CLOUDSDK_AUTH_ACCESS_TOKEN", "synthetic")
    monkeypatch.setenv("KUBECONFIG", "/operator")
    monkeypatch.setenv("HOME", "/operator")
    env = helpers["client_environment"](key_file, tmp_path)
    assert env["HOME"] == str(tmp_path)
    assert env["GOOGLE_APPLICATION_CREDENTIALS"] == str(key_file)
    assert env["KUBECONFIG"] == str(tmp_path / "kubeconfig")
    assert "CLOUDSDK_AUTH_ACCESS_TOKEN" not in env


def test_client_directory_must_be_private(helpers, tmp_path):
    tmp_path.chmod(0o755)
    with raises(ValueError):
        helpers["client_environment"](tmp_path / "key", tmp_path)


@mark.parametrize("output", ["{}", '{"status":{"token":"bad\\ntoken"}}', "[]", "invalid"])
def test_rejects_invalid_token_output(helpers, monkeypatch, output):
    command = Mock(return_value=CompletedProcess([], 0, output, ""))
    monkeypatch.setitem(helpers["adc_token"].__globals__, "run", command)
    with raises(RuntimeError, match="DEPLOYER_AUTHENTICATION_FAILED"):
        helpers["adc_token"]({})


def test_authentication_uses_adc_only_and_captures_output(helpers, monkeypatch):
    command = Mock(
        return_value=CompletedProcess([], 0, '{"status":{"token":"synthetic-token"}}', "")
    )
    monkeypatch.setitem(helpers["adc_token"].__globals__, "run", command)
    assert helpers["adc_token"]({"HOME": "/private"}) == "synthetic-token"
    assert command.call_args.args[0] == [
        "/usr/local/bin/gke-gcloud-auth-plugin",
        "--use_application_default_credentials",
    ]
    assert command.call_args.kwargs["timeout"] == 30
    assert command.call_args.kwargs["capture_output"] is True


def test_authentication_timeout_is_sanitized(helpers, monkeypatch):
    monkeypatch.setitem(
        helpers["adc_token"].__globals__,
        "run",
        Mock(side_effect=TimeoutExpired("secret-command", 30)),
    )
    with raises(RuntimeError, match="^DEPLOYER_AUTHENTICATION_FAILED$"):
        helpers["adc_token"]({})


def test_cluster_discovery_has_fixed_authority_and_closes_response(helpers, monkeypatch):
    response = Response(dumps(cluster_data()).encode())
    opener = SimpleNamespace(open=Mock(return_value=response))
    build = Mock(return_value=opener)
    monkeypatch.setitem(helpers["cluster_endpoint"].__globals__, "build_opener", build)
    assert helpers["cluster_endpoint"](PROJECT, "synthetic-token") == "https://test.asia.gke.goog"
    request = opener.open.call_args.args[0]
    assert (
        request.full_url
        == f"https://container.googleapis.com/v1/projects/{PROJECT}/locations/asia-southeast1-a/clusters/finsecure-pay-demo"
    )
    assert request.headers["Authorization"] == "Bearer synthetic-token"
    assert build.call_args.args[0].proxies == {}
    assert response.closed


@mark.parametrize(
    "endpoint",
    [
        "evil.example",
        "test.gke.goog.evil.example",
        "test.gke.goog/path",
        "https://test.gke.goog",
        "test.gke.goog:443",
        None,
    ],
)
def test_rejects_unexpected_cluster_endpoint(helpers, monkeypatch, endpoint):
    data = cluster_data()
    data["controlPlaneEndpointsConfig"]["dnsEndpointConfig"]["endpoint"] = endpoint
    response = Response(dumps(data).encode())
    monkeypatch.setitem(
        helpers["cluster_endpoint"].__globals__,
        "build_opener",
        Mock(return_value=SimpleNamespace(open=Mock(return_value=response))),
    )
    with raises(RuntimeError, match="CLUSTER_DISCOVERY_FAILED"):
        helpers["cluster_endpoint"](PROJECT, "synthetic-token")
    assert response.closed


def test_refuses_redirect_and_closes_redirect_response(helpers):
    response = BytesIO(b"unused")
    with raises(RuntimeError, match="CLUSTER_REDIRECT_REFUSED"):
        helpers["NoRedirect"]().redirect_request(
            Request("https://container.googleapis.com"),
            response,
            302,
            "Found",
            {},
            "https://evil.example",
        )
    assert response.closed


def test_closes_http_error_body_without_exposing_details(helpers, monkeypatch):
    body = BytesIO(b"private-error")
    failure = HTTPError("https://private.example", 403, "private-error", {}, body)
    monkeypatch.setitem(
        helpers["cluster_endpoint"].__globals__,
        "build_opener",
        Mock(return_value=SimpleNamespace(open=Mock(side_effect=failure))),
    )
    with raises(RuntimeError, match="^CLUSTER_DISCOVERY_FAILED$"):
        helpers["cluster_endpoint"](PROJECT, "synthetic-token")
    assert body.closed


def test_writes_private_adc_configuration_without_embedding_token(
    helpers, monkeypatch, key_file, tmp_path
):
    state = helpers["prepare_client"].__globals__
    monkeypatch.setitem(state, "adc_token", Mock(return_value="synthetic-token"))
    monkeypatch.setitem(state, "cluster_endpoint", Mock(return_value="https://test.gke.goog"))
    env = helpers["prepare_client"](key_file, tmp_path)
    path = Path(env["KUBECONFIG"])
    assert path.stat().st_mode & 0o777 == 0o600
    config = loads(path.read_text())
    assert "synthetic-token" not in path.read_text()
    assert config["users"][0]["user"]["exec"]["args"] == ["--use_application_default_credentials"]
    assert "insecure-skip-tls-verify" not in config["clusters"][0]["cluster"]
    with raises(FileExistsError):
        helpers["prepare_client"](key_file, tmp_path)
