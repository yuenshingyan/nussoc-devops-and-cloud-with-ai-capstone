"""Allowlisted JSON events: never format arbitrary messages, arguments or exceptions."""

from asyncio import CancelledError
from datetime import UTC, datetime
from json import dumps
from logging import ERROR, INFO, Formatter, LogRecord, getLogger
from math import isfinite
from time import perf_counter
from typing import get_args

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from finsecure_pay.schemas.transaction import ValidationErrorCode

BUSINESS_CODES = frozenset(get_args(ValidationErrorCode.__value__))
HTTP_EVENTS = {"http_request_completed", "http_request_failed", "http_request_cancelled"}
SERVER_MESSAGES = {
    "Started server process [%d]": "SERVER_STARTED",
    "Waiting for application startup.": "APPLICATION_STARTING",
    "Application startup complete.": "APPLICATION_STARTED",
    "Shutting down": "SERVER_STOPPING",
    "Waiting for application shutdown.": "APPLICATION_STOPPING",
    "Application shutdown complete.": "APPLICATION_STOPPED",
    "Finished server process [%d]": "SERVER_STOPPED",
    "Invalid HTTP request received.": "INVALID_HTTP_REQUEST",
    "Unsupported upgrade request.": "UNSUPPORTED_UPGRADE",
}


def valid_fields(event: object, fields: object) -> bool:
    """Fail closed on malformed records, including arbitrary extra keys and values."""
    if not isinstance(event, str) or not isinstance(fields, dict):
        return False
    if event == "validation_outcome":
        if set(fields) != {"outcome", "codes"} or type(fields["codes"]) is not list:
            return False
        codes = fields["codes"]
        if not all(type(code) is str for code in codes):
            return False
        return (
            (fields["outcome"] == "accepted" and codes == [])
            or (fields["outcome"] == "invalid" and codes == ["INVALID_REQUEST"])
            or (
                fields["outcome"] == "rejected"
                and bool(codes)
                and len(codes) <= len(BUSINESS_CODES)
                and all(code in BUSINESS_CODES for code in codes)
            )
        )
    if event not in HTTP_EVENTS:
        return False
    expected = {"route", "method", "status_class", "duration_seconds"}
    if event == "http_request_failed":
        expected.add("error_code")
        if fields.get("error_code") != "UNEXPECTED_ERROR":
            return False
    return (
        set(fields) == expected
        and fields["route"] in ("/health", "/validate", "other")
        and fields["method"] in ("GET", "POST", "OTHER")
        and fields["status_class"] in ("1xx", "2xx", "3xx", "4xx", "5xx", "no_response", "other")
        and type(fields["duration_seconds"]) is float
        and isfinite(fields["duration_seconds"])
        and fields["duration_seconds"] >= 0
    )


class JsonEventFormatter(Formatter):
    """Retain severity and safe diagnostic codes, not potentially sensitive raw text."""

    def format(self, record: LogRecord) -> str:
        level = next(
            name
            for threshold, name in [
                (50, "CRITICAL"),
                (40, "ERROR"),
                (30, "WARNING"),
                (20, "INFO"),
                (0, "DEBUG"),
            ]
            if record.levelno >= threshold
        )
        event = getattr(record, "finsecure_event", None)
        fields = getattr(record, "finsecure_fields", None)
        result = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": level,
        }
        if valid_fields(event, fields):
            result.update(event=event, **fields)
        else:
            # Uvicorn args/tracebacks can contain URLs and submitted values. Retain
            # unknown warnings visibly, but never interpolate their free-form text.
            result["event"] = (
                "server_diagnostic" if record.name.startswith("uvicorn") else "runtime_diagnostic"
            )
            result["diagnostic_code"] = (
                "UNEXPECTED_ERROR"
                if record.exc_info
                else SERVER_MESSAGES.get(record.msg, "UNCLASSIFIED_MESSAGE")
                if type(record.msg) is str
                else "UNCLASSIFIED_MESSAGE"
            )
        return dumps(result, ensure_ascii=True, allow_nan=False, separators=(",", ":"))


def record_validation(outcome: str, codes: list[str]) -> None:
    """Log only a validated outcome and allowlisted codes, never a transaction."""
    getLogger("finsecure_pay").info(
        "validation_outcome",
        extra={
            "finsecure_event": "validation_outcome",
            "finsecure_fields": {"outcome": outcome, "codes": codes},
        },
    )


class HttpLoggingMiddleware:
    """Observe ASGI completion without consuming bodies or swallowing cancellation."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] == "/metrics":
            await self.app(scope, receive, send)
            return
        fields = {
            "route": scope["path"] if scope["path"] in ("/health", "/validate") else "other",
            "method": scope["method"] if scope["method"] in ("GET", "POST") else "OTHER",
            "status_class": "no_response",
        }
        started = perf_counter()
        event, level = "http_request_completed", INFO

        async def observe_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                status = message["status"]
                fields["status_class"] = (
                    f"{status // 100}xx" if type(status) is int and 100 <= status < 600 else "other"
                )
            await send(message)

        try:
            await self.app(scope, receive, observe_send)
        except CancelledError:
            event = "http_request_cancelled"
            raise
        except BaseException:
            event, level = "http_request_failed", ERROR
            fields["error_code"] = "UNEXPECTED_ERROR"
            raise
        finally:
            fields["duration_seconds"] = perf_counter() - started
            getLogger("finsecure_pay").log(
                level, event, extra={"finsecure_event": event, "finsecure_fields": fields}
            )
