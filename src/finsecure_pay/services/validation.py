"""Pure transaction-validation rules; no HTTP or external-system access."""

from decimal import Decimal

from finsecure_pay.schemas.transaction import (
    TransactionRequest,
    ValidationErrorCode,
    ValidationResponse,
)

MAX_TRANSACTION_AMOUNT = Decimal("10000")
SUPPORTED_CURRENCIES = frozenset({"SGD", "USD", "HKD"})
MAX_FRACTIONAL_DIGITS = 2


def validate_transaction(transaction: TransactionRequest) -> ValidationResponse:
    """Validate an already syntax-checked request without rounding or performing I/O."""
    amount = Decimal(transaction.amount)
    errors: list[ValidationErrorCode] = []

    if amount <= 0:
        errors.append("AMOUNT_NOT_POSITIVE")
    if amount > MAX_TRANSACTION_AMOUNT:
        errors.append("AMOUNT_LIMIT_EXCEEDED")
    if transaction.currency not in SUPPORTED_CURRENCIES:
        errors.append("UNSUPPORTED_CURRENCY")
    # Count supplied digits, including trailing zeros: silently normalizing would
    # accept a precision the caller was explicitly required not to send.
    if len(transaction.amount.partition(".")[2]) > MAX_FRACTIONAL_DIGITS:
        errors.append("AMOUNT_PRECISION_EXCEEDED")
    if transaction.sender_id == transaction.recipient_id:
        errors.append("SAME_ACCOUNT")

    return ValidationResponse(valid=not errors, errors=errors)
