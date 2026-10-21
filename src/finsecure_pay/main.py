"""FastAPI application construction."""

from fastapi import FastAPI

from finsecure_pay.api.health import router


def create_app() -> FastAPI:
    """Create an independent application instance for serving or testing."""
    app = FastAPI(
        title="FinSecure Pay",
        version="0.1.0",
        description="Transaction-validation API for the FinSecure Pay DevOps capstone.",
    )
    app.include_router(router)
    return app
