from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from repositories.rules import FirestoreRuleRepository, get_rule_repository
from schemas.rule import Rule

STATEMENT = {
    "ja": "夜9時以降は住宅街で静かにお願いします。",
    "en": "Please keep quiet in residential streets after 9 pm.",
}


def make_rule(rule_id: str, region: str) -> Rule:
    return Rule(
        id=rule_id,
        region=region,
        statement=STATEMENT,
        updated_at="2026-11-07T00:00:00Z",
    )


class FakeRuleRepository:
    def __init__(self, rules: list[Rule]) -> None:
        self._rules = rules

    def list_by_region(self, region: str) -> list[Rule]:
        return [rule for rule in self._rules if rule.region == region]


@pytest.fixture
def client():
    # Firestore の代わりに、メモリ上のルールを返す。
    fake = FakeRuleRepository(
        [
            make_rule("rule_001", "sakai"),
            make_rule("rule_002", "sakai"),
            make_rule("rule_003", "kyoto"),
        ]
    )
    app.dependency_overrides[get_rule_repository] = lambda: fake
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_region_rules_returns_only_that_region(client):
    response = client.get("/api/regions/sakai/rules")

    assert response.status_code == 200
    assert [rule["id"] for rule in response.json()] == ["rule_001", "rule_002"]
    assert response.json()[0] == {
        "id": "rule_001",
        "region": "sakai",
        "statement": STATEMENT,
        "updated_at": "2026-11-07T00:00:00Z",
        "last_reviewed_at": None,
    }


def test_list_region_rules_returns_empty_list_for_region_without_rules(client):
    # 地域の一覧を持たないので、ルールのない地域も 404 にせず空の一覧を返す。
    response = client.get("/api/regions/unknown/rules")

    assert response.status_code == 200
    assert response.json() == []


class FakeDocument:
    def __init__(self, doc_id: str, data: dict) -> None:
        self.id = doc_id
        self._data = data

    def to_dict(self) -> dict:
        return self._data


def test_firestore_repository_uses_document_id_as_rule_id():
    # Rule.id は保存されたフィールドではなく、ドキュメントIDから入れる。
    data = make_rule("stale_id", "sakai").model_dump()
    collection = MagicMock()
    collection.where.return_value.stream.return_value = [FakeDocument("abc123", data)]
    client = MagicMock()
    client.collection.return_value = collection

    rules = FirestoreRuleRepository(client).list_by_region("sakai")

    client.collection.assert_called_once_with("rules")
    assert [rule.id for rule in rules] == ["abc123"]


def test_firestore_repository_filters_by_region():
    # Firestore には、region が指定した地域と等しいルールだけを問い合わせる。
    collection = MagicMock()
    collection.where.return_value.stream.return_value = []
    client = MagicMock()
    client.collection.return_value = collection

    FirestoreRuleRepository(client).list_by_region("sakai")

    collection.where.assert_called_once()
    field_filter = collection.where.call_args.kwargs["filter"]
    assert (field_filter.field_path, field_filter.op_string, field_filter.value) == (
        "region",
        "==",
        "sakai",
    )
