from fastapi.testclient import TestClient

from main import app


def test_app_starts_and_serves_openapi():
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Regional Rules API"
    assert response.json()["paths"] == {}
