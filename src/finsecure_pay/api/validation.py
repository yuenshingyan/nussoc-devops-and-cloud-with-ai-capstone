"""Transaction-validation endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from finsecure_pay.api.dependencies import get_application_metrics, get_settings
from finsecure_pay.config import Settings
from finsecure_pay.observability.metrics import ApplicationMetrics
from finsecure_pay.schemas.errors import RequestErrorResponse
from finsecure_pay.schemas.transaction import TransactionRequest, ValidationResponse
from finsecure_pay.services.validation import validate_transaction

validation_router = APIRouter(tags=["transactions"])


@validation_router.post(
    "/validate",
    response_model=ValidationResponse,
    responses={422: {"model": RequestErrorResponse, "description": "Malformed request"}},
)
async def post_validation(
    transaction: TransactionRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    metrics: Annotated[ApplicationMetrics, Depends(get_application_metrics)],
) -> ValidationResponse:
    """Return business validation results; this endpoint never transfers money."""
    result = validate_transaction(transaction, settings=settings)
    metrics.record_validation("accepted" if result.valid else "rejected")
    return result
