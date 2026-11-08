from fastapi.testclient import TestClient

from main import app


def test_app_starts_and_serves_openapi():
    # Firestore に接続しなくても、アプリが起動してOpenAPI定義を返せることを確認する。
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Regional Rules API"
    assert "/api/posts" in response.json()["paths"]
