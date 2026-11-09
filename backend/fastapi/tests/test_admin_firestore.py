"""管理者 API の Firestore 結合テスト（Firestore Emulator を使う）。

FIRESTORE_EMULATOR_HOST が設定されているときだけ実行する。手順は README を参照。

本物の FirestoreAdminRepository を使い、Fake では再現できない次の点を確かめる。

- 同時に採否・編集したときの競合検出と再試行（再試行時に状態を再検証すること）
- コミットに失敗したとき、候補とルールのどちらも変わらないこと
- 既存ドキュメントの更新で、モデルにないフィールドが消えないこと
"""

import os
import threading
import uuid
from datetime import datetime, timezone

import pytest
import requests
from fastapi import HTTPException

pytestmark = pytest.mark.skipif(
    not os.getenv("FIRESTORE_EMULATOR_HOST"),
    reason="FIRESTORE_EMULATOR_HOST is not set",
)

from google.api_core.exceptions import Aborted  # noqa: E402
from google.cloud import firestore  # noqa: E402
from google.cloud.firestore_v1.transaction import Transaction  # noqa: E402

from api import admin as admin_api  # noqa: E402
from repositories.admin import FirestoreAdminRepository  # noqa: E402
from schemas.admin import CandidateDecision, RuleEdit  # noqa: E402
from services.admin_decisions import rule_version  # noqa: E402

NOW = datetime(2026, 11, 9, 6, 0, tzinfo=timezone.utc)
OLD = datetime(2023, 11, 3, tzinfo=timezone.utc)
EDITED = {"ja": "修正した文です。", "en": "An edited sentence."}


def statement(text):
    return {"ja": f"{text}。", "en": f"{text}."}


@pytest.fixture
def client():
    # テストごとに別のプロジェクトを使い、データが混ざらないようにする。
    project = f"demo-admin-{uuid.uuid4().hex[:8]}"
    db = firestore.Client(project=project)
    yield db
    host = os.environ["FIRESTORE_EMULATOR_HOST"]
    requests.delete(
        f"http://{host}/emulator/v1/projects/{project}/databases/(default)/documents",
        timeout=10,
    )


@pytest.fixture
def repository(client):
    client.collection("rules").document("rule_1").set(
        {
            "id": "rule_1",
            "region": "sakai",
            "statement": statement("既存のルール"),
            "updated_at": OLD,
            "last_reviewed_at": None,
            # 他機能（#15 の location など）が追加したフィールドの代わり
            "location": {"lat": 34.57, "lng": 135.48},
        }
    )
    candidates = {
        "post_1_1": {"type": "add"},
        "post_1_2": {"type": "update", "target_rule_id": "rule_1"},
        "post_1_5": {"type": "update", "target_rule_id": "rule_1"},
        "post_1_4": {
            "type": "review",
            "target_rule_id": "rule_1",
            "review_reason": "投稿の内容が公開ルールと矛盾しています",
        },
    }
    for candidate_id, fields in candidates.items():
        client.collection("candidates").document(candidate_id).set(
            {
                "source": "post",
                "post_id": "post_1",
                "region": "sakai",
                "statement": statement(f"候補{candidate_id}"),
                "status": "pending",
                "target_rule_id": None,
                "review_reason": None,
                "created_by_batch": "batch_1",  # モデルにないフィールド
                **fields,
            }
        )
    return FirestoreAdminRepository(client)


def rule_doc(client, rule_id="rule_1"):
    return client.collection("rules").document(rule_id).get().to_dict()


def candidate_doc(client, candidate_id):
    return client.collection("candidates").document(candidate_id).get().to_dict()


def version(repository):
    return rule_version(repository.get_rules(["rule_1"])["rule_1"])


def decide(repository, candidate_id, **body):
    return admin_api.decide(
        candidate_id, CandidateDecision(**body), "admin_uid", repository, NOW
    )


def edit(repository, expected_version, text=EDITED):
    return admin_api.update_rule(
        "rule_1",
        RuleEdit(statement=text, expected_version=expected_version),
        "admin_uid",
        repository,
        NOW,
    )


