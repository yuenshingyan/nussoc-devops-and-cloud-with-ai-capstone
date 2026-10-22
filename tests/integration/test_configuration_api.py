"""Verify environment settings reach HTTP validation without changing its schema."""

from fastapi.testclient import TestClient
from pytest import mark, raises

from finsecure_pay.main import create_app


@mark.parametrize(
    ("limit", "amount", "expected"),
    [
        ("125.50", "125.50", {"valid": True, "errors": []}),
        ("125.50", "125.51", {"valid": False, "errors": ["AMOUNT_LIMIT_EXCEEDED"]}),
        ("20000", "15000", {"valid": True, "errors": []}),
    ],
)
def test_api_uses_configured_amount_limit(
    monkeypatch, transaction_payload, limit, amount, expected
):
    monkeypatch.setenv("FINSECURE_MAX_TRANSACTION_AMOUNT", limit)
    transaction_payload["amount"] = amount

    with TestClient(create_app()) as client:
        response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 200
    assert response.json() == expected


@mark.parametrize(
    ("currency", "expected"),
    [
        ("USD", {"valid": True, "errors": []}),
        ("SGD", {"valid": False, "errors": ["UNSUPPORTED_CURRENCY"]}),
    ],
)
def test_api_uses_configured_currency_subset(monkeypatch, transaction_payload, currency, expected):
    monkeypatch.setenv("FINSECURE_SUPPORTED_CURRENCIES", "USD")
    transaction_payload["currency"] = currency

    with TestClient(create_app()) as client:
        response = client.post("/validate", json=transaction_payload)
        health = client.get("/health")

    assert response.status_code == 200
    assert response.json() == expected
    assert health.status_code == 200 and health.json() == {"status": "healthy"}


def test_applications_keep_independent_startup_settings(monkeypatch, transaction_payload):
    monkeypatch.setenv("FINSECURE_MAX_TRANSACTION_AMOUNT", "100")
    first = create_app()
    monkeypatch.setenv("FINSECURE_MAX_TRANSACTION_AMOUNT", "200")
    second = create_app()
    monkeypatch.setenv("FINSECURE_MAX_TRANSACTION_AMOUNT", "1")

    with TestClient(first) as first_client, TestClient(second) as second_client:
        assert first_client.post("/validate", json=transaction_payload).json() == {
            "valid": False,
            "errors": ["AMOUNT_LIMIT_EXCEEDED"],
        }
        assert second_client.post("/validate", json=transaction_payload).json() == {
            "valid": True,
            "errors": [],
        }


@mark.parametrize(
    ("variable", "value"),
    [("FINSECURE_MAX_TRANSACTION_AMOUNT", "0"), ("FINSECURE_SUPPORTED_CURRENCIES", "")],
)
def test_invalid_configuration_prevents_application_creation(monkeypatch, variable, value):
    monkeypatch.setenv(variable, value)

    with raises(ValueError, match="Invalid application configuration"):
        create_app()
