"""Validated, immutable application settings loaded once per application instance."""

from decimal import Decimal
from os import getenv
from re import fullmatch
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

type SupportedCurrency = Literal["SGD", "USD", "HKD"]


class Settings(BaseModel):
    """Validation policy; configured currencies share the existing two-decimal rule."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", validate_default=True)

    max_transaction_amount: Decimal = Field(default=Decimal("10000"), gt=0, allow_inf_nan=False)
    supported_currencies: frozenset[SupportedCurrency] = Field(
        default=frozenset({"SGD", "USD", "HKD"}), min_length=1
    )

    @field_validator("max_transaction_amount", mode="before")
    @classmethod
    def parse_amount(cls, value: object) -> object:
        """Accept explicitly documented plain decimal strings, never floating-point input."""
        if isinstance(value, str):
            if len(value) > 32 or fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", value) is None:
                raise ValueError("Use a plain decimal string with at most two fractional digits")
            return Decimal(value)
        return value

    @field_validator("max_transaction_amount")
    @classmethod
    def check_amount_precision(cls, value: Decimal) -> Decimal:
        """Reject excess precision in programmatically supplied Decimal values too."""
        if value.as_tuple().exponent < -2:
            raise ValueError("At most two fractional digits are allowed")
        return value

    @field_validator("supported_currencies", mode="before")
    @classmethod
    def parse_currencies(cls, value: object) -> object:
        """Parse an exact uppercase comma-separated allowlist without silent trimming."""
        if isinstance(value, str):
            currencies = value.split(",")
            if len(currencies) != len(set(currencies)):
                raise ValueError("Currencies must not repeat")
            return frozenset(currencies)
        return value


DEFAULT_SETTINGS = Settings()


def load_settings() -> Settings:
    """Read only known environment variables and fail startup without echoing bad values."""
    values = {}
    for environment_name, field_name in [
        ("FINSECURE_MAX_TRANSACTION_AMOUNT", "max_transaction_amount"),
        ("FINSECURE_SUPPORTED_CURRENCIES", "supported_currencies"),
    ]:
        value = getenv(environment_name)
        if value is not None:
            values[field_name] = value
    try:
        return Settings.model_validate(values)
    except ValidationError:
        raise ValueError(
            "Invalid application configuration: check FINSECURE_MAX_TRANSACTION_AMOUNT "
            "and FINSECURE_SUPPORTED_CURRENCIES against the documented settings contract."
        ) from None
