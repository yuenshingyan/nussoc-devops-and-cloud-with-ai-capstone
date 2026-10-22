"""Verify startup settings without external services or environment leakage."""

from decimal import Decimal
from traceback import format_exception

from pydantic import ValidationError
from pytest import mark, raises

from finsecure_pay.config import Settings, load_settings
from finsecure_pay.schemas.transaction import TransactionRequest
from finsecure_pay.services.validation import validate_transaction


def test_settings_preserve_existing_defaults():
    settings = load_settings()

    assert settings.max_transaction_amount == Decimal("10000")
    assert settings.supported_currencies == frozenset({"SGD", "USD", "HKD"})


@mark.parametrize("amount", ["0.01", "125.50", "20000", "9" * 32])
def test_settings_parse_exact_amount_override(monkeypatch, amount):
    monkeypatch.setenv("FINSECURE_MAX_TRANSACTION_AMOUNT", amount)

    assert load_settings().max_transaction_amount == Decimal(amount)


@mark.parametrize(
    "amount", ["", "0", "-1", "NaN", "Infinity", "1e3", " 10", "+10", "1.000", "1" * 33]
)
def test_settings_reject_invalid_amount_override(monkeypatch, amount):
    monkeypatch.setenv("FINSECURE_MAX_TRANSACTION_AMOUNT", amount)

    with raises(ValueError, match="Invalid application configuration"):
        load_settings()


@mark.parametrize("currencies", ["SGD", "USD,HKD", "HKD,SGD,USD"])
def test_settings_parse_currency_subset(monkeypatch, currencies):
    monkeypatch.setenv("FINSECURE_SUPPORTED_CURRENCIES", currencies)

    assert load_settings().supported_currencies == frozenset(currencies.split(","))


@mark.parametrize("currencies", ["", "JPY", "EUR", "sgd", "SGD, USD", "SGD,", "SGD,SGD"])
def test_settings_reject_invalid_currency_allowlist(monkeypatch, currencies):
    monkeypatch.setenv("FINSECURE_SUPPORTED_CURRENCIES", currencies)

    with raises(ValueError, match="Invalid application configuration"):
        load_settings()


@mark.parametrize(
    "variable", ["FINSECURE_MAX_TRANSACTION_AMOUNT", "FINSECURE_SUPPORTED_CURRENCIES"]
)
def test_startup_error_does_not_echo_setting_values(monkeypatch, variable):
    monkeypatch.setenv(variable, "synthetic-secret-value")

    with raises(ValueError) as error:
        load_settings()

    assert "synthetic-secret-value" not in str(error.value)
    assert "synthetic-secret-value" not in "".join(format_exception(error.value))


def test_settings_ignore_unrelated_environment_variables(monkeypatch):
    monkeypatch.setenv("FINSECURE_UNRELATED_SETTING", "unused")

    assert load_settings() == Settings()


def test_settings_are_immutable():
    settings = Settings()

    with raises(ValidationError, match="frozen"):
        settings.max_transaction_amount = Decimal("50")


@mark.parametrize("amount", [1.5, True, Decimal("1.000"), Decimal("NaN"), Decimal("Infinity")])
def test_settings_reject_invalid_programmatic_amounts(amount):
    with raises(ValidationError):
        Settings(max_transaction_amount=amount)


def test_service_uses_supplied_settings_without_reading_environment(
    transaction_payload, monkeypatch
):
    monkeypatch.setenv("FINSECURE_MAX_TRANSACTION_AMOUNT", "9999")
    request = TransactionRequest(**transaction_payload)
    settings = Settings(
        max_transaction_amount=Decimal("100"), supported_currencies=frozenset({"USD"})
    )

    result = validate_transaction(request, settings=settings)

    assert result.valid is False
    assert result.errors == ["AMOUNT_LIMIT_EXCEEDED", "UNSUPPORTED_CURRENCY"]
    assert validate_transaction(request).valid is True
