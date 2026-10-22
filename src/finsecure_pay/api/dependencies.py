"""HTTP-layer access to application-owned configuration."""

from fastapi import Request

from finsecure_pay.config import Settings


def get_settings(request: Request) -> Settings:
    """Return the validated settings snapshot created with this application."""
    return request.app.state.settings
