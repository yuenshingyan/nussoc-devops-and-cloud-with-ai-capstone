"""Observe HTTP ASGI handling without buffering bodies or changing error behaviour."""

from time import perf_counter

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from finsecure_pay.observability.metrics import ApplicationMetrics


class HttpMetricsMiddleware:
    """Preserve ASGI messages, exceptions and cancellation while bounding every label."""

    def __init__(self, app: ASGIApp, metrics: ApplicationMetrics) -> None:
        self.app = app
        self.metrics = metrics

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] == "/metrics":
            await self.app(scope, receive, send)
            return
        route = scope["path"] if scope["path"] in ("/health", "/validate") else "other"
        method = scope["method"] if scope["method"] in ("GET", "POST") else "OTHER"
        status_class = "no_response"
        started = perf_counter()

        async def observe_send(message: Message) -> None:
            nonlocal status_class
            if message["type"] == "http.response.start":
                status = message["status"]
                status_class = (
                    f"{status // 100}xx" if type(status) is int and 100 <= status < 600 else "other"
                )
            await send(message)

        try:
            await self.app(scope, receive, observe_send)
        except Exception:
            # Cancellation is a BaseException and must propagate without an error count.
            self.metrics.exceptions.labels(route=route, method=method).inc()
            raise
        finally:
            self.metrics.requests.labels(
                route=route, method=method, status_class=status_class
            ).inc()
            self.metrics.duration.labels(route=route, method=method).observe(
                perf_counter() - started
            )
