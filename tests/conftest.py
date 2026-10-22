"""Shared API test fixtures."""

from collections.abc import Iterator

from fastapi.testclient import TestClient
from pytest import MonkeyPatch, fixture

from finsecure_pay.main import create_app


@fixture(autouse=True)
def isolate_settings(monkeypatch: MonkeyPatch) -> None:
    """Keep developer environment overrides from changing unrelated test behavior."""
    monkeypatch.delenv("FINSECURE_MAX_TRANSACTION_AMOUNT", raising=False)
    monkeypatch.delenv("FINSECURE_SUPPORTED_CURRENCIES", raising=False)


@fixture
def client() -> Iterator[TestClient]:
    """Provide a fresh API client and close it after each test."""
    with TestClient(create_app()) as test_client:
        yield test_client


@fixture
def transaction_payload() -> dict[str, str]:
    """Provide fresh synthetic request data so tests cannot affect one another."""
    return {
        "transaction_id": "txn_001",
        "sender_id": "account_001",
        "recipient_id": "account_002",
        "amount": "125.50",
        "currency": "SGD",
    }
