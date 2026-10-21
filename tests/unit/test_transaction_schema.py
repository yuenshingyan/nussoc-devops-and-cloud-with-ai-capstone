"""Exercise strict request syntax without HTTP or business-rule evaluation."""

from pydantic import ValidationError
from pytest import mark, raises

from finsecure_pay.schemas.transaction import TransactionRequest


@mark.parametrize("field", ["transaction_id", "sender_id", "recipient_id"])
@mark.parametrize("identifier", ["a", "A" * 64, "Account-001_test"])
def test_schema_preserves_valid_identifier_boundaries(transaction_payload, field, identifier):
    transaction_payload[field] = identifier

    request = TransactionRequest(**transaction_payload)

    assert request.model_dump() == transaction_payload


@mark.parametrize("field", ["transaction_id", "sender_id", "recipient_id"])
@mark.parametrize(
    "identifier",
    ["", "a" * 65, "account\n", " account", "account ", "a.b", "é", "e\u0301", "a\x00b"],
)
def test_schema_rejects_invalid_identifiers_without_normalizing(
    transaction_payload, field, identifier
):
    transaction_payload[field] = identifier

    with raises(ValidationError) as error:
        TransactionRequest(**transaction_payload)

    assert error.value.errors()[0]["loc"] == (field,)


@mark.parametrize(
    "amount", ["", "-", ".", "１２.５０", "1_000.00", "1,000.00", "0x10", "-Infinity", "1.00\r\n"]
)
def test_schema_rejects_non_decimal_amount_syntax(transaction_payload, amount):
    transaction_payload["amount"] = amount

    with raises(ValidationError) as error:
        TransactionRequest(**transaction_payload)

    assert error.value.errors()[0]["loc"] == ("amount",)


def test_schema_preserves_full_32_character_decimal(transaction_payload):
    transaction_payload["amount"] = "10000." + "0" * 25 + "1"

    request = TransactionRequest(**transaction_payload)

    assert len(request.amount) == 32
    assert request.amount == transaction_payload["amount"]
