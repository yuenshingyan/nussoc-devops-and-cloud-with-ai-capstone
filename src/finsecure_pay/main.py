"""FastAPI application construction."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from finsecure_pay.api.errors import handle_request_validation_error
from finsecure_pay.api.health import health_router
from finsecure_pay.api.validation import validation_router


def create_app() -> FastAPI:
    """Create an independent application instance for serving or testing."""
    app = FastAPI(
        title="FinSecure Pay",
        version="0.1.0",
        description="Transaction-validation API for the FinSecure Pay DevOps capstone.",
    )
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.include_router(health_router)
    app.include_router(validation_router)
    return app
