"""Isolated polling/gate demonstration; never merge this file into main."""


def test_ci_demo_health_contract(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "intentional-failure"}
