from functools import lru_cache
from typing import Protocol

from google.cloud import firestore

from schemas.region import Region

REGIONS_COLLECTION = "regions"


class RegionRepository(Protocol):
    def list_all(self) -> list[Region]: ...


class FirestoreRegionRepository:
    def __init__(self, client: firestore.Client) -> None:
        self._collection = client.collection(REGIONS_COLLECTION)

    def list_all(self) -> list[Region]:
        # Region.id はドキュメントIDと同じ値にする
        return [
            Region.model_validate({**doc.to_dict(), "id": doc.id})
            for doc in self._collection.stream()
        ]


# クライアントの作成は最初のリクエストまで遅らせる。
# 起動時やテスト時に Google Cloud の認証がなくても動かせるようにするため。
@lru_cache
def get_region_repository() -> RegionRepository:
    return FirestoreRegionRepository(firestore.Client())
