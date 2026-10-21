"""Test business rules independently of HTTP and external services."""

from pytest import mark

from finsecure_pay.schemas.transaction import TransactionRequest
from finsecure_pay.services.validation import validate_transaction


@mark.parametrize("currency", ["SGD", "USD", "HKD"])
def test_validation_accepts_supported_currency(transaction_payload, currency):
    transaction_payload["currency"] = currency

    result = validate_transaction(TransactionRequest(**transaction_payload))

    assert result.valid is True
    assert result.errors == []


@mark.parametrize("amount", ["0.01", "1", "10000", "10000.00"])
def test_validation_accepts_amount_within_limits(transaction_payload, amount):
    transaction_payload["amount"] = amount

    result = validate_transaction(TransactionRequest(**transaction_payload))

    assert result.valid is True
    assert result.errors == []


@mark.parametrize(
    ("amount", "expected"),
    [
        ("0", "AMOUNT_NOT_POSITIVE"),
        ("-0.00", "AMOUNT_NOT_POSITIVE"),
        ("-0.01", "AMOUNT_NOT_POSITIVE"),
        ("10000.01", "AMOUNT_LIMIT_EXCEEDED"),
        ("1.001", "AMOUNT_PRECISION_EXCEEDED"),
        ("1.000", "AMOUNT_PRECISION_EXCEEDED"),
    ],
)
def test_validation_rejects_invalid_amount(transaction_payload, amount, expected):
    transaction_payload["amount"] = amount

    result = validate_transaction(TransactionRequest(**transaction_payload))

    assert result.valid is False
    assert result.errors == [expected]


def test_validation_reports_all_applicable_errors_in_order(transaction_payload):
    transaction_payload.update(amount="10000.001", currency="EUR", recipient_id="account_001")

    result = validate_transaction(TransactionRequest(**transaction_payload))

    assert result.valid is False
    assert result.errors == [
        "AMOUNT_LIMIT_EXCEEDED",
        "UNSUPPORTED_CURRENCY",
        "AMOUNT_PRECISION_EXCEEDED",
        "SAME_ACCOUNT",
    ]


def test_validation_compares_account_identifiers_case_sensitively(transaction_payload):
    transaction_payload.update(sender_id="account_001", recipient_id="ACCOUNT_001")

    result = validate_transaction(TransactionRequest(**transaction_payload))

    assert result.valid is True
    assert result.errors == []
