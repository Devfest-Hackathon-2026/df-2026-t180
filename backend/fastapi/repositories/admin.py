"""管理者 API（機能D）の DB 操作。

保存構造は docs/詳細設計.md の「コレクション構成」に従う。

- admins: ドキュメントID = Firebase UID
- candidates: ドキュメントID = 候補ID（{post_id}_{連番} など）
- rules: ドキュメントID = 自動ID（ルールの id と同じ値を保存する）
"""

from collections.abc import Callable, Iterable
from functools import lru_cache
from typing import Protocol, TypeVar

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from schemas.candidate import Candidate
from schemas.post import StoredPost
from schemas.rule import Rule

ADMINS_COLLECTION = "admins"
CANDIDATES_COLLECTION = "candidates"
POSTS_COLLECTION = "posts"
RULES_COLLECTION = "rules"

T = TypeVar("T")


class AdminTransaction(Protocol):
    """1 回の採否・編集の中で使う読み書き。読みはすべて書きより先に行う。"""

    def get_candidate(self, candidate_id: str) -> Candidate | None: ...
    def get_rule(self, rule_id: str) -> Rule | None: ...
    def new_rule_id(self) -> str: ...
    def set_candidate(self, candidate: Candidate) -> None: ...
    def set_rule(self, rule: Rule) -> None: ...


class AdminRepository(Protocol):
    def is_admin(self, uid: str) -> bool: ...
    def list_candidates(
        self, *, status: str | None, type: str | None, region: str | None
    ) -> list[Candidate]: ...
    def get_posts(self, post_ids: Iterable[str]) -> dict[str, StoredPost]: ...
    def get_rules(self, rule_ids: Iterable[str]) -> dict[str, Rule]: ...
    def list_rules(self, *, region: str | None) -> list[Rule]: ...
    def run_transaction(self, work: Callable[[AdminTransaction], T]) -> T: ...


def _candidate(snapshot) -> Candidate:
    return Candidate.model_validate({**snapshot.to_dict(), "id": snapshot.id})


def _rule(snapshot) -> Rule:
    return Rule.model_validate({**snapshot.to_dict(), "id": snapshot.id})


class FirestoreAdminTransaction:
    def __init__(self, client: firestore.Client, transaction) -> None:
        self._client = client
        self._transaction = transaction

    def _get(self, collection: str, doc_id: str):
        snapshot = (
            self._client.collection(collection)
            .document(doc_id)
            .get(transaction=self._transaction)
        )
        return snapshot if snapshot.exists else None

    def get_candidate(self, candidate_id: str) -> Candidate | None:
        snapshot = self._get(CANDIDATES_COLLECTION, candidate_id)
        return _candidate(snapshot) if snapshot else None

    def get_rule(self, rule_id: str) -> Rule | None:
        snapshot = self._get(RULES_COLLECTION, rule_id)
        return _rule(snapshot) if snapshot else None

    def new_rule_id(self) -> str:
        # 自動IDを払い出すだけで、書き込みは set_rule で行う。
        return self._client.collection(RULES_COLLECTION).document().id

    def set_candidate(self, candidate: Candidate) -> None:
        ref = self._client.collection(CANDIDATES_COLLECTION).document(candidate.id)
        self._transaction.set(ref, candidate.model_dump())

    def set_rule(self, rule: Rule) -> None:
        ref = self._client.collection(RULES_COLLECTION).document(rule.id)
        self._transaction.set(ref, rule.model_dump())


class FirestoreAdminRepository:
    def __init__(self, client: firestore.Client) -> None:
        self._client = client

    def is_admin(self, uid: str) -> bool:
        return self._client.collection(ADMINS_COLLECTION).document(uid).get().exists

    def list_candidates(
        self, *, status: str | None, type: str | None, region: str | None
    ) -> list[Candidate]:
        query = self._client.collection(CANDIDATES_COLLECTION)
        for field, value in (("status", status), ("type", type), ("region", region)):
            if value is not None:
                query = query.where(filter=FieldFilter(field, "==", value))
        return sorted((_candidate(s) for s in query.stream()), key=lambda c: c.id)

    def _get_all(self, collection: str, ids: Iterable[str]):
        refs = [
            self._client.collection(collection).document(i) for i in dict.fromkeys(ids)
        ]
        if not refs:
            return []
        return [s for s in self._client.get_all(refs) if s.exists]

    def get_posts(self, post_ids: Iterable[str]) -> dict[str, StoredPost]:
        return {
            s.id: StoredPost.model_validate(s.to_dict())
            for s in self._get_all(POSTS_COLLECTION, post_ids)
        }

    def get_rules(self, rule_ids: Iterable[str]) -> dict[str, Rule]:
        return {s.id: _rule(s) for s in self._get_all(RULES_COLLECTION, rule_ids)}

    def list_rules(self, *, region: str | None) -> list[Rule]:
        query = self._client.collection(RULES_COLLECTION)
        if region is not None:
            query = query.where(filter=FieldFilter("region", "==", region))
        rules = (_rule(s) for s in query.stream())
        # 新しく更新されたものから並べる。
        return sorted(rules, key=lambda r: r.updated_at, reverse=True)

    def run_transaction(self, work: Callable[[AdminTransaction], T]) -> T:
        # 候補とルールを同じトランザクションで読み書きし、二重採用や途中失敗を防ぐ。
        @firestore.transactional
        def run(transaction):
            return work(FirestoreAdminTransaction(self._client, transaction))

        return run(self._client.transaction())


# クライアントの作成は最初のリクエストまで遅らせる。
# Google Cloud の認証がなくても起動・テストできるようにするため。
@lru_cache
def get_admin_repository() -> AdminRepository:
    return FirestoreAdminRepository(firestore.Client())