def run_together(*calls):
    """呼び出しを同時に始めて結果を返す（成功なら "ok"、HTTP エラーなら状態コード）。"""
    start = threading.Barrier(len(calls))
    results = [None] * len(calls)

    def run(i, call):
        start.wait()
        try:
            call()
            results[i] = "ok"
        except HTTPException as error:
            results[i] = error.status_code
        except Exception as error:  # 想定外の失敗も結果として残す
            results[i] = repr(error)[:300]

    threads = [threading.Thread(target=run, args=(i, c)) for i, c in enumerate(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    return results


# --- 保存形式 ---------------------------------------------------------------------


def test_updates_keep_fields_the_model_does_not_know(client, repository):
    decide(
        repository, "post_1_2", action="approve", expected_version=version(repository)
    )

    rule = rule_doc(client)
    assert rule["statement"] == statement("候補post_1_2")
    assert rule["location"] == {"lat": 34.57, "lng": 135.48}
    candidate = candidate_doc(client, "post_1_2")
    assert candidate["status"] == "approved"
    assert candidate["created_by_batch"] == "batch_1"


def test_version_is_the_same_after_reading_back(client, repository):
    # 書き込んだ直後に返す version と、読み直して計算した version が一致する
    # （Firestore に保存した日時の精度・タイムゾーンで値が変わらない）。
    result = edit(repository, version(repository))

    assert result.version == version(repository)


def test_approving_add_creates_a_new_document(client, repository):
    result = decide(repository, "post_1_1", action="approve")

    assert result.rule.id != "rule_1"
    assert rule_doc(client, result.rule.id)["statement"] == statement("候補post_1_1")


# --- 同時実行 ---------------------------------------------------------------------


def assert_at_most_one_wins(results):
    """同時の操作は、多くても 1 つだけ成功し、残りは 409 になる（500 にならない）。

    Emulator ではロックの競合で両方とも再試行の上限に達し、両方 409 になることもある。
    その場合は何も書き込まれない。
    """
    assert all(r in ("ok", 409) for r in results), results
    assert results.count("ok") <= 1


def test_same_candidate_approved_twice_at_once(client, repository):
    results = run_together(
        lambda: decide(repository, "post_1_1", action="approve"),
        lambda: decide(repository, "post_1_1", action="approve"),
    )

    assert_at_most_one_wins(results)
    created = [d.id for d in client.collection("rules").stream() if d.id != "rule_1"]
    assert len(created) == results.count("ok")
    status = candidate_doc(client, "post_1_1")["status"]
    assert status == ("approved" if "ok" in results else "pending")


def test_two_update_candidates_for_the_same_rule_at_once(client, repository):
    seen = version(repository)
    results = run_together(
        lambda: decide(repository, "post_1_2", action="approve", expected_version=seen),
        lambda: decide(repository, "post_1_5", action="approve", expected_version=seen),
    )

    assert_at_most_one_wins(results)
    statuses = [candidate_doc(client, i)["status"] for i in ("post_1_2", "post_1_5")]
    assert statuses.count("approved") == results.count("ok")


def test_direct_edit_and_approval_at_once(client, repository):
    seen = version(repository)
    results = run_together(
        lambda: edit(repository, seen),
        lambda: decide(repository, "post_1_4", action="approve", expected_version=seen),
    )

    assert_at_most_one_wins(results)
    if "ok" not in results:
        assert rule_doc(client)["statement"] == statement("既存のルール")


def test_retry_checks_the_state_again(client, repository, monkeypatch):
    """1 回目のコミットが競合で中断されると、再試行で読み直して 409 になる。

    Firestore はトランザクション中に読んだドキュメントをロックするため、別の書き込みは
    途中に割り込めない。ここでは 1 回目のコミットを、その間に別の管理者が編集した
    状態で Aborted（競合）にして、SDK の再試行を起こす。
    """
    seen = version(repository)
    attempts = []
    original_commit = Transaction._commit

    def commit(self):
        attempts.append(1)
        if len(attempts) == 1:
            self._rollback()
            client.collection("rules").document("rule_1").update(
                {"statement": statement("別の管理者の編集"), "updated_at": NOW}
            )
            raise Aborted("simulated contention")
        return original_commit(self)

    monkeypatch.setattr(Transaction, "_commit", commit)

    with pytest.raises(HTTPException) as error:
        decide(repository, "post_1_2", action="approve", expected_version=seen)

    assert error.value.status_code == 409
    assert len(attempts) == 1  # 2 回目は読み直した時点で 409 になり、コミットしない
    assert rule_doc(client)["statement"] == statement("別の管理者の編集")
    assert candidate_doc(client, "post_1_2")["status"] == "pending"


def test_contention_that_never_settles_is_409(client, repository, monkeypatch):
    def always_aborted(self):
        raise Aborted("simulated contention")

    monkeypatch.setattr(Transaction, "_commit", always_aborted)

    with pytest.raises(HTTPException) as error:
        decide(repository, "post_1_1", action="approve")

    assert error.value.status_code == 409
    assert candidate_doc(client, "post_1_1")["status"] == "pending"


def test_failed_commit_changes_neither_document(client, repository, monkeypatch):
    # 新しいルールのIDが既存のものと重なり、create がコミット時に失敗する場合。
    from repositories import admin as admin_repository

    monkeypatch.setattr(
        admin_repository.FirestoreAdminTransaction, "new_rule_id", lambda self: "rule_1"
    )
    before = rule_doc(client)

    with pytest.raises(Exception):
        decide(repository, "post_1_1", action="approve")

    assert rule_doc(client) == before
    assert candidate_doc(client, "post_1_1")["status"] == "pending"
