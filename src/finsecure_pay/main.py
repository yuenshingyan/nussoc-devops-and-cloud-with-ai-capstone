"""FastAPI application construction."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create an independent application instance for serving or testing."""
    return FastAPI(
        title="FinSecure Pay",
        version="0.1.0",
        description="Transaction-validation API for the FinSecure Pay DevOps capstone.",
    )
