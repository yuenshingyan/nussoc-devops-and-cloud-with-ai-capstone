"""One-attempt GKE HTTPS requests; run inside the bounded worker command adapter."""

from contextlib import closing
from http.client import HTTPException, HTTPSConnection
from json import dumps
from math import isfinite
from re import fullmatch
from ssl import create_default_context
from time import monotonic

from scripts.release_archive import strict_json
from scripts.release_deployment import image_patch, require, verify_patch_response

DEPLOYMENT_PATH = "/apis/apps/v1/namespaces/finsecure-pay/deployments/finsecure-pay"
REPLICA_SETS_PATH = "/apis/apps/v1/namespaces/finsecure-pay/replicasets"
PODS_PATH = "/api/v1/namespaces/finsecure-pay/pods"
SELECTOR = "?labelSelector=app.kubernetes.io%2Fname%3Dfinsecure-pay"
RESPONSE_LIMIT = 1024 * 1024


def remaining(deadline: float) -> float:
    """Check the same worker-local deadline; never renew it for another request."""
    require(type(deadline) is float and isfinite(deadline), "DEPLOYMENT_BUDGET_INVALID")
    seconds = deadline - monotonic()
    if seconds <= 0:
        raise TimeoutError("DEPLOYMENT_BUDGET_EXCEEDED")
    require(seconds <= 600, "DEPLOYMENT_BUDGET_INVALID")
    return seconds


class DeploymentClient:
    """Use an already-discovered fixed-cluster DNS endpoint and in-memory ADC bearer.

    Each request owns its TLS connection. No proxies, redirects, request retries or kubectl
    retry machinery are used. Socket timeouts/checks are cooperative: DNS and blocked reads
    require the outer run_command process-group deadline for a hard execution bound.
    """

    def __init__(self, endpoint: str, token: str, deadline: float) -> None:
        require(
            type(endpoint) is str
            and fullmatch(r"https://[a-z0-9-]+(?:\.[a-z0-9-]+)*\.gke\.goog", endpoint) is not None,
            "DEPLOYMENT_ENDPOINT_INVALID",
        )
        require(
            type(token) is str
            and 0 < len(token) <= 8192
            and fullmatch(r"[A-Za-z0-9._~+/-]+=*", token) is not None,
            "DEPLOYMENT_TOKEN_INVALID",
        )
        remaining(deadline)
        self._host = endpoint[8:]
        self._token = token
        self.deadline = deadline

    def _request(self, method: str, path: str, patch: list[dict] | None = None) -> dict:
        timeout = remaining(self.deadline)
        headers = {"Authorization": "Bearer " + self._token, "Accept": "application/json"}
        payload = None
        if patch is not None:
            headers["Content-Type"] = "application/json-patch+json"
            payload = dumps(patch, allow_nan=False).encode("utf-8")
        failure = (
            "DEPLOYMENT_PATCH_OUTCOME_UNKNOWN_INSPECT_MANUALLY"
            if method == "PATCH"
            else "DEPLOYMENT_GET_FAILED"
        )
        try:
            with closing(
                HTTPSConnection(self._host, timeout=timeout, context=create_default_context())
            ) as connection:
                connection.request(method, path, body=payload, headers=headers)
                with connection.getresponse() as response:
                    status = response.status
                    data = bytearray()
                    while chunk := response.read1(min(65536, RESPONSE_LIMIT - len(data) + 1)):
                        remaining(self.deadline)
                        data.extend(chunk)
                        require(len(data) <= RESPONSE_LIMIT, "DEPLOYMENT_RESPONSE_LIMIT")
                    remaining(self.deadline)
        except HTTPException, OSError, ValueError:
            raise RuntimeError(failure) from None
        if method == "PATCH" and status in {400, 401, 403, 404, 409, 415, 422, 429}:
            raise RuntimeError("DEPLOYMENT_PATCH_REJECTED_INSPECT_MANUALLY")
        if status != 200:
            raise RuntimeError(failure)
        try:
            document = strict_json(bytes(data))
            require(type(document) is dict, "DEPLOYMENT_RESPONSE_INVALID")
        except ValueError, RecursionError:
            raise RuntimeError(failure) from None
        return document

    def get_deployment(self) -> dict:
        """Read only the fixed named Deployment."""
        return self._request("GET", DEPLOYMENT_PATH)

    def patch_image(
        self, before: dict, expected_uid: str, expected_spec_sha256: str, digest: str
    ) -> dict:
        """Send exactly one CAS image patch; never re-read/rebase a rejected mutation."""
        patch = image_patch(before, expected_uid, expected_spec_sha256, digest)
        after = self._request("PATCH", DEPLOYMENT_PATH, patch)
        verify_patch_response(before, after, expected_uid, expected_spec_sha256, digest)
        return after

    def get_service(self) -> dict:
        """Read the fixed Service so smoke traffic cannot silently use a changed selector."""
        return self._request("GET", "/api/v1/namespaces/finsecure-pay/services/finsecure-pay")

    def get_replica_sets(self) -> dict:
        """Observe matching ReplicaSets without broad cluster discovery."""
        return self._request("GET", REPLICA_SETS_PATH + SELECTOR)

    def get_pods(self) -> dict:
        """Observe matching Pods; ownership/image checks remain mandatory."""
        return self._request("GET", PODS_PATH + SELECTOR)
