"""Application liveness endpoint."""

from fastapi import APIRouter

from finsecure_pay.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Report application liveness without probing external dependencies."""
    return HealthResponse(status="healthy")
