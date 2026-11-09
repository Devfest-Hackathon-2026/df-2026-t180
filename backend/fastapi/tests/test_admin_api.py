from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from api import admin as admin_api
from main import app
from repositories.admin import TransactionContention, get_admin_repository
from schemas.candidate import Candidate
from schemas.post import StoredPost
from schemas.rule import Rule
from services import firebase_auth
from services.admin_decisions import rule_version
from services.candidate_generation import GeminiOutput
from services.firebase_auth import AuthUnavailable, InvalidToken

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
    """書き込みはため込み、run_transaction が最後まで成功したときだけ反映する。"""

    def __init__(self, repository: "FakeAdminRepository") -> None:
        self._repository = repository
        self.candidates: dict[str, Candidate] = {}
        self.rules: dict[str, Rule] = {}

    def get_candidate(self, candidate_id):
        return self._repository.candidates.get(candidate_id)

    def get_rule(self, rule_id):
        return self._repository.rules.get(rule_id)

    def new_rule_id(self):
        # Firestore の自動IDと同じく、毎回別のIDを払い出す。
        self._repository.issued_ids += 1
        return f"rule_new_{self._repository.issued_ids}"

    def update_candidate(self, before, after):
        assert self._repository.candidates[before.id] == before
        self.candidates[after.id] = after

    def save_rule(self, before, after):
        if before is None:
            assert after.id not in self._repository.rules, "create must not overwrite"
        self.rules[after.id] = after


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
        self.issued_ids = 0

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

    def list_rules(self, *, region):
        rules = [r for r in self.rules.values() if region is None or r.region == region]
        return sorted(rules, key=lambda r: r.updated_at, reverse=True)

    def run_transaction(self, work):
        transaction = FakeTransaction(self)
        result = work(transaction)
        self.candidates.update(transaction.candidates)
        self.rules.update(transaction.rules)
        self.commits += 1
        return result


def version_of(repository, rule_id="rule_1") -> str:
    return rule_version(repository.rules[rule_id])


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
    ("get", "/api/admin/rules", None),
    ("patch", "/api/admin/candidates/post_1_1", {"action": "approve"}),
    (
        "patch",
        "/api/admin/rules/rule_1",
        {"statement": EDITED, "expected_version": "v"},
    ),
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


def test_checks_token_before_touching_the_database(client):
    # トークンが無効なら、DB の準備（Firestore への接続）より先に 401 を返す。
    def unavailable():
        raise RuntimeError("database unavailable")

    app.dependency_overrides[get_admin_repository] = unavailable
    response = client.get(
        "/api/admin/candidates", headers={"Authorization": "Bearer wrong"}
    )

    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path", "body"), ENDPOINTS)
def test_rejects_signed_in_non_admin(client, repository, method, path, body):
    headers = {"Authorization": f"Bearer {VISITOR_TOKEN}"}
    response = client.request(method, path, json=body, headers=headers)

    assert response.status_code == 403
    assert repository.commits == 0


@pytest.fixture
def not_configured(monkeypatch):
    """検証器の差し替えを外し、プロジェクトIDのない本物の設定を使う。"""
    monkeypatch.setattr(firebase_auth, "load_dotenv", lambda: None)
    app.dependency_overrides.pop(admin_api._verifier)
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    firebase_auth.get_token_verifier.cache_clear()
    yield
    firebase_auth.get_token_verifier.cache_clear()


def test_returns_503_when_sign_in_is_not_configured(client, not_configured):
    response = client.get("/api/admin/candidates", headers=AUTH)

    assert response.status_code == 503


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": f"Basic {ADMIN_TOKEN}"}], ids=["none", "basic"]
)
def test_missing_token_is_401_even_when_not_configured(client, not_configured, headers):
    response = client.get("/api/admin/candidates", headers=headers)

    assert response.status_code == 401


def test_returns_503_when_public_keys_are_unavailable(client, repository):
    def unavailable(token):
        raise AuthUnavailable("could not fetch keys")

    app.dependency_overrides[admin_api._verifier] = lambda: unavailable
    response = client.get("/api/admin/candidates", headers=AUTH)

    assert response.status_code == 503
    # 内部の例外の内容は返さない。
    assert "could not fetch keys" not in response.text


