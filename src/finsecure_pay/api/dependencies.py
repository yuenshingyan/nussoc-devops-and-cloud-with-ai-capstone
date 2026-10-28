"""HTTP-layer access to application-owned configuration."""

from fastapi import Request

from finsecure_pay.config import Settings
from finsecure_pay.observability.metrics import ApplicationMetrics


def get_settings(request: Request) -> Settings:
    """Return the validated settings snapshot created with this application."""
    return request.app.state.settings


def get_application_metrics(request: Request) -> ApplicationMetrics:
    """Return this application's isolated metrics registry and instruments."""
    return request.app.state.metrics
