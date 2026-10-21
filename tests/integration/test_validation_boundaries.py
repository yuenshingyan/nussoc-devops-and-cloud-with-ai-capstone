"""Verify boundary behavior through the serialized JSON API contract."""

from pytest import mark


@mark.parametrize("field", ["transaction_id", "sender_id", "recipient_id", "amount", "currency"])
@mark.parametrize("value", [None, 1, False, [], {"synthetic-sensitive-key": "synthetic-value"}])
def test_validate_rejects_non_string_fields(client, transaction_payload, field, value):
    transaction_payload[field] = value

    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", field],
                "type": "string_type",
                "msg": "Invalid request value. Check the API contract.",
            }
        ]
    }
    assert "synthetic-sensitive-key" not in response.text
    assert "synthetic-value" not in response.text


@mark.parametrize("body", ["null", "[]", "123", "true", '"synthetic-secret-body"'])
def test_validate_rejects_non_object_json_body(client, body):
    response = client.post("/validate", content=body, headers={"content-type": "application/json"})

    assert response.status_code == 422
    details = response.json()["detail"]
    assert details
    assert all(detail["loc"] == ["body"] for detail in details)
    assert all(set(detail) == {"loc", "type", "msg"} for detail in details)
    assert "synthetic-secret-body" not in response.text


def test_validate_rejects_absent_body(client):
    response = client.post("/validate")

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body"]
    assert response.json()["detail"][0]["type"] == "missing"


def test_validate_reports_all_missing_fields_without_business_result(client):
    response = client.post("/validate", json={})

    assert response.status_code == 422
    assert set(response.json()) == {"detail"}
    details = response.json()["detail"]
    assert len(details) == 5
    assert {detail["loc"][1] for detail in details} == {
        "transaction_id",
        "sender_id",
        "recipient_id",
        "amount",
        "currency",
    }
    assert all(detail["type"] == "missing" for detail in details)


@mark.parametrize("currency", ["SGD", "USD", "HKD"])
@mark.parametrize("amount", ["0.01", "10000.00", "0" * 28 + "1.00"])
def test_validate_accepts_amount_boundaries_in_each_currency(
    client, transaction_payload, currency, amount
):
    transaction_payload.update(currency=currency, amount=amount)

    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": []}


@mark.parametrize("identifier_length", [1, 64])
def test_validate_accepts_identifier_length_boundaries(
    client, transaction_payload, identifier_length
):
    transaction_payload.update(
        transaction_id="t" * identifier_length,
        sender_id="s" * identifier_length,
        recipient_id="r" * identifier_length,
    )

    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": []}


@mark.parametrize("field", ["transaction_id", "sender_id", "recipient_id"])
def test_validate_rejects_identifier_above_length_limit(client, transaction_payload, field):
    transaction_payload[field] = "a" * 65

    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]


@mark.parametrize("amount", ["-0", "-0.00", "0.00"])
def test_validate_rejects_all_zero_amount_forms(client, transaction_payload, amount):
    transaction_payload["amount"] = amount

    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 200
    assert response.json() == {"valid": False, "errors": ["AMOUNT_NOT_POSITIVE"]}


@mark.parametrize("amount", ["0.001", "1.000", "9999." + "9" * 27])
def test_validate_rejects_excess_precision_without_rounding(client, transaction_payload, amount):
    transaction_payload["amount"] = amount

    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 200
    assert response.json() == {"valid": False, "errors": ["AMOUNT_PRECISION_EXCEEDED"]}


def test_validate_preserves_tiny_difference_above_maximum(client, transaction_payload):
    transaction_payload["amount"] = "10000." + "0" * 25 + "1"

    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 200
    assert response.json() == {
        "valid": False,
        "errors": ["AMOUNT_LIMIT_EXCEEDED", "AMOUNT_PRECISION_EXCEEDED"],
    }


def test_validate_returns_all_rejections_in_documented_order(client, transaction_payload):
    transaction_payload.update(amount="-0.001", currency="EUR", recipient_id="account_001")

    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 200
    assert response.json() == {
        "valid": False,
        "errors": [
            "AMOUNT_NOT_POSITIVE",
            "UNSUPPORTED_CURRENCY",
            "AMOUNT_PRECISION_EXCEEDED",
            "SAME_ACCOUNT",
        ],
    }


def test_validate_case_distinct_accounts_remain_distinct(client, transaction_payload):
    transaction_payload.update(sender_id="Account", recipient_id="account")

    response = client.post("/validate", json=transaction_payload)

    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": []}


def test_validate_repeated_request_has_no_deduplication_side_effect(client, transaction_payload):
    for _ in range(2):
        response = client.post("/validate", json=transaction_payload)

        assert response.status_code == 200
        assert response.json() == {"valid": True, "errors": []}


def test_validate_rejection_does_not_affect_next_request(client, transaction_payload):
    rejected = client.post("/validate", json={**transaction_payload, "amount": "0"})
    accepted = client.post("/validate", json=transaction_payload)

    assert rejected.json() == {"valid": False, "errors": ["AMOUNT_NOT_POSITIVE"]}
    assert accepted.status_code == 200
    assert accepted.json() == {"valid": True, "errors": []}


def test_openapi_documents_required_fields_and_forbids_extra_properties(client):
    schema = client.get("/openapi.json").json()
    request = schema["components"]["schemas"]["TransactionRequest"]

    assert set(request["required"]) == {
        "transaction_id",
        "sender_id",
        "recipient_id",
        "amount",
        "currency",
    }
    assert request["additionalProperties"] is False
    assert request["properties"]["amount"]["type"] == "string"
    assert request["properties"]["amount"]["maxLength"] == 32
