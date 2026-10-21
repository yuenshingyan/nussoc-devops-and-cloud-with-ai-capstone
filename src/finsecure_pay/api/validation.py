"""Transaction-validation endpoint."""

from fastapi import APIRouter

from finsecure_pay.schemas.errors import RequestErrorResponse
from finsecure_pay.schemas.transaction import TransactionRequest, ValidationResponse
from finsecure_pay.services.validation import validate_transaction

validation_router = APIRouter(tags=["transactions"])


@validation_router.post(
    "/validate",
    response_model=ValidationResponse,
    responses={422: {"model": RequestErrorResponse, "description": "Malformed request"}},
)
async def post_validation(transaction: TransactionRequest) -> ValidationResponse:
    """Return business validation results; this endpoint never transfers money."""
    return validate_transaction(transaction)
