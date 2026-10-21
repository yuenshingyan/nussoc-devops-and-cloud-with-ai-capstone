"""Response schema for the application liveness endpoint."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Stable response indicating that the application can serve requests."""

    status: Literal["healthy"]
