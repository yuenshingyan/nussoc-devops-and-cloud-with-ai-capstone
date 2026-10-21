"""Shared API test fixtures."""

from collections.abc import Iterator

from fastapi.testclient import TestClient
from pytest import fixture

from finsecure_pay.main import create_app


@fixture
def client() -> Iterator[TestClient]:
    """Provide a fresh API client and close it after each test."""
    with TestClient(create_app()) as test_client:
        yield test_client
