from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from repositories.regions import FirestoreRegionRepository, get_region_repository
from schemas.region import Region

SAKAI = {"id": "sakai", "name": {"ja": "堺市", "en": "Sakai"}}


class FakeRegionRepository:
    def __init__(self, regions: list[Region]) -> None:
        self._regions = regions

    def list_all(self) -> list[Region]:
        return self._regions


@pytest.fixture
def use_regions():
    # Firestore の代わりに、メモリ上の地域を返す。
    def override(regions: list[Region]) -> None:
        fake = FakeRegionRepository(regions)
        app.dependency_overrides[get_region_repository] = lambda: fake

    yield override
    app.dependency_overrides.clear()


def test_list_regions_returns_all_regions(use_regions):
    use_regions([Region.model_validate(SAKAI)])

    with TestClient(app) as client:
        response = client.get("/api/regions")

    assert response.status_code == 200
    assert response.json() == [SAKAI]


def test_list_regions_returns_empty_list_without_regions(use_regions):
    use_regions([])

    with TestClient(app) as client:
        response = client.get("/api/regions")

    assert response.status_code == 200
    assert response.json() == []


def test_firestore_repository_uses_document_id_as_region_id():
    # Region.id は保存されたフィールドではなく、ドキュメントIDから入れる。
    doc = MagicMock(id="sakai")
    doc.to_dict.return_value = {"name": SAKAI["name"]}
    client = MagicMock()
    client.collection.return_value.stream.return_value = [doc]

    regions = FirestoreRegionRepository(client).list_all()

    client.collection.assert_called_once_with("regions")
    assert regions == [Region.model_validate(SAKAI)]
