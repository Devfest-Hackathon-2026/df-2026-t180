from functools import lru_cache
from typing import Protocol

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from schemas.rule import Rule

RULES_COLLECTION = "rules"


class RuleRepository(Protocol):
    def list_by_region(self, region: str) -> list[Rule]: ...


class FirestoreRuleRepository:
    def __init__(self, client: firestore.Client) -> None:
        self._collection = client.collection(RULES_COLLECTION)

    def list_by_region(self, region: str) -> list[Rule]:
        query = self._collection.where(filter=FieldFilter("region", "==", region))
        # Rule.id はドキュメントIDと同じ値にする
        return [
            Rule.model_validate({**doc.to_dict(), "id": doc.id})
            for doc in query.stream()
        ]


# クライアントの作成は最初のリクエストまで遅らせる。
# 起動時やテスト時に Google Cloud の認証がなくても動かせるようにするため。
@lru_cache
def get_rule_repository() -> RuleRepository:
    return FirestoreRuleRepository(firestore.Client())
