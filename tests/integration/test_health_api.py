"""Verify the public health endpoint contract."""

from fastapi.testclient import TestClient


def test_health_returns_healthy_json(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "healthy"}


def test_health_rejects_post(client: TestClient) -> None:
    response = client.post("/health")

    assert response.status_code == 405
    assert "GET" in response.headers["allow"]


def test_openapi_documents_health_response(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    response = schema["paths"]["/health"]["get"]["responses"]["200"]
    reference = response["content"]["application/json"]["schema"]["$ref"]
    model = schema["components"]["schemas"][reference.rsplit("/", 1)[-1]]

    assert "status" in model["required"]
    assert model["properties"]["status"]["const"] == "healthy"