def test_removing_an_admin_takes_effect_on_the_next_request(client, repository):
    assert client.get("/api/admin/rules", headers=AUTH).status_code == 200

    repository.admins.discard("admin_uid")

    assert client.get("/api/admin/rules", headers=AUTH).status_code == 403
    response = client.patch(
        "/api/admin/rules/rule_1",
        json={"statement": EDITED, "expected_version": version_of(repository)},
        headers=AUTH,
    )
    assert response.status_code == 403
    assert repository.rules["rule_1"].updated_at == OLD


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
    # 採用時に送り返す version。公開ルール一覧の version と同じ値。
    rules = client.get("/api/admin/rules", headers=AUTH).json()
    assert body["post_1_2"]["current"]["version"] == rules[0]["version"]


def test_no_candidates_is_an_empty_list_and_rules_still_work(client, repository):
    repository.candidates.clear()

    response = client.get("/api/admin/candidates?status=all", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == []

    rules = client.get("/api/admin/rules", headers=AUTH)
    assert [r["id"] for r in rules.json()] == ["rule_1"]
    edited = client.patch(
        "/api/admin/rules/rule_1",
        json={"statement": EDITED, "expected_version": rules.json()[0]["version"]},
        headers=AUTH,
    )
    assert edited.status_code == 200


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


@pytest.mark.parametrize(
    ("recorded", "changed"),
    [("current", False), ("older", True), (None, False)],
    ids=["same-version", "rule-changed", "not-recorded"],
)
def test_flags_candidates_whose_rule_changed_since_generation(
    client, repository, recorded, changed
):
    # 機能B が記録した「Gemini が参照したルールの版」と今の版を比べる。
    version = {"current": version_of(repository), "older": "0123456789abcdef"}
    repository.candidates["post_1_2"] = repository.candidates["post_1_2"].model_copy(
        update={"target_rule_version": version.get(recorded)}
    )

    body = {
        c["id"]: c for c in client.get("/api/admin/candidates", headers=AUTH).json()
    }

    assert body["post_1_2"]["rule_changed_since_generated"] is changed
    assert body["post_1_1"]["rule_changed_since_generated"] is False  # add


def test_flag_appears_after_the_rule_is_edited(client, repository):
    repository.candidates["post_1_2"] = repository.candidates["post_1_2"].model_copy(
        update={"target_rule_version": version_of(repository)}
    )
    edit(client, version_of(repository))

    body = {
        c["id"]: c for c in client.get("/api/admin/candidates", headers=AUTH).json()
    }

    assert body["post_1_2"]["rule_changed_since_generated"] is True


def test_add_candidate_cannot_have_a_target_rule_version():
    with pytest.raises(ValueError):
        make_candidate("post_9_1", target_rule_version="0123456789abcdef")


def test_rejects_unknown_filter_values(client):
    response = client.get("/api/admin/candidates?status=done", headers=AUTH)

    assert response.status_code == 422


# --- 採否（#24 の方針） -------------------------------------------------------


def decide(client, candidate_id, body):
    return client.patch(
        f"/api/admin/candidates/{candidate_id}", json=body, headers=AUTH
    )


def approve(repository, edited=None, version=None):
    return {
        "action": "approve",
        **({"statement": edited} if edited else {}),
        "expected_version": version or version_of(repository),
    }


@pytest.fixture
def post_review(repository):
    """投稿との矛盾から生成された review 候補。"""
    candidate = make_candidate(
        "post_1_4",
        type="review",
        target_rule_id="rule_1",
        review_reason="投稿の内容が公開ルールと矛盾しています",
        statement=statement("投稿にもとづく提案"),
    )
    repository.candidates[candidate.id] = candidate
    return candidate.id


@pytest.fixture(params=["stale", "post"])
def review_id(request, post_review):
    """経年確認(stale_rule)と投稿由来の review。どちらも同じ 3 つの操作を使う。"""
    return "stale_rule_1" if request.param == "stale" else post_review


@pytest.mark.parametrize("edited", [None, EDITED])
def test_approving_add_creates_rule(client, repository, edited):
    body = {"action": "approve", **({"statement": edited} if edited else {})}
    response = decide(client, "post_1_1", body)

    assert response.status_code == 200
    published = edited or statement("候補")
    rule_id = response.json()["rule"]["id"]
    rule = repository.rules[rule_id]
    assert rule.statement.model_dump() == published
    assert (rule.region, rule.updated_at, rule.last_reviewed_at) == ("sakai", NOW, None)
    candidate = repository.candidates["post_1_1"]
    assert candidate.status == "approved"
    # 提案文はそのまま、公開した文は decided_statement に残る。
    assert candidate.statement.model_dump() == statement("候補")
    assert candidate.decided_statement.model_dump() == published
    assert response.json()["candidate"]["decided_statement"] == published
    assert response.json()["rule"]["version"] == rule_version(rule)


def test_approving_several_adds_creates_separate_rules(client, repository):
    for i in range(2, 5):
        repository.candidates[f"post_2_{i}"] = make_candidate(
            f"post_2_{i}", statement=statement(f"候補{i}")
        )

    ids = [
        decide(client, f"post_2_{i}", {"action": "approve"}).json()["rule"]["id"]
        for i in range(2, 5)
    ]

    assert len(set(ids)) == 3
    assert {repository.rules[i].statement.ja for i in ids} == {
        "候補2。",
        "候補3。",
        "候補4。",
    }
    assert repository.rules["rule_1"].statement.model_dump() == statement(
        "既存のルール"
    )


@pytest.mark.parametrize("location", [{"lat": 34.5738, "lng": 135.4795}, None])
def test_approving_add_inherits_location(client, repository, location):
    # 場所に紐づく Candidate から作った Rule は、同じ location を持つ。
    candidate = make_candidate("post_1_4", location=location)
    repository.candidates[candidate.id] = candidate

    response = decide(client, "post_1_4", {"action": "approve"})

    assert response.status_code == 200
    rule_id = response.json()["rule"]["id"]
    assert repository.rules[rule_id].model_dump()["location"] == location
    assert response.json()["rule"]["location"] == location


@pytest.mark.parametrize("edited", [None, EDITED])
def test_approving_update_replaces_rule_text(client, repository, edited):
    response = decide(client, "post_1_2", approve(repository, edited))

    assert response.status_code == 200
    rule = repository.rules["rule_1"]
    assert rule.statement.model_dump() == (edited or statement("候補"))
    assert (rule.updated_at, rule.last_reviewed_at) == (NOW, None)
    candidate = repository.candidates["post_1_2"]
    assert candidate.status == "approved"
    assert candidate.statement.model_dump() == statement("候補")
    assert candidate.decided_statement == rule.statement
    assert response.json()["rule"]["version"] == version_of(repository)


def test_review_still_correct_only_moves_last_reviewed_at(
    client, repository, review_id
):
    proposals = {review_id: repository.candidates[review_id].statement}
    response = decide(client, review_id, approve(repository))

    assert response.status_code == 200
    rule = repository.rules["rule_1"]
    assert rule.statement.model_dump() == statement("既存のルール")
    assert (rule.updated_at, rule.last_reviewed_at) == (OLD, NOW)
    candidate = repository.candidates[review_id]
    assert candidate.status == "approved"
    # 提案文（投稿由来では公開文と違う）は残し、確認した公開ルールの文を別に残す。
    assert candidate.statement == proposals[review_id]
    assert candidate.decided_statement == rule.statement


def test_review_edit_and_approve_also_moves_last_reviewed_at(
    client, repository, review_id
):
    proposals = {review_id: repository.candidates[review_id].statement}
    response = decide(client, review_id, approve(repository, EDITED))

    assert response.status_code == 200
    rule = repository.rules["rule_1"]
    assert rule.statement.model_dump() == EDITED
    assert (rule.updated_at, rule.last_reviewed_at) == (NOW, NOW)
    candidate = repository.candidates[review_id]
    assert candidate.statement == proposals[review_id]
    assert candidate.decided_statement.model_dump() == EDITED


def test_review_reject_changes_neither_date(client, repository, review_id):
    before = repository.rules["rule_1"]
    response = decide(client, review_id, {"action": "reject"})

    assert response.status_code == 200
    assert repository.rules["rule_1"] == before
    assert repository.candidates[review_id].status == "rejected"


@pytest.mark.parametrize("candidate_id", ["post_1_1", "post_1_2", "stale_rule_1"])
def test_reject_leaves_rules_unchanged(client, repository, candidate_id):
    before = dict(repository.rules)
    response = decide(client, candidate_id, {"action": "reject"})

    assert response.status_code == 200
    assert response.json()["rule"] is None
    assert repository.candidates[candidate_id].status == "rejected"
    assert repository.candidates[candidate_id].decided_statement is None
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
        {"action": "approve", "expected_version": ""},
    ],
)
def test_rejects_invalid_decision_bodies(client, repository, body):
    response = decide(client, "post_1_1", body)

    assert response.status_code == 422
    assert repository.candidates["post_1_1"].status == "pending"


