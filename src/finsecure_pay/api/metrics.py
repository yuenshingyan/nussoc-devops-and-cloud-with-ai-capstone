"""Read-only Prometheus exposition for the local monitoring demo."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from finsecure_pay.api.dependencies import get_application_metrics
from finsecure_pay.observability.metrics import ApplicationMetrics

metrics_router = APIRouter()


@metrics_router.get("/metrics", include_in_schema=False)
def get_metrics(
    metrics: Annotated[ApplicationMetrics, Depends(get_application_metrics)],
) -> Response:
    """Expose only this application's registry; do not start a separate listener."""
    return Response(
        generate_latest(metrics.registry), headers={"Content-Type": CONTENT_TYPE_LATEST}
    )
