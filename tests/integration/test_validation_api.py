"""Test accepted, business-rejected, and malformed requests through the API."""

from pytest import mark


def test_validate_accepts_transaction(client, transaction_payload):
    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": []}


@mark.parametrize(
    ("updates", "errors"),
    [
        ({"amount": "0"}, ["AMOUNT_NOT_POSITIVE"]),
        ({"amount": "10000.01"}, ["AMOUNT_LIMIT_EXCEEDED"]),
        ({"currency": "EUR"}, ["UNSUPPORTED_CURRENCY"]),
        ({"amount": "0.001"}, ["AMOUNT_PRECISION_EXCEEDED"]),
        ({"recipient_id": "account_001"}, ["SAME_ACCOUNT"]),
    ],
)
def test_validate_returns_business_rejection_with_http_200(
    client, transaction_payload, updates, errors
):
    transaction_payload.update(updates)

    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 200
    assert response.json() == {"valid": False, "errors": errors}


@mark.parametrize(
    ("field", "value"),
    [
        ("amount", 125.50),
        ("amount", True),
        ("amount", None),
        ("amount", "NaN"),
        ("amount", "Infinity"),
        ("amount", "1e2"),
        ("amount", " 1.00"),
        ("amount", "1.00\n"),
        ("amount", "+1.00"),
        ("amount", ".50"),
        ("amount", "1."),
        ("amount", "1" * 33),
        ("currency", "sgd"),
        ("currency", "SG"),
        ("transaction_id", ""),
        ("transaction_id", "a" * 65),
        ("sender_id", " account_001"),
        ("sender_id", "account_001\n"),
        ("recipient_id", "用户"),
    ],
)
def test_validate_rejects_malformed_fields(client, transaction_payload, field, value):
    transaction_payload[field] = value

    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 422
    details = response.json()["detail"]
    assert details
    assert all(detail["loc"] == ["body", field] for detail in details)
    assert all(set(detail) == {"loc", "type", "msg"} for detail in details)


@mark.parametrize("field", ["transaction_id", "sender_id", "recipient_id", "amount", "currency"])
def test_validate_rejects_missing_fields(client, transaction_payload, field):
    del transaction_payload[field]

    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "missing"


def test_validate_redacts_unknown_field_names_and_values(client, transaction_payload):
    transaction_payload["synthetic-secret-field"] = "synthetic-secret-value"
    transaction_payload["amount"] = "synthetic-sensitive-amount"

    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 422
    assert "synthetic-secret" not in response.text
    assert "synthetic-sensitive" not in response.text
    assert {detail["type"] for detail in response.json()["detail"]} == {
        "extra_forbidden",
        "string_pattern_mismatch",
    }
    assert {tuple(detail["loc"]) for detail in response.json()["detail"]} == {
        ("body",),
        ("body", "amount"),
    }


def test_validate_redacts_invalid_json(client):
    response = client.post(
        "/validate",
        content='{"amount": synthetic-secret-value}',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert "synthetic-secret-value" not in response.text
    assert response.json()["detail"][0]["type"] == "json_invalid"
    assert response.json()["detail"][0]["loc"] == ["body"]


def test_validate_requires_post(client):
    response = client.get("/validate")

    assert response.status_code == 405
    assert "POST" in response.headers["allow"]


def test_openapi_documents_safe_request_error_schema(client):
    schema = client.get("/openapi.json").json()
    error_response = schema["paths"]["/validate"]["post"]["responses"]["422"]

    assert error_response["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/RequestErrorResponse"
    )
    assert set(schema["components"]["schemas"]["RequestErrorDetail"]["properties"]) == {
        "loc",
        "type",
        "msg",
    }