@pytest.mark.parametrize("candidate_id", ["post_1_2", "stale_rule_1"])
def test_approving_an_existing_rule_requires_expected_version(
    client, repository, candidate_id
):
    before = dict(repository.rules)
    response = decide(client, candidate_id, {"action": "approve"})

    assert response.status_code == 422
    assert repository.candidates[candidate_id].status == "pending"
    assert repository.rules == before


def test_already_decided_candidate_is_a_conflict(client, repository):
    response = decide(client, "post_1_3", {"action": "approve"})

    assert response.status_code == 409
    assert repository.candidates["post_1_3"].status == "rejected"
    assert set(repository.rules) == {"rule_1"}


def test_deciding_twice_is_a_conflict(client, repository):
    assert decide(client, "post_1_1", {"action": "approve"}).status_code == 200
    response = decide(client, "post_1_1", {"action": "reject"})

    assert response.status_code == 409
    assert repository.candidates["post_1_1"].status == "approved"


@pytest.mark.parametrize("candidate_id", ["post_1_2", "stale_rule_1"])
def test_approving_with_missing_target_rule_is_a_conflict(
    client, repository, candidate_id
):
    del repository.rules["rule_1"]
    response = decide(
        client, candidate_id, {"action": "approve", "expected_version": "v"}
    )

    assert response.status_code == 409
    assert repository.candidates[candidate_id].status == "pending"
    assert repository.rules == {}


