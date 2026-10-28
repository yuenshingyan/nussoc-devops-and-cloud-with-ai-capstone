"""Use real registries and synthetic ASGI applications to test instrumentation semantics."""

from asyncio import CancelledError, run
from unittest.mock import Mock

from prometheus_client import generate_latest
from pytest import MonkeyPatch, mark, raises
from starlette.types import Message, Receive, Scope, Send

from finsecure_pay.observability.http import HttpMetricsMiddleware
from finsecure_pay.observability.metrics import ApplicationMetrics


async def receive() -> Message:
    """Return synthetic request data only if the application explicitly receives it."""
    return {"type": "http.request", "body": b"private synthetic body", "more_body": False}


async def discard(message: Message) -> None:
    """Accept a synthetic ASGI output without a real network resource."""


@mark.parametrize(
    "status,expected",
    [(101, "1xx"), (200, "2xx"), (307, "3xx"), (422, "4xx"), (500, "5xx"), (700, "other")],
)
def test_status_class_and_monotonic_duration_are_recorded_once(
    monkeypatch: MonkeyPatch, status, expected
):
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({"type": "http.response.body", "body": b"first", "more_body": True})
        await send({"type": "http.response.body", "body": b"last", "more_body": False})

    monkeypatch.setattr(
        "finsecure_pay.observability.http.perf_counter", Mock(side_effect=[10, 10.125])
    )
    metrics = ApplicationMetrics()
    run(
        HttpMetricsMiddleware(app, metrics)(
            {"type": "http", "path": "/health", "method": "GET"}, receive, discard
        )
    )
    labels = {"route": "/health", "method": "GET"}
    assert (
        metrics.registry.get_sample_value(
            "finsecure_http_requests_total", {**labels, "status_class": expected}
        )
        == 1
    )
    assert (
        metrics.registry.get_sample_value("finsecure_http_request_duration_seconds_sum", labels)
        == 0.125
    )
    assert (
        metrics.registry.get_sample_value("finsecure_http_request_duration_seconds_count", labels)
        == 1
    )


@mark.parametrize("cancel", [False, True])
@mark.parametrize("started_response", [False, True])
def test_errors_and_cancellation_propagate_without_fabricated_responses(cancel, started_response):
    error = CancelledError("synthetic-private") if cancel else RuntimeError("synthetic-private")
    sent = []

    async def send(message: Message) -> None:
        sent.append(message)

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        if started_response:
            await send({"type": "http.response.start", "status": 200, "headers": []})
        raise error

    metrics = ApplicationMetrics()
    with raises(type(error)) as caught:
        run(
            HttpMetricsMiddleware(app, metrics)(
                {"type": "http", "path": "/unknown-private", "method": "PRIVATE"}, receive, send
            )
        )
    assert caught.value is error
    assert len(sent) == int(started_response)
    labels = {"route": "other", "method": "OTHER"}
    assert (
        metrics.registry.get_sample_value(
            "finsecure_http_requests_total",
            {**labels, "status_class": "2xx" if started_response else "no_response"},
        )
        == 1
    )
    assert (metrics.registry.get_sample_value("finsecure_http_exceptions_total", labels) or 0) == (
        0 if cancel else 1
    )
    assert (
        metrics.registry.get_sample_value("finsecure_http_request_duration_seconds_count", labels)
        == 1
    )
    assert b"synthetic-private" not in generate_latest(metrics.registry)
    assert b"unknown-private" not in generate_latest(metrics.registry)


@mark.parametrize(
    "scope",
    [
        {"type": "lifespan"},
        {"type": "websocket", "path": "/ws"},
        {"type": "http", "path": "/metrics", "method": "GET"},
    ],
)
def test_non_http_and_metrics_calls_pass_through_unchanged(scope):
    events = []

    async def app(actual: Scope, actual_receive: Receive, actual_send: Send) -> None:
        assert actual is scope and actual_receive is receive and actual_send is discard
        events.append("called")

    metrics = ApplicationMetrics()
    run(HttpMetricsMiddleware(app, metrics)(scope, receive, discard))
    assert events == ["called"]
    assert metrics.registry.get_sample_value("finsecure_http_requests_total") is None


def test_messages_and_request_body_are_not_consumed_or_rewritten():
    messages = [
        {"type": "http.response.start", "status": 200, "headers": []},
        {"type": "http.response.body", "body": b"private", "more_body": False},
    ]
    received = []
    sent = []

    async def app(scope: Scope, actual_receive: Receive, send: Send) -> None:
        received.append(await actual_receive())
        for message in messages:
            await send(message)

    async def send(message: Message) -> None:
        sent.append(message)

    metrics = ApplicationMetrics()
    run(
        HttpMetricsMiddleware(app, metrics)(
            {"type": "http", "path": "/validate", "method": "POST"}, receive, send
        )
    )
    assert len(received) == 1 and received[0]["body"] == b"private synthetic body"
    assert len(sent) == len(messages) and all(
        actual is original for actual, original in zip(sent, messages, strict=True)
    )
    assert b"private" not in generate_latest(metrics.registry)


def test_unknown_validation_outcome_cannot_create_unbounded_series():
    metrics = ApplicationMetrics()
    with raises(ValueError, match="Unknown validation"):
        metrics.record_validation("private-dynamic-outcome")
    assert b"private-dynamic-outcome" not in generate_latest(metrics.registry)
