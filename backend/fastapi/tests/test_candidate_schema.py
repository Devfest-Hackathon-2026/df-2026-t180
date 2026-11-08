import pytest
from pydantic import ValidationError

from schemas.candidate import Candidate

BASE = {
    "id": "abc123_1",
    "post_id": "abc123",
    "region": "sakai",
    "statement": {"ja": "静かにしてください。", "en": "Please keep quiet."},
    "status": "pending",
    "type": "add",
}


@pytest.mark.parametrize(
    "fields",
    [
        {"type": "add"},
        {"type": "update", "target_rule_id": "rule_001"},
        {
            "type": "review",
            "target_rule_id": "rule_001",
            "review_reason": "既存ルールと矛盾",
        },
    ],
)
@pytest.mark.parametrize("status", ["pending", "approved", "rejected"])
def test_candidate_type_round_trip_preserves_existing_fields(fields, status):
    # 各候補種別・採否状態で、JSON変換後も全項目が保持されることを確認する。
    payload = {**BASE, **fields, "status": status}
    candidate = Candidate.model_validate(payload)
    assert candidate.model_dump(exclude_unset=True) == payload
    assert Candidate.model_validate_json(candidate.model_dump_json()) == candidate


def test_candidate_type_is_required():
    # typeを省略すると、必須項目の欠落として検証エラーになることを確認する。
    payload = {k: v for k, v in BASE.items() if k != "type"}
    with pytest.raises(ValidationError) as error:
        Candidate.model_validate(payload)
    assert error.value.errors()[0]["loc"] == ("type",)
    assert error.value.errors()[0]["type"] == "missing"


def test_optional_candidate_fields_default_to_none():
    # addで対象ルールIDと確認理由を省略すると、どちらもNoneになることを確認する。
    candidate = Candidate.model_validate(BASE)
    assert candidate.target_rule_id is None
    assert candidate.review_reason is None


@pytest.mark.parametrize("kind", [None, "", "ADD", "delete", 123, True, [], {}])
def test_candidate_rejects_unsupported_type(kind):
    # 未定義の候補種別や文字列以外の値をtypeに指定すると拒否されることを確認する。
    with pytest.raises(ValidationError):
        Candidate.model_validate({**BASE, "type": kind})


@pytest.mark.parametrize(
    "fields",
    [
        {"type": "add", "target_rule_id": "rule_001"},
        {"type": "update"},
        {"type": "update", "target_rule_id": None},
        {"type": "update", "target_rule_id": ""},
        {"type": "update", "target_rule_id": " \n\t"},
        {"type": "review"},
        {"type": "review", "target_rule_id": "rule_001", "review_reason": None},
        {"type": "review", "target_rule_id": "rule_001", "review_reason": ""},
        {"type": "review", "target_rule_id": "rule_001", "review_reason": " \n\t"},
        {"type": "review", "target_rule_id": " ", "review_reason": "確認が必要"},
    ],
)
def test_candidate_rejects_invalid_field_combinations(fields):
    # 候補種別ごとの対象ID・確認理由の不正な組み合わせを拒否することを確認する。
    with pytest.raises(ValidationError):
        Candidate.model_validate({**BASE, **fields})


@pytest.mark.parametrize("field", ["target_rule_id", "review_reason"])
@pytest.mark.parametrize("value", [123, True, [], {}])
def test_candidate_rejects_non_string_optional_fields(field, value):
    # 対象ID・確認理由の数値・真偽値・リスト・辞書を拒否することを確認する。
    with pytest.raises(ValidationError):
        Candidate.model_validate(
            {
                **BASE,
                "type": "review",
                "target_rule_id": "rule_001",
                "review_reason": "確認",
                field: value,
            }
        )


@pytest.mark.parametrize("target", [None, "", " \n\t"])
def test_review_requires_nonempty_target_rule_id(target):
    # 理由が有効でも、reviewの対象IDのNone・空文字・空白を拒否することを確認する。
    with pytest.raises(ValidationError, match="target_rule_id"):
        Candidate.model_validate(
            {
                **BASE,
                "type": "review",
                "target_rule_id": target,
                "review_reason": "確認が必要",
            }
        )


def test_review_rejects_missing_target_with_valid_reason():
    # 理由が有効でも、reviewの対象ID省略がエラーになることを確認する。
    with pytest.raises(ValidationError, match="review requires target_rule_id"):
        Candidate.model_validate(
            {
                **BASE,
                "type": "review",
                "review_reason": "確認が必要",
            }
        )