@pytest.mark.parametrize("candidate_id", ["post_1_2", "stale_rule_1"])
def test_rejecting_with_missing_target_rule_is_allowed(
    client, repository, candidate_id
):
    # 削除済みのルールを対象にした不要な候補は、却下して片付けられる。
    del repository.rules["rule_1"]
    response = decide(client, candidate_id, {"action": "reject"})

    assert response.status_code == 200
    assert repository.candidates[candidate_id].status == "rejected"
    assert repository.rules == {}


@pytest.mark.parametrize(
    ("candidate_id", "edited"),
    [("post_1_2", None), ("stale_rule_1", None), ("stale_rule_1", EDITED)],
    ids=["update", "review-still-correct", "review-edit"],
)
def test_target_rule_in_another_region_is_a_conflict(
    client, repository, candidate_id, edited
):
    repository.candidates[candidate_id] = repository.candidates[
        candidate_id
    ].model_copy(update={"region": "osaka"})
    before = repository.rules["rule_1"]

    response = decide(client, candidate_id, approve(repository, edited))

    assert response.status_code == 409
    assert repository.candidates[candidate_id].status == "pending"
    assert repository.rules["rule_1"] == before


def test_unknown_candidate_is_not_found(client):
    response = decide(client, "post_9_9", {"action": "approve"})

    assert response.status_code == 404


# --- 古い画面からの上書き（version の不一致は 409、何も書き込まない） ---------------


def edit(client, version, text=EDITED):
    return client.patch(
        "/api/admin/rules/rule_1",
        json={"statement": text, "expected_version": version},
        headers=AUTH,
    )


def assert_nothing_written(repository, rule_before, candidate_ids=()):
    assert repository.rules["rule_1"] == rule_before
    for candidate_id in candidate_ids:
        assert repository.candidates[candidate_id].status == "pending"


def test_two_admins_editing_from_the_same_screen(client, repository):
    seen = version_of(repository)  # A と B が同じ内容を開いている
    assert edit(client, seen).status_code == 200  # A が先に保存
    after_a = repository.rules["rule_1"]

    response = edit(client, seen, statement("Bの編集"))  # B は古い画面から保存

    assert response.status_code == 409
    assert_nothing_written(repository, after_a)


def test_second_update_candidate_for_the_same_rule(client, repository):
    repository.candidates["post_1_5"] = make_candidate(
        "post_1_5", type="update", target_rule_id="rule_1"
    )
    seen = version_of(repository)
    assert decide(client, "post_1_2", approve(repository, version=seen)).is_success
    after_first = repository.rules["rule_1"]

    response = decide(client, "post_1_5", approve(repository, version=seen))

    assert response.status_code == 409
    assert_nothing_written(repository, after_first, ["post_1_5"])


