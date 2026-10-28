"""Metrics are an additive, bounded public contract, not transaction payload storage."""

from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families
from pytest import mark

from finsecure_pay.main import create_app


def sample(client: TestClient, name: str, labels: dict[str, str]) -> float:
    """Read a named sample from actual HTTP exposition, treating absent series as zero."""
    response = client.get("/metrics")
    assert response.status_code == 200
    for family in text_string_to_metric_families(response.text):
        for item in family.samples:
            if item.name == name and item.labels == labels:
                return item.value
    return 0


def test_metrics_exposes_text_but_not_openapi_or_default_python_collectors(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; version=1.0.0; charset=utf-8"
    assert "finsecure_validation_outcomes_total" in response.text
    assert "python_info" not in response.text
    assert "python_gc_" not in response.text
    assert "/metrics" not in client.get("/openapi.json").json()["paths"]


@mark.parametrize("method", ["get", "post", "head", "options"])
def test_exact_metrics_path_is_excluded_for_every_method(client, method):
    response = client.request(method, "/metrics")
    assert response.status_code == (200 if method == "get" else 405)
    text = client.get("/metrics").text
    families = list(text_string_to_metric_families(text))
    assert not any(
        item.name.startswith("finsecure_http_") for family in families for item in family.samples
    )


def test_health_is_counted_once_and_latency_histogram_is_observed(client):
    assert client.get("/health").json() == {"status": "healthy"}
    labels = {"route": "/health", "method": "GET"}
    assert sample(client, "finsecure_http_requests_total", {**labels, "status_class": "2xx"}) == 1
    assert sample(client, "finsecure_http_request_duration_seconds_count", labels) == 1
    assert (
        sample(client, "finsecure_http_request_duration_seconds_bucket", {**labels, "le": "+Inf"})
        == 1
    )
    assert sample(client, "finsecure_http_request_duration_seconds_sum", labels) >= 0
    for outcome in ("accepted", "rejected", "invalid"):
        assert sample(client, "finsecure_validation_outcomes_total", {"outcome": outcome}) == 0


@mark.parametrize(
    "changes,outcome,status",
    [({}, "accepted", 200), ({"amount": "0"}, "rejected", 200), ({"amount": 1}, "invalid", 422)],
)
def test_each_validation_outcome_is_counted_once(
    client, transaction_payload, changes, outcome, status
):
    response = client.post("/validate", json={**transaction_payload, **changes})
    assert response.status_code == status
    assert sample(client, "finsecure_validation_outcomes_total", {"outcome": outcome}) == 1
    assert (
        sample(
            client,
            "finsecure_http_requests_total",
            {"route": "/validate", "method": "POST", "status_class": str(status // 100) + "xx"},
        )
        == 1
    )
    assert (
        sample(client, "finsecure_http_exceptions_total", {"route": "/validate", "method": "POST"})
        == 0
    )


def test_multiple_rule_failures_count_one_rejected_evaluation(client, transaction_payload):
    payload = {
        **transaction_payload,
        "amount": "10000.001",
        "currency": "EUR",
        "recipient_id": transaction_payload["sender_id"],
    }
    response = client.post("/validate", json=payload)
    assert len(response.json()["errors"]) == 4
    assert sample(client, "finsecure_validation_outcomes_total", {"outcome": "rejected"}) == 1


@mark.parametrize("body", ['{"broken":', "{}", '{"amount":null}'])
def test_malformed_json_or_multiple_schema_errors_count_one_invalid_request(client, body):
    assert (
        client.post(
            "/validate", content=body, headers={"content-type": "application/json"}
        ).status_code
        == 422
    )
    assert sample(client, "finsecure_validation_outcomes_total", {"outcome": "invalid"}) == 1


@mark.parametrize(
    "method,path,route,status_class",
    [
        ("GET", "/validate", "/validate", "4xx"),
        ("DELETE", "/unknown-private-path", "other", "4xx"),
        ("SECRET_METHOD", "/unknown-private-path", "other", "4xx"),
        ("GET", "/metrics/", "other", "3xx"),
    ],
)
def test_http_failures_and_redirects_use_bounded_labels_without_validation_outcomes(
    client, method, path, route, status_class
):
    client.request(method, path, follow_redirects=False)
    assert (
        sample(
            client,
            "finsecure_http_requests_total",
            {
                "route": route,
                "method": method if method in ("GET", "POST") else "OTHER",
                "status_class": status_class,
            },
        )
        == 1
    )
    assert sample(client, "finsecure_validation_outcomes_total", {"outcome": "invalid"}) == 0


def test_metrics_do_not_include_synthetic_private_input(client, transaction_payload):
    sentinel = "PrivateSyntheticSentinel123"
    payload = {**transaction_payload, "transaction_id": sentinel, "sender_id": sentinel + "sender"}
    client.post("/validate?private=" + sentinel, json=payload, headers={"X-Private": sentinel})
    client.post("/validate", json={**payload, sentinel: sentinel})
    client.get("/" + sentinel)
    text = client.get("/metrics").text
    assert sentinel not in text
    allowed_keys = {"route", "method", "status_class", "outcome", "le"}
    for family in text_string_to_metric_families(text):
        for item in family.samples:
            assert set(item.labels) <= allowed_keys


def test_application_instances_do_not_share_counters():
    with TestClient(create_app()) as first, TestClient(create_app()) as second:
        first.get("/health")
        labels = {"route": "/health", "method": "GET", "status_class": "2xx"}
        assert sample(first, "finsecure_http_requests_total", labels) == 1
        assert sample(second, "finsecure_http_requests_total", labels) == 0


def test_unexpected_exception_preserves_response_and_records_separate_signal():
    def fail() -> None:
        raise RuntimeError("PrivateSyntheticExceptionText")

    app = create_app()
    app.add_api_route("/synthetic-error", fail)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/synthetic-error")
        assert response.status_code == 500
        labels = {"route": "other", "method": "GET"}
        assert sample(client, "finsecure_http_exceptions_total", labels) == 1
        # The outer framework creates this 500 after the inner observer re-raises.
        assert (
            sample(
                client, "finsecure_http_requests_total", {**labels, "status_class": "no_response"}
            )
            == 1
        )
        assert "PrivateSyntheticExceptionText" not in client.get("/metrics").text
        assert sample(client, "finsecure_validation_outcomes_total", {"outcome": "accepted"}) == 0
