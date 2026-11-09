from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api import admin as admin_api
from main import app
from repositories.admin import get_admin_repository
from schemas.candidate import Candidate
from schemas.post import StoredPost
from schemas.rule import Rule
from services import firebase_auth
from services.firebase_auth import InvalidToken

NOW = datetime(2026, 11, 9, 6, 0, tzinfo=timezone.utc)
OLD = datetime(2023, 11, 3, tzinfo=timezone.utc)
ADMIN_TOKEN = "admin-token"
VISITOR_TOKEN = "visitor-token"
AUTH = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
EDITED = {"ja": "修正した文です。", "en": "An edited sentence."}


def statement(text: str) -> dict:
    return {"ja": f"{text}。", "en": f"{text}."}


def make_candidate(candidate_id: str, **fields) -> Candidate:
    base = {
        "id": candidate_id,
        "post_id": "post_1",
        "region": "sakai",
        "statement": statement("候補"),
        "status": "pending",
        "type": "add",
    }
    return Candidate(**{**base, **fields})


class FakeTransaction:
    def __init__(self, repository: "FakeAdminRepository") -> None:
        self._repository = repository
        self.candidates: dict[str, Candidate] = {}
        self.rules: dict[str, Rule] = {}

    def get_candidate(self, candidate_id):
        return self._repository.candidates.get(candidate_id)

    def get_rule(self, rule_id):
        return self._repository.rules.get(rule_id)

    def new_rule_id(self):
        return "rule_new"

    def set_candidate(self, candidate):
        self.candidates[candidate.id] = candidate

    def set_rule(self, rule):
        self.rules[rule.id] = rule


class FakeAdminRepository:
    """Firestore の代わり。トランザクション内の書き込みは成功したときだけ反映する。"""

    def __init__(self) -> None:
        self.admins = {"admin_uid"}
        self.posts = {
            "post_1": StoredPost(
                text="芝生でバーベキューする人がいる",
                region="sakai",
                reason="煙が住宅に届くため",
                status="processed",
                status_updated_at=NOW,
                created_at=NOW,
            )
        }
        self.rules = {
            "rule_1": Rule(
                id="rule_1",
                region="sakai",
                statement=statement("既存のルール"),
                updated_at=OLD,
            )
        }
        self.candidates = {
            c.id: c
            for c in [
                make_candidate("post_1_1"),
                make_candidate("post_1_2", type="update", target_rule_id="rule_1"),
                make_candidate(
                    "stale_rule_1",
                    source="stale_rule",
                    post_id=None,
                    type="review",
                    target_rule_id="rule_1",
                    review_reason="最終確認から3年が経過しました",
                    statement=statement("既存のルール"),
                ),
                make_candidate("post_1_3", status="rejected"),
            ]
        }
        self.commits = 0

    def is_admin(self, uid):
        return uid in self.admins

    def list_candidates(self, *, status, type, region):
        return sorted(
            (
                c
                for c in self.candidates.values()
                if (status is None or c.status == status)
                and (type is None or c.type == type)
                and (region is None or c.region == region)
            ),
            key=lambda c: c.id,
        )

    def get_posts(self, post_ids):
        return {i: self.posts[i] for i in post_ids if i in self.posts}

    def get_rules(self, rule_ids):
        return {i: self.rules[i] for i in rule_ids if i in self.rules}

    def run_transaction(self, work):
        transaction = FakeTransaction(self)
        result = work(transaction)
        self.candidates.update(transaction.candidates)
        self.rules.update(transaction.rules)
        self.commits += 1
        return result


def verify(token: str) -> str:
    if token == ADMIN_TOKEN:
        return "admin_uid"
    if token == VISITOR_TOKEN:
        return "visitor_uid"
    raise InvalidToken("bad token")


@pytest.fixture
def repository():
    fake = FakeAdminRepository()
    app.dependency_overrides[get_admin_repository] = lambda: fake
    app.dependency_overrides[admin_api._verifier] = lambda: verify
    app.dependency_overrides[admin_api.utc_now] = lambda: NOW
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def client(repository):
    with TestClient(app) as test_client:
        yield test_client


