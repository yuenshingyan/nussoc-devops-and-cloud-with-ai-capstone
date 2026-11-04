"""Prepare an owned GKE client configuration from the dedicated file credential only."""

from json import dumps, loads
from os import environ, getuid
from pathlib import Path
from re import fullmatch
from stat import S_IMODE, S_ISDIR, S_ISREG
from subprocess import SubprocessError, run
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

PLUGIN = "/usr/local/bin/gke-gcloud-auth-plugin"
CLUSTER = "finsecure-pay-demo"
ZONE = "asia-southeast1-a"


class NoRedirect(HTTPRedirectHandler):
    """Do not forward a bearer credential to a redirect destination."""

    def redirect_request(
        self, req: Request, fp: BinaryIO, code: int, msg: str, headers: object, newurl: str
    ) -> None:
        fp.close()
        raise RuntimeError("CLUSTER_REDIRECT_REFUSED")


def credential_project(path: Path) -> str:
    """Validate the private file and intended identity before invoking ADC authentication."""
    info = path.lstat()
    if (
        not path.is_absolute()
        or not S_ISREG(info.st_mode)
        or S_IMODE(info.st_mode) not in {0o400, 0o600}
        or info.st_uid != getuid()
        or info.st_nlink != 1
        or not 0 < info.st_size <= 16384
    ):
        raise ValueError("UNSAFE_DEPLOYER_FILE")
    data = loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("INVALID_DEPLOYER_FILE")
    project = data.get("project_id")
    if (
        not isinstance(project, str)
        or fullmatch(r"finsecure-pay-capstone-[a-f0-9]{6}", project) is None
        or data.get("type") != "service_account"
        or data.get("client_email") != f"finsecure-gke-deployer@{project}.iam.gserviceaccount.com"
        or data.get("token_uri") != "https://oauth2.googleapis.com/token"
        or data.get("universe_domain", "googleapis.com") != "googleapis.com"
    ):
        raise ValueError("WRONG_DEPLOYER_IDENTITY_OR_AUTHORITY")
    return project


def client_environment(key_file: Path, directory: Path) -> dict[str, str]:
    """Keep credential overrides and shared home/profile caches out of the client process."""
    info = directory.lstat()
    if not S_ISDIR(info.st_mode) or info.st_uid != getuid() or S_IMODE(info.st_mode) != 0o700:
        raise ValueError("UNSAFE_CLIENT_DIRECTORY")
    env = {
        key: value
        for key, value in environ.items()
        if not key.startswith(("GOOGLE_", "CLOUDSDK_", "GKE_", "KUBERNETES_"))
        and key not in {"KUBECONFIG", "HOME"}
    }
    env.update(
        HOME=str(directory),
        CLOUDSDK_CONFIG=str(directory / "sdk-cache"),
        GOOGLE_APPLICATION_CREDENTIALS=str(key_file),
        KUBECONFIG=str(directory / "kubeconfig"),
    )
    return env


def adc_token(env: dict[str, str]) -> str:
    """Capture a short-lived token in memory; never run gcloud or use a personal login."""
    try:
        result = run(
            [PLUGIN, "--use_application_default_credentials"],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode:
            raise ValueError("Plugin failure")
        token = loads(result.stdout)["status"]["token"]
        if (
            not isinstance(token, str)
            or len(token) > 8192
            or fullmatch(r"[A-Za-z0-9._~+/-]+=*", token) is None
        ):
            raise ValueError("Invalid token")
        return token
    except OSError, SubprocessError, ValueError, KeyError, TypeError:
        raise RuntimeError("DEPLOYER_AUTHENTICATION_FAILED") from None


def cluster_endpoint(project: str, token: str) -> str:
    """Read only the fixed Google cluster endpoint over verified HTTPS, without proxies."""
    if fullmatch(r"finsecure-pay-capstone-[a-f0-9]{6}", project) is None:
        raise ValueError("INVALID_TARGET_PROJECT")
    request = Request(
        f"https://container.googleapis.com/v1/projects/{project}/locations/{ZONE}/clusters/{CLUSTER}",
        headers={"Authorization": "Bearer " + token},
    )
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=20) as response:
            if response.status != 200:
                raise ValueError("Unexpected status")
            raw = response.read(2097153)
            if len(raw) > 2097152:
                raise ValueError("Oversized response")
            data = loads(raw)
        endpoint = data["controlPlaneEndpointsConfig"]["dnsEndpointConfig"]["endpoint"]
        if (
            data["name"] != CLUSTER
            or data["location"] != ZONE
            or data["status"] != "RUNNING"
            or not isinstance(endpoint, str)
            or fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*\.gke\.goog", endpoint) is None
        ):
            raise ValueError("Unexpected target")
        return "https://" + endpoint
    except HTTPError as error:
        error.close()
        raise RuntimeError("CLUSTER_DISCOVERY_FAILED") from None
    except URLError, OSError, ValueError, KeyError, TypeError:
        raise RuntimeError("CLUSTER_DISCOVERY_FAILED") from None


def prepare_client(key_file: Path, directory: Path) -> dict[str, str]:
    """Write a private kubeconfig; the caller owns cleanup of the directory and caches."""
    project = credential_project(key_file)
    env = client_environment(key_file, directory)
    endpoint = cluster_endpoint(project, adc_token(env))
    config = {
        "apiVersion": "v1",
        "kind": "Config",
        "clusters": [{"name": "release", "cluster": {"server": endpoint}}],
        "contexts": [
            {
                "name": "release",
                "context": {
                    "cluster": "release",
                    "user": "deployer",
                    "namespace": "finsecure-pay",
                },
            }
        ],
        "current-context": "release",
        "users": [
            {
                "name": "deployer",
                "user": {
                    "exec": {
                        "apiVersion": "client.authentication.k8s.io/v1beta1",
                        "command": PLUGIN,
                        "args": ["--use_application_default_credentials"],
                        "interactiveMode": "Never",
                    }
                },
            }
        ],
    }
    path = directory / "kubeconfig"
    with path.open("x", encoding="utf-8") as target:
        path.chmod(0o600)
        target.write(dumps(config))
    return env
