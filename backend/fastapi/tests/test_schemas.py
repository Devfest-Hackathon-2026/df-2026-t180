from datetime import date

import pytest
from pydantic import ValidationError

from schemas.admin import Admin
from schemas.candidate import Candidate
from schemas.post import Post
from schemas.rule import Rule

STATEMENT = {
    "ja": "この場所では騒音にご注意ください。",
    "en": "Please keep noise to a minimum here.",
}
ADMIN = {"firebase_uid": "firebase-user-001", "employee_name": "管理者"}
POST = {"text": "夜間は静かにしてください。", "region": "sakai"}
CANDIDATE = {
    "id": "candidate_001",
    "region": "sakai",
    "statement": STATEMENT,
    "status": "pending",
}
RULE = {
    "id": "rule_001",
    "region": "sakai",
    "statement": STATEMENT,
    "updated_at": "2026-11-07",
}


@pytest.mark.parametrize(
    ("schema", "payload"),
    [(Admin, ADMIN), (Post, POST), (Candidate, CANDIDATE), (Rule, RULE)],
)
def test_schema_json_round_trip(schema, payload):
    # 正常なデータをJSONに変換し、読み戻しても内容が変わらないことを確認する。
    model = schema.model_validate(payload)

    assert schema.model_validate_json(model.model_dump_json()) == model
    assert model.model_dump(mode="json", exclude_unset=True) == payload


@pytest.mark.parametrize("reason", [None, "", "音", "夜間の騒音で眠れないため。"])
def test_post_accepts_optional_reason(reason):
    # 任意の投稿理由には、null・空文字・1文字・通常の文章を指定できることを確認する。
    assert Post(**POST, reason=reason).reason == reason


@pytest.mark.parametrize(
    ("schema", "payload", "fields"),
    [
        (Admin, ADMIN, ["firebase_uid", "employee_name"]),
        (Post, POST, ["text", "region"]),
        (Candidate, CANDIDATE, ["id", "region"]),
        (Rule, RULE, ["id", "region"]),
    ],
)
@pytest.mark.parametrize("value", ["a", "堺"])
def test_schema_accepts_single_character_strings(schema, payload, fields, value):
    # 必須文字列に半角英字・日本語を1文字だけ指定しても受け付けることを確認する。
    for field in fields:
        model = schema.model_validate({**payload, field: value})
        assert getattr(model, field) == value


@pytest.mark.parametrize("schema,payload", [(Candidate, CANDIDATE), (Rule, RULE)])
def test_schema_accepts_single_character_statement(schema, payload):
    # 候補・公開ルールの日英文章が、それぞれ1文字でも受け付けられることを確認する。
    model = schema.model_validate({**payload, "statement": {"ja": "静", "en": "Q"}})

    assert model.statement.ja == "静"
    assert model.statement.en == "Q"


@pytest.mark.parametrize("status", ["pending", "approved", "rejected"])
def test_candidate_accepts_valid_status(status):
    # 確認待ち・採用済み・不採用の3状態を受け付け、JSON出力でも保持することを確認する。
    model = Candidate.model_validate({**CANDIDATE, "status": status})

    assert model.status == status
    assert model.model_dump(mode="json")["status"] == status


@pytest.mark.parametrize("status", ["unknown", "", " ", "Pending", None, 123, True])
def test_candidate_rejects_invalid_status(status):
    # 定義外の状態、空文字、空白、null、文字列以外の値を拒否することを確認する。
    with pytest.raises(ValidationError) as exc_info:
        Candidate.model_validate({**CANDIDATE, "status": status})

    assert exc_info.value.errors()[0]["loc"] == ("status",)
    assert exc_info.value.errors()[0]["type"] == "literal_error"


def test_candidate_requires_status():
    # 状態の省略時にデフォルト値を補わず、必須項目のエラーになることを確認する。
    payload = {key: value for key, value in CANDIDATE.items() if key != "status"}

    with pytest.raises(ValidationError) as exc_info:
        Candidate.model_validate(payload)

    assert exc_info.value.errors()[0]["loc"] == ("status",)
    assert exc_info.value.errors()[0]["type"] == "missing"


def test_post_defaults_reason_to_none():
    # 投稿理由を省略した場合は、Noneとして扱われることを確認する。
    assert Post(**POST).reason is None


def test_rule_parses_design_example_date():
    # 設計書の更新日文字列が、Pythonの日付型に変換されることを確認する。
    assert Rule(**RULE).updated_at == date(2026, 11, 7)


@pytest.mark.parametrize(
    ("schema", "payload"),
    [(Admin, ADMIN), (Post, POST), (Candidate, CANDIDATE), (Rule, RULE)],
)
def test_schema_rejects_missing_required_fields(schema, payload):
    # 必須項目を1つずつ省略し、どの項目が欠けてもエラーになることを確認する。
    for field in payload:
        incomplete = {key: value for key, value in payload.items() if key != field}
        with pytest.raises(ValidationError):
            schema.model_validate(incomplete)


@pytest.mark.parametrize("invalid", ["", " \n\t", None, 123])
@pytest.mark.parametrize(
    ("schema", "payload", "fields"),
    [
        (Admin, ADMIN, ["firebase_uid", "employee_name"]),
        (Post, POST, ["text", "region"]),
        (Candidate, CANDIDATE, ["id", "region"]),
        (Rule, RULE, ["id", "region"]),
    ],
)
def test_schema_rejects_invalid_required_strings(schema, payload, fields, invalid):
    # 必須文字列に空文字・空白のみ・null・数値を指定するとエラーになることを確認する。
    for field in fields:
        with pytest.raises(ValidationError):
            schema.model_validate({**payload, field: invalid})


@pytest.mark.parametrize("schema,payload", [(Candidate, CANDIDATE), (Rule, RULE)])
@pytest.mark.parametrize(
    "statement",
    [
        None,
        "plain text",
        {"ja": "日本語のみ"},
        {"en": "English only"},
        {"ja": "", "en": "English"},
        {"ja": "日本語", "en": " \n"},
        {"ja": 123, "en": "English"},
        {**STATEMENT, "fr": "French"},
    ],
)
def test_schema_rejects_invalid_statement(schema, payload, statement):
    # 日英文章の欠落、不正な型、空の文章、未対応言語の追加を拒否することを確認する。
    with pytest.raises(ValidationError):
        schema.model_validate({**payload, "statement": statement})


@pytest.mark.parametrize("updated_at", [None, "not-a-date", "2026-02-30"])
def test_rule_rejects_invalid_date(updated_at):
    # 更新日にnull、不正な文字列、存在しない日付を指定するとエラーになることを確認する。
    with pytest.raises(ValidationError):
        Rule.model_validate({**RULE, "updated_at": updated_at})


def test_post_rejects_non_string_reason():
    # 任意項目の投稿理由でも、数値は受け付けないことを確認する。
    with pytest.raises(ValidationError):
        Post(**POST, reason=123)


@pytest.mark.parametrize(
    ("schema", "payload", "extra"),
    [
        (Admin, ADMIN, {"password": "must-not-be-stored"}),
        (Post, POST, {"unexpected": "value"}),
        (Candidate, CANDIDATE, {"approved": True}),
        (Rule, RULE, {"unexpected": "value"}),
    ],
)
def test_schema_rejects_unknown_fields(schema, payload, extra):
    # パスワードや採否フラグなど、定義していない項目を受け付けないことを確認する。
    with pytest.raises(ValidationError):
        schema.model_validate({**payload, **extra})