# --- 認証・認可 ---------------------------------------------------------------

ENDPOINTS = [
    ("get", "/api/admin/candidates", None),
    ("patch", "/api/admin/candidates/post_1_1", {"action": "approve"}),
    ("patch", "/api/admin/rules/rule_1", {"statement": EDITED}),
]


@pytest.mark.parametrize(("method", "path", "body"), ENDPOINTS)
@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer wrong"}, {"Authorization": f"Basic {ADMIN_TOKEN}"}],
)
def test_requires_valid_token(client, repository, method, path, body, headers):
    response = client.request(method, path, json=body, headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert repository.commits == 0


@pytest.mark.parametrize(("method", "path", "body"), ENDPOINTS)
def test_rejects_signed_in_non_admin(client, repository, method, path, body):
    headers = {"Authorization": f"Bearer {VISITOR_TOKEN}"}
    response = client.request(method, path, json=body, headers=headers)

    assert response.status_code == 403
    assert repository.commits == 0


def test_returns_503_when_sign_in_is_not_configured(client, monkeypatch):
    # 検証器の差し替えを外し、プロジェクトIDのない本物の設定を使う。
    app.dependency_overrides.pop(admin_api._verifier)
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    firebase_auth.get_token_verifier.cache_clear()

    response = client.get("/api/admin/candidates", headers=AUTH)

    assert response.status_code == 503
    firebase_auth.get_token_verifier.cache_clear()


# --- 候補一覧 -----------------------------------------------------------------


def test_lists_pending_candidates_with_post_and_current_rule(client):
    response = client.get("/api/admin/candidates", headers=AUTH)

    assert response.status_code == 200
    body = {c["id"]: c for c in response.json()}
    assert set(body) == {"post_1_1", "post_1_2", "stale_rule_1"}
    assert body["post_1_1"]["post"]["text"] == "芝生でバーベキューする人がいる"
    assert body["post_1_1"]["current"] is None
    assert body["post_1_2"]["current"]["statement"] == statement("既存のルール")
    assert body["stale_rule_1"]["post"] is None
    assert body["stale_rule_1"]["current"]["updated_at"].startswith("2023-11-03")


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("?type=update", {"post_1_2"}),
        ("?type=review", {"stale_rule_1"}),
        ("?status=rejected", {"post_1_3"}),
        ("?status=all", {"post_1_1", "post_1_2", "post_1_3", "stale_rule_1"}),
        ("?region=osaka", set()),
    ],
)
def test_filters_candidates(client, query, expected):
    response = client.get(f"/api/admin/candidates{query}", headers=AUTH)

    assert response.status_code == 200
    assert {c["id"] for c in response.json()} == expected


def test_rejects_unknown_filter_values(client):
    response = client.get("/api/admin/candidates?status=done", headers=AUTH)

    assert response.status_code == 422


# --- 採否（#24 の方針） -------------------------------------------------------


def decide(client, candidate_id, body):
    return client.patch(
        f"/api/admin/candidates/{candidate_id}", json=body, headers=AUTH
    )


@pytest.mark.parametrize("edited", [None, EDITED])
def test_approving_add_creates_rule(client, repository, edited):
    body = {"action": "approve", **({"statement": edited} if edited else {})}
    response = decide(client, "post_1_1", body)

    assert response.status_code == 200
    published = edited or statement("候補")
    rule = repository.rules["rule_new"]
    assert rule.statement.model_dump() == published
    assert (rule.region, rule.updated_at, rule.last_reviewed_at) == ("sakai", NOW, None)
    candidate = repository.candidates["post_1_1"]
    assert candidate.status == "approved"
    assert candidate.statement.model_dump() == published
    assert response.json()["rule"]["id"] == "rule_new"


@pytest.mark.parametrize("edited", [None, EDITED])
def test_approving_update_replaces_rule_text(client, repository, edited):
    body = {"action": "approve", **({"statement": edited} if edited else {})}
    response = decide(client, "post_1_2", body)

    assert response.status_code == 200
    rule = repository.rules["rule_1"]
    assert rule.statement.model_dump() == (edited or statement("候補"))
    assert (rule.updated_at, rule.last_reviewed_at) == (NOW, None)
    assert repository.candidates["post_1_2"].status == "approved"


