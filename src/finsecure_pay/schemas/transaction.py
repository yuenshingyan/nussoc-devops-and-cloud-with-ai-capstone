"""Transaction request and business-validation response contracts."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

type TransactionIdentifier = Annotated[
    str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
]
type ValidationErrorCode = Literal[
    "AMOUNT_NOT_POSITIVE",
    "AMOUNT_LIMIT_EXCEEDED",
    "UNSUPPORTED_CURRENCY",
    "AMOUNT_PRECISION_EXCEEDED",
    "SAME_ACCOUNT",
]


class TransactionRequest(BaseModel):
    """Strict request syntax; business restrictions are checked by the service."""

    model_config = ConfigDict(strict=True, extra="forbid")

    transaction_id: TransactionIdentifier
    sender_id: TransactionIdentifier
    recipient_id: TransactionIdentifier
    amount: Annotated[
        str,
        Field(
            min_length=1,
            max_length=32,
            pattern=r"^-?[0-9]+(?:\.[0-9]+)?$",
            description="Plain decimal string; JSON numbers and exponent notation are rejected.",
        ),
    ]
    currency: Annotated[str, Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")]


class ValidationResponse(BaseModel):
    """Business-rule result with all applicable error codes in documented order."""

    valid: bool
    errors: list[ValidationErrorCode]