def test_approving_an_old_candidate_after_a_direct_edit(client, repository):
    seen = version_of(repository)
    assert edit(client, seen).status_code == 200
    after_edit = repository.rules["rule_1"]

    response = decide(client, "post_1_2", approve(repository, version=seen))

    assert response.status_code == 409
    assert_nothing_written(repository, after_edit, ["post_1_2"])


def test_review_after_the_rule_changed(client, repository, review_id):
    seen = version_of(repository)
    assert edit(client, seen).status_code == 200
    after_edit = repository.rules["rule_1"]

    response = decide(client, review_id, approve(repository, version=seen))

    assert response.status_code == 409
    assert_nothing_written(repository, after_edit, [review_id])


def test_still_correct_review_changes_the_version(client, repository, review_id):
    # 文と updated_at が変わらない「問題なし」でも、古い画面からの編集は検知できる。
    seen = version_of(repository)
    assert decide(client, review_id, approve(repository, version=seen)).is_success

    assert version_of(repository) != seen
    assert edit(client, seen).status_code == 409


# --- 公開ルールの一覧・編集 -------------------------------------------------


def test_lists_rules_newest_first(client, repository):
    repository.rules["rule_2"] = Rule(
        id="rule_2", region="sakai", statement=statement("新しいルール"), updated_at=NOW
    )
    repository.rules["rule_3"] = Rule(
        id="rule_3", region="osaka", statement=statement("別の地域"), updated_at=NOW
    )

    response = client.get("/api/admin/rules?region=sakai", headers=AUTH)

    assert response.status_code == 200
    assert [r["id"] for r in response.json()] == ["rule_2", "rule_1"]
    assert response.json()[1]["version"] == version_of(repository)


def test_edits_rule_text_and_moves_updated_at(client, repository):
    response = edit(client, version_of(repository))

    assert response.status_code == 200
    rule = repository.rules["rule_1"]
    assert rule.statement.model_dump() == EDITED
    assert (rule.updated_at, rule.last_reviewed_at) == (NOW, None)
    assert response.json()["id"] == "rule_1"
    # 続けて編集するときは、返ってきた version を使う。
    assert response.json()["version"] == version_of(repository)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"statement": EDITED},
        {"statement": {"ja": "", "en": "x"}, "expected_version": "v"},
        {"statement": EDITED, "expected_version": "v", "region": "x"},
    ],
    ids=["empty", "no-version", "blank-ja", "extra-field"],
)
def test_rejects_invalid_rule_edits(client, repository, body):
    response = client.patch("/api/admin/rules/rule_1", json=body, headers=AUTH)

    assert response.status_code == 422
    assert repository.rules["rule_1"].updated_at == OLD


def test_editing_unknown_rule_is_not_found(client):
    response = client.patch(
        "/api/admin/rules/rule_9",
        json={"statement": EDITED, "expected_version": "v"},
        headers=AUTH,
    )

    assert response.status_code == 404


def test_contention_that_never_settles_is_a_conflict(client, repository):
    def contended(work):
        raise TransactionContention("too many concurrent changes")

    repository.run_transaction = contended
    response = decide(client, "post_1_2", approve(repository))

    assert response.status_code == 409
    assert repository.candidates["post_1_2"].status == "pending"


def test_flag_for_a_candidate_generated_by_the_batch(client, repository):
    """機能B が記録した版と、機能D の一覧の警告がつながっていること（#39）。"""
    from services.candidate_generation import run_candidate_batch

    gemini = Mock()
    gemini.generate.return_value = GeminiOutput(
        candidates=[
            {
                "type": "update",
                "statement": statement("提案"),
                "target_rule_id": "rule_1",
            }
        ],
        duplicates=[],
    )
    batch = run_candidate_batch(
        [repository.posts["post_1"]],
        list(repository.rules.values()),
        [],
        generator=gemini,
        post_ids=["post_7"],
    )
    generated = batch.posts[0].candidates[0]
    repository.candidates[generated.id] = generated

    def flag():
        body = client.get("/api/admin/candidates", headers=AUTH).json()
        return {c["id"]: c for c in body}[generated.id]["rule_changed_since_generated"]

    assert flag() is False
    edit(client, version_of(repository))  # 別の管理者がルールを編集
    assert flag() is True