def test_review_still_correct_only_moves_last_reviewed_at(client, repository):
    response = decide(client, "stale_rule_1", {"action": "approve"})

    assert response.status_code == 200
    rule = repository.rules["rule_1"]
    assert rule.statement.model_dump() == statement("既存のルール")
    assert (rule.updated_at, rule.last_reviewed_at) == (OLD, NOW)
    assert repository.candidates["stale_rule_1"].status == "approved"


def test_review_edit_and_approve_replaces_text(client, repository):
    response = decide(
        client, "stale_rule_1", {"action": "approve", "statement": EDITED}
    )

    assert response.status_code == 200
    rule = repository.rules["rule_1"]
    assert rule.statement.model_dump() == EDITED
    assert rule.updated_at == NOW


@pytest.mark.parametrize("candidate_id", ["post_1_1", "post_1_2", "stale_rule_1"])
def test_reject_leaves_rules_unchanged(client, repository, candidate_id):
    before = dict(repository.rules)
    response = decide(client, candidate_id, {"action": "reject"})

    assert response.status_code == 200
    assert response.json()["rule"] is None
    assert repository.candidates[candidate_id].status == "rejected"
    assert repository.rules == before


def test_reject_with_statement_is_invalid(client, repository):
    response = decide(client, "post_1_1", {"action": "reject", "statement": EDITED})

    assert response.status_code == 422
    assert repository.commits == 0


@pytest.mark.parametrize(
    "body",
    [
        {"action": "publish"},
        {"action": "approve", "statement": {"ja": " ", "en": "x"}},
        {"action": "approve", "status": "approved"},
    ],
)
def test_rejects_invalid_decision_bodies(client, repository, body):
    response = decide(client, "post_1_1", body)

    assert response.status_code == 422
    assert repository.candidates["post_1_1"].status == "pending"


def test_already_decided_candidate_is_a_conflict(client, repository):
    response = decide(client, "post_1_3", {"action": "approve"})

    assert response.status_code == 409
    assert repository.candidates["post_1_3"].status == "rejected"
    assert "rule_new" not in repository.rules


def test_deciding_twice_is_a_conflict(client, repository):
    assert decide(client, "post_1_1", {"action": "approve"}).status_code == 200
    response = decide(client, "post_1_1", {"action": "reject"})

    assert response.status_code == 409
    assert repository.candidates["post_1_1"].status == "approved"


def test_missing_target_rule_is_a_conflict_and_writes_nothing(client, repository):
    del repository.rules["rule_1"]
    response = decide(client, "post_1_2", {"action": "approve"})

    assert response.status_code == 409
    assert repository.candidates["post_1_2"].status == "pending"
    assert repository.rules == {}


def test_unknown_candidate_is_not_found(client):
    response = decide(client, "post_9_9", {"action": "approve"})

    assert response.status_code == 404


# --- 公開ルールの編集 -------------------------------------------------------


def test_edits_rule_text_and_moves_updated_at(client, repository):
    response = client.patch(
        "/api/admin/rules/rule_1", json={"statement": EDITED}, headers=AUTH
    )

    assert response.status_code == 200
    rule = repository.rules["rule_1"]
    assert rule.statement.model_dump() == EDITED
    assert rule.updated_at == NOW
    assert response.json()["id"] == "rule_1"


@pytest.mark.parametrize(
    "body",
    [{}, {"statement": {"ja": "", "en": "x"}}, {"statement": EDITED, "region": "x"}],
)
def test_rejects_invalid_rule_edits(client, repository, body):
    response = client.patch("/api/admin/rules/rule_1", json=body, headers=AUTH)

    assert response.status_code == 422
    assert repository.rules["rule_1"].updated_at == OLD


def test_editing_unknown_rule_is_not_found(client):
    response = client.patch(
        "/api/admin/rules/rule_9", json={"statement": EDITED}, headers=AUTH
    )

    assert response.status_code == 404
