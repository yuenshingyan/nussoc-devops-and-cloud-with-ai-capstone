"""Verify application construction and public metadata."""

from fastapi.testclient import TestClient

from finsecure_pay.main import create_app


def test_openapi_metadata(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "FinSecure Pay"
    assert response.json()["info"]["version"] == "0.2.0"


def test_factory_creates_independent_instances() -> None:
    first = create_app()
    second = create_app()

    assert first is not second
    first.state.test_marker = "first instance only"
    assert not hasattr(second.state, "test_marker")
