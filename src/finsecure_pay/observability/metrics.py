"""Application-owned Prometheus metrics with explicitly bounded label values."""

from prometheus_client import CollectorRegistry, Counter, Histogram, ProcessCollector

DURATION_BUCKETS_SECONDS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5)
VALIDATION_OUTCOMES = ("accepted", "rejected", "invalid")


class ApplicationMetrics:
    """Keep each application instance's metrics separate from the global registry."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self.requests = Counter(
            "finsecure_http_requests_total",
            "Finished or terminated HTTP ASGI invocations, excluding the exact metrics path.",
            ("route", "method", "status_class"),
            registry=self.registry,
        )
        self.duration = Histogram(
            "finsecure_http_request_duration_seconds",
            "Elapsed ASGI handling time in seconds, not client-perceived delivery time.",
            ("route", "method"),
            buckets=DURATION_BUCKETS_SECONDS,
            registry=self.registry,
        )
        self.exceptions = Counter(
            "finsecure_http_exceptions_total",
            "Unhandled non-cancellation exceptions escaping instrumented ASGI handling.",
            ("route", "method"),
            registry=self.registry,
        )
        self.validation = Counter(
            "finsecure_validation_outcomes_total",
            "Business evaluations or schema-invalid POST validate requests, not deliveries.",
            ("outcome",),
            registry=self.registry,
        )
        for outcome in VALIDATION_OUTCOMES:
            self.validation.labels(outcome=outcome)
        ProcessCollector(namespace="finsecure", registry=self.registry)

    def record_validation(self, outcome: str) -> None:
        """Record one known outcome without admitting caller-controlled label values."""
        if outcome not in VALIDATION_OUTCOMES:
            raise ValueError("Unknown validation metric outcome")
        self.validation.labels(outcome=outcome).inc()
