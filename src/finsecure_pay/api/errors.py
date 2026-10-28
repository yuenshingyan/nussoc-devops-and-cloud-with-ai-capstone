"""Redact framework request-validation errors before returning them to clients."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from finsecure_pay.api.dependencies import get_application_metrics
from finsecure_pay.schemas.errors import RequestErrorDetail, RequestErrorResponse
from finsecure_pay.schemas.transaction import TransactionRequest


async def handle_request_validation_error(
    request: Request, exception: RequestValidationError
) -> JSONResponse:
    """Return schema error metadata without echoing arbitrary fields or submitted values."""
    if request.method == "POST" and request.scope["path"] == "/validate":
        get_application_metrics(request).record_validation("invalid")
    details = []
    for error in exception.errors():
        location = ["body"]
        original_location = error["loc"]
        # Even an unknown field name can contain sensitive caller-supplied text.
        if (
            len(original_location) > 1
            and original_location[0] == "body"
            and original_location[1] in TransactionRequest.model_fields
        ):
            location.append(original_location[1])
        details.append(
            RequestErrorDetail(
                loc=location,
                type=error["type"],
                msg="Invalid request value. Check the API contract.",
            )
        )

    response = RequestErrorResponse(detail=details)
    return JSONResponse(status_code=422, content=response.model_dump())
