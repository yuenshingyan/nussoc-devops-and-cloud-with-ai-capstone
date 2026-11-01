"""Check observable JSON output and ASGI transparency with synthetic sensitive values."""

from asyncio import CancelledError, run
from datetime import datetime
from json import loads
from logging import INFO, LogRecord, getLogger
from unittest.mock import Mock

from fastapi.testclient import TestClient
from pytest import LogCaptureFixture, mark, raises
from starlette.types import Message, Receive, Scope, Send

from finsecure_pay.main import create_app
from finsecure_pay.observability.logging import HttpLoggingMiddleware, JsonEventFormatter


def events(caplog: LogCaptureFixture) -> list[dict]:
    return [loads(JsonEventFormatter().format(record)) for record in caplog.records]


async def receive() -> Message:
    raise AssertionError("middleware must not consume the body")


async def discard(message: Message) -> None:
    pass


@mark.parametrize(
    "status,expected",
    [
        (101, "1xx"),
        (200, "2xx"),
        (307, "3xx"),
        (422, "4xx"),
        (500, "5xx"),
        (700, "other"),
        (True, "other"),
    ],
)
def test_request_events_use_bounded_fields_and_monotonic_seconds(
    caplog, monkeypatch, status, expected
):
    caplog.set_level(INFO, logger="finsecure_pay")
    monkeypatch.setattr(
        "finsecure_pay.observability.logging.perf_counter", Mock(side_effect=[10.0, 10.125])
    )
    sent = []

    async def send(message: Message) -> None:
        sent.append(message)

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({"type": "http.response.body", "body": b"synthetic-private"})

    run(
        HttpLoggingMiddleware(app)(
            {
                "type": "http",
                "path": "/synthetic-private",
                "method": "synthetic-private",
                "query_string": b"synthetic-private",
            },
            receive,
            send,
        )
    )
    (record,) = events(caplog)
    assert record["route"] == "other" and record["method"] == "OTHER"
    assert record["status_class"] == expected and record["duration_seconds"] == 0.125
    assert datetime.fromisoformat(record["timestamp"]).utcoffset().total_seconds() == 0
    assert "synthetic-private" not in str(record)
    assert sent[-1]["body"] == b"synthetic-private"


@mark.parametrize("error", [RuntimeError("synthetic-private"), CancelledError("synthetic-private")])
def test_failures_and_cancellation_propagate_with_safe_diagnostics(caplog, error):
    caplog.set_level(INFO, logger="finsecure_pay")

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        raise error

    with raises(type(error)) as caught:
        run(
            HttpLoggingMiddleware(app)(
                {"type": "http", "path": "/validate", "method": "POST"}, receive, discard
            )
        )
    assert caught.value is error
    (record,) = events(caplog)
    assert record["event"] == (
        "http_request_cancelled" if isinstance(error, CancelledError) else "http_request_failed"
    )
    assert record["status_class"] == "no_response"
    assert record["level"] == ("INFO" if isinstance(error, CancelledError) else "ERROR")
    assert "synthetic-private" not in str(record)


@mark.parametrize(
    "scope",
    [
        {"type": "lifespan"},
        {"type": "websocket"},
        {"type": "http", "path": "/metrics", "method": "GET"},
    ],
)
def test_metrics_and_non_http_are_forwarded_without_access_events(caplog, scope):
    caplog.set_level(INFO, logger="finsecure_pay")
    observed = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        observed.append(scope)

    run(HttpLoggingMiddleware(app)(scope, receive, discard))
    assert observed == [scope]
    assert not caplog.records


@mark.parametrize(
    "amount,outcome,codes",
    [
        ("1.00", "accepted", []),
        ("-1.00", "rejected", ["AMOUNT_NOT_POSITIVE"]),
        (1, "invalid", ["INVALID_REQUEST"]),
    ],
)
def test_real_api_outcomes_never_log_transaction_values(caplog, amount, outcome, codes):
    caplog.set_level(INFO, logger="finsecure_pay")
    with TestClient(create_app()) as client:
        response = client.post(
            "/validate",
            json={
                "transaction_id": "synthetic-private",
                "sender_id": "synthetic-private-sender",
                "recipient_id": "synthetic-private-recipient",
                "amount": amount,
                "currency": "SGD",
            },
        )
    assert response.status_code == (422 if outcome == "invalid" else 200)
    records = events(caplog)
    (result,) = [record for record in records if record["event"] == "validation_outcome"]
    assert result["outcome"] == outcome and result["codes"] == codes
    assert "synthetic-private" not in str(records)


@mark.parametrize(
    "message",
    ["synthetic-private %s", {"secret": "synthetic-private"}, "Invalid HTTP request received."],
)
def test_server_diagnostics_preserve_warning_without_interpolating_data(message):
    record = LogRecord(
        "uvicorn.error",
        30,
        "synthetic-private",
        1,
        message,
        ("synthetic-private",),
        (RuntimeError, RuntimeError("synthetic-private"), None),
    )
    result = loads(JsonEventFormatter().format(record))
    assert result["level"] == "WARNING" and result["diagnostic_code"] == "UNEXPECTED_ERROR"
    assert "synthetic-private" not in str(result)


@mark.parametrize(
    "fields",
    [
        {"outcome": "rejected", "codes": ["synthetic-private"]},
        {"outcome": "accepted", "codes": [], "secret": "synthetic-private"},
        {"outcome": "invalid", "codes": []},
        {"outcome": "accepted", "codes": "synthetic-private"},
    ],
)
def test_malformed_event_data_is_not_exported(caplog, fields):
    caplog.set_level(INFO, logger="finsecure_pay")
    getLogger("finsecure_pay").info(
        "synthetic-private",
        extra={"finsecure_event": "validation_outcome", "finsecure_fields": fields},
    )
    (record,) = events(caplog)
    assert record["event"] == "runtime_diagnostic"
    assert "synthetic-private" not in str(record)


@mark.parametrize(
    "code",
    [
        "AMOUNT_NOT_POSITIVE",
        "AMOUNT_LIMIT_EXCEEDED",
        "UNSUPPORTED_CURRENCY",
        "AMOUNT_PRECISION_EXCEEDED",
        "SAME_ACCOUNT",
    ],
)
def test_every_documented_business_code_is_preserved(caplog, code):
    caplog.set_level(INFO, logger="finsecure_pay")
    getLogger("finsecure_pay").info(
        "validation_outcome",
        extra={
            "finsecure_event": "validation_outcome",
            "finsecure_fields": {"outcome": "rejected", "codes": [code]},
        },
    )
    (result,) = events(caplog)
    assert result["event"] == "validation_outcome"
    assert result["codes"] == [code]


@mark.parametrize(
    "duration", [float("nan"), float("inf"), -1.0, True, "synthetic-private", 10**1000]
)
def test_invalid_duration_does_not_crash_or_export_sensitive_data(caplog, duration):
    caplog.set_level(INFO, logger="finsecure_pay")
    getLogger("finsecure_pay").info(
        "synthetic-private",
        extra={
            "finsecure_event": "http_request_completed",
            "finsecure_fields": {
                "route": "/health",
                "method": "GET",
                "status_class": "2xx",
                "duration_seconds": duration,
            },
        },
    )
    (record,) = events(caplog)
    assert record["event"] == "runtime_diagnostic"
    assert "synthetic-private" not in str(record)
