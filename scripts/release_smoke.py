"""Single-attempt synthetic smoke checks against the approved public HTTP demo endpoint."""

from contextlib import closing
from http.client import HTTPConnection, HTTPException
from json import dumps

from scripts.release_archive import strict_json
from scripts.release_deployment import require
from scripts.release_http import RESPONSE_LIMIT, remaining

PUBLIC_HOST = "35.198.197.186"


def verify_service(service: dict) -> None:
    """Require the approved endpoint and routing before mutation and again before smoke."""
    require(
        type(service) is dict
        and service.get("apiVersion") == "v1"
        and service.get("kind") == "Service"
        and type(service.get("metadata")) is dict
        and type(service.get("spec")) is dict
        and type(service.get("status")) is dict,
        "DEPLOYMENT_SERVICE_INVALID",
    )
    metadata, spec = service["metadata"], service["spec"]
    ports = spec.get("ports")
    balancer = service["status"].get("loadBalancer")
    require(
        metadata.get("name") == "finsecure-pay"
        and metadata.get("namespace") == "finsecure-pay"
        and metadata.get("deletionTimestamp") is None
        and spec.get("type") == "LoadBalancer"
        and spec.get("selector") == {"app.kubernetes.io/name": "finsecure-pay"}
        and type(ports) is list
        and len(ports) == 1
        and type(ports[0]) is dict
        and type(ports[0].get("port")) is int
        and ports[0]["port"] == 80
        and ports[0].get("targetPort") == "http"
        and ports[0].get("protocol") == "TCP"
        and type(balancer) is dict
        and type(balancer.get("ingress")) is list
        and len(balancer["ingress"]) == 1
        and type(balancer["ingress"][0]) is dict
        and balancer["ingress"][0].get("ip") == PUBLIC_HOST,
        "DEPLOYMENT_SERVICE_CHANGED",
    )


def smoke_request(
    path: str, payload: dict | None, expected_status: int, expected_body: dict, deadline: float
) -> None:
    """Do not forward credentials, follow redirects, retry or expose response/request bodies.

    Run inside the bounded worker command adapter for hard DNS/I/O cancellation. This
    plaintext endpoint is approved only for synthetic demo data, never real payments.
    """
    body = dumps(payload).encode("utf-8") if payload is not None else None
    try:
        with closing(HTTPConnection(PUBLIC_HOST, 80, timeout=remaining(deadline))) as connection:
            connection.request(
                "POST" if payload is not None else "GET",
                path,
                body=body,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            with connection.getresponse() as response:
                status = response.status
                data = bytearray()
                while chunk := response.read1(min(65536, RESPONSE_LIMIT - len(data) + 1)):
                    remaining(deadline)
                    data.extend(chunk)
                    if len(data) > RESPONSE_LIMIT:
                        raise ValueError("SMOKE_RESPONSE_LIMIT")
                remaining(deadline)
        actual = strict_json(bytes(data))
        matches = dumps(actual, sort_keys=True, allow_nan=False) == dumps(
            expected_body, sort_keys=True
        )
    except HTTPException, OSError, ValueError, RecursionError:
        raise RuntimeError("DEPLOYMENT_SMOKE_REQUEST_FAILED") from None
    if status != expected_status or not matches:
        raise RuntimeError("DEPLOYMENT_SMOKE_RESPONSE_MISMATCH")


def verify_smoke(deadline: float) -> dict:
    """Check health, success, business rejection and strict malformed-input rejection once."""
    remaining(deadline)
    payload = {
        "transaction_id": "release_smoke_001",
        "sender_id": "synthetic_sender",
        "recipient_id": "synthetic_recipient",
        "amount": "125.50",
        "currency": "SGD",
    }
    cases = [
        ("/health", None, 200, {"status": "healthy"}),
        ("/validate", payload, 200, {"valid": True, "errors": []}),
        (
            "/validate",
            {**payload, "amount": "0"},
            200,
            {"valid": False, "errors": ["AMOUNT_NOT_POSITIVE"]},
        ),
        (
            "/validate",
            {**payload, "amount": 125},
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
    for path, data, status, expected in cases:
        smoke_request(path, data, status, expected, deadline)
    return {"status": "smoke_verified", "cases": len(cases), "synthetic_data_only": True}
