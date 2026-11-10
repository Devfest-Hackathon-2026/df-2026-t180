import pytest
from fastapi.testclient import TestClient

from main import app
from repositories.posts import get_post_repository
from schemas.post import StoredPost

POST = {"text": "夜間は静かにしてください。", "region": "sakai"}


class FakePostRepository:
    def __init__(self) -> None:
        self.saved: list[StoredPost] = []

    def add(self, post: StoredPost) -> str:
        self.saved.append(post)
        return f"post_{len(self.saved)}"


@pytest.fixture
def repository():
    # Firestore の代わりにメモリに保存し、保存内容をテストから確認できるようにする。
    fake = FakePostRepository()
    app.dependency_overrides[get_post_repository] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def client(repository):
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize("reason", [None, "夜間の騒音で眠れないため。"])
def test_create_post_saves_unprocessed_post(client, repository, reason):
    # バッチが拾えるよう、保存直後の status が unprocessed になっていることを確認する。
    payload = {**POST, "reason": reason}
    response = client.post("/api/posts", json=payload)

    assert response.status_code == 201
    assert response.json() == {"id": "post_1"}
    saved = repository.saved[0]
    assert saved.model_dump(include={"text", "region", "reason"}) == payload
    assert saved.status == "unprocessed"
    assert saved.status_updated_at == saved.created_at
    assert saved.created_at.utcoffset().total_seconds() == 0


def test_create_post_accepts_missing_reason(client, repository):
    response = client.post("/api/posts", json=POST)

    assert response.status_code == 201
    assert repository.saved[0].reason is None


@pytest.mark.parametrize(
    "extra",
    [
        {"status": "processed"},
        {"created_at": "2026-01-01T00:00:00+09:00"},
        {"status_updated_at": "2026-01-01T00:00:00+09:00"},
    ],
)
def test_create_post_rejects_server_managed_fields(client, repository, extra):
    # サーバーが管理する項目を住民が送ってきても、保存せずに拒否することを確認する。
    response = client.post("/api/posts", json={**POST, **extra})

    assert response.status_code == 422
    assert repository.saved == []


@pytest.mark.parametrize(
    "payload",
    [
        {"region": "sakai"},
        {"text": "夜間は静かにしてください。"},
        {**POST, "text": " "},
        {**POST, "region": ""},
        {**POST, "reason": 123},
        {**POST, "reason": ""},
        {**POST, "reason": " "},
    ],
)
def test_create_post_rejects_invalid_payload(client, repository, payload):
    response = client.post("/api/posts", json=payload)

    assert response.status_code == 422
    assert repository.saved == []


@pytest.mark.parametrize(
    "location", [{"lat": 34.5738, "lng": 135.4795}, {"lat": 34, "lng": 135}]
)
def test_create_post_saves_location(client, repository, location):
    # 場所に紐づく投稿では、送られた位置をそのまま保存する。整数も受け付ける。
    response = client.post("/api/posts", json={**POST, "location": location})

    assert response.status_code == 201
    assert repository.saved[0].location.model_dump() == location


def test_create_post_without_location_saves_none(client, repository):
    response = client.post("/api/posts", json=POST)

    assert response.status_code == 201
    assert repository.saved[0].location is None


@pytest.mark.parametrize(
    "location",
    [
        {"lat": 91, "lng": 135.0},
        {"lat": 34.5, "lng": 181},
        {"lat": 34.5},
        {"lat": 34.5, "lng": 135.0, "alt": 10},
        {"lat": True, "lng": 135},
        {"lat": "34.5", "lng": "135"},
        "34.5,135.0",
    ],
)
def test_create_post_rejects_invalid_location(client, repository, location):
    # 範囲外の緯度経度や、形の違う位置は保存しない。
    response = client.post("/api/posts", json={**POST, "location": location})

    assert response.status_code == 422
    assert repository.saved == []
