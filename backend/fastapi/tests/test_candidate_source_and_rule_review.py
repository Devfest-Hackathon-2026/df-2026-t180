from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from schemas.candidate import Candidate
from schemas.rule import Rule

BASE = {
    "id": "candidate_1",
    "region": "sakai",
    "statement": {"ja": "静かにしてください。", "en": "Please keep quiet."},
    "status": "pending",
    "type": "review",
    "target_rule_id": "rule_1",
    "review_reason": "内容の確認が必要",
}


@pytest.mark.parametrize("source_fields", [{}, {"source": "post"}])
def test_post_source_preserves_backward_compatibility(source_fields):
    # source省略時も、投稿IDを持つ従来の候補をpostとして読み戻せる。
    candidate = Candidate(**BASE, post_id="post_1", **source_fields)
    assert candidate.source == "post"
    assert candidate.post_id == "post_1"
    assert Candidate.model_validate_json(candidate.model_dump_json()) == candidate


@pytest.mark.parametrize("source_fields", [{}, {"source": "post"}])
@pytest.mark.parametrize(
    "id_fields",
    [{}, {"post_id": None}, {"post_id": ""}, {"post_id": " "}, {"post_id": 123}],
)
def test_post_source_requires_valid_post_id(source_fields, id_fields):
    # sourceを省略しても、投稿IDの欠落・不正値は許可しない。
    with pytest.raises(ValidationError):
        Candidate(**BASE, **source_fields, **id_fields)


@pytest.mark.parametrize("id_fields", [{}, {"post_id": None}])
@pytest.mark.parametrize("status", ["pending", "approved", "rejected"])
def test_stale_rule_candidate_round_trip(id_fields, status):
    # 経年確認は実在しない投稿IDなしで、既存の採否状態と共存できる。
    candidate = Candidate(
        **{**BASE, "source": "stale_rule", "status": status}, **id_fields
    )
    assert candidate.post_id is None
    assert candidate.type == "review"
    assert Candidate.model_validate_json(candidate.model_dump_json()) == candidate


@pytest.mark.parametrize(
    "changes",
    [
        {"post_id": "post_1"},
        {"post_id": ""},
        {"post_id": 123},
        {"type": "add", "target_rule_id": None},
        {"type": "update"},
        {"target_rule_id": None},
        {"target_rule_id": ""},
        {"target_rule_id": " "},
        {"review_reason": None},
        {"review_reason": ""},
        {"review_reason": " "},
    ],
)
def test_stale_rule_rejects_invalid_combinations(changes):
    # 経年確認の投稿ID指定・review以外・対象IDや理由の不足を拒否する。
    with pytest.raises(ValidationError):
        Candidate(**{**BASE, "source": "stale_rule", **changes})


@pytest.mark.parametrize("field", ["target_rule_id", "review_reason"])
def test_stale_rule_requires_target_and_reason(field):
    # 経年確認の対象ID・確認理由を省略した場合も検証に失敗する。
    payload = {**BASE, "source": "stale_rule"}
    del payload[field]
    with pytest.raises(ValidationError):
        Candidate(**payload)


@pytest.mark.parametrize("source", [None, "", "unknown", 123])
def test_invalid_candidate_source_is_rejected(source):
    # 定義した2種類以外の生成元は受け付けない。
    with pytest.raises(ValidationError):
        Candidate(**BASE, source=source, post_id="post_1")


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"last_reviewed_at": None},
        {"last_reviewed_at": "2026-11-09T00:00:00Z"},
        {"last_reviewed_at": datetime(2026, 11, 9, tzinfo=timezone.utc)},
    ],
)
def test_rule_accepts_optional_utc_review_time(fields):
    # 確認日時の追加後も更新日はdate型を維持し、日時は独立して保持する。
    rule = Rule(
        id="rule_1",
        region="sakai",
        statement=BASE["statement"],
        updated_at="2023-11-08T00:00:00Z",
        **fields,
    )
    assert rule.updated_at == datetime(2023, 11, 8, tzinfo=timezone.utc)
    assert isinstance(rule.updated_at, datetime)
    if fields.get("last_reviewed_at") is None:
        assert rule.last_reviewed_at is None
    else:
        assert rule.last_reviewed_at == datetime(2026, 11, 9, tzinfo=timezone.utc)
    assert Rule.model_validate_json(rule.model_dump_json()) == rule


@pytest.mark.parametrize("field", ["updated_at", "last_reviewed_at"])
@pytest.mark.parametrize(
    "value",
    [
        "invalid",
        "2026-02-30T00:00:00Z",
        "2026-11-09",
        "2026-11-09T00:00:00",
        "2026-11-09T00:00:00+09:00",
        datetime(2026, 11, 9),
        date(2026, 11, 9),
        {},
        [],
    ],
)
def test_rule_rejects_invalid_or_non_utc_review_time(field, value):
    # 不正日時・naive日時・UTC以外を、共通のUtcDatetime規則で拒否する。
    with pytest.raises(ValidationError):
        Rule(
            id="rule_1",
            region="sakai",
            statement=BASE["statement"],
            **{"updated_at": "2023-11-08T00:00:00Z", field: value},
        )
