import json
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
from google import genai
from google.auth.credentials import AnonymousCredentials
from pydantic import ValidationError

from schemas.candidate import Candidate
from schemas.post import Post, StoredPost
from schemas.rule import Rule
from services.candidate_generation import (
    CandidateGenerationError,
    GeminiGenerator,
    GeminiOutput,
    run_candidate_batch,
)

STATEMENT = {"ja": "静かにしてください。", "en": "Please keep quiet."}
POST = Post(text="夜は騒がないでほしい", region="sakai")
RULE = Rule(
    id="r1", region="sakai", statement=STATEMENT, updated_at="2026-01-01T00:00:00Z"
)
TODAY = date(2026, 11, 8)


def draft(kind="add", **extra):
    # Geminiが返す候補データを、種別と追加項目から組み立てる。
    return {"type": kind, "statement": STATEMENT, **extra}


def make_generator(candidates=None, duplicates=None):
    # 実APIを呼ばず、指定したJSONを返すGeminiモックを作る。
    client = Mock()
    client.models.generate_content.return_value.text = json.dumps(
        {
            "candidates": candidates if candidates is not None else [draft()],
            "duplicates": duplicates or [],
        }
    )
    return GeminiGenerator(client, "test-model")


def run(generator, posts=None, rules=None, candidates=None, **kwargs):
    # 投稿IDと判定日を補い、共通のテスト入力でバッチを実行する。
    selected_posts = [POST] if posts is None else posts
    post_ids = kwargs.pop("post_ids", [f"post_{i}" for i in range(len(selected_posts))])
    return run_candidate_batch(
        selected_posts,
        [RULE] if rules is None else rules,
        candidates or [],
        generator=generator,
        post_ids=post_ids,
        today=TODAY,
        **kwargs,
    )


@pytest.mark.parametrize(
    "kind,extra",
    [
        ("add", {}),
        ("update", {"target_rule_id": "r1"}),
        ("review", {"target_rule_id": "r1", "review_reason": "既存情報と矛盾"}),
    ],
)
def test_generate_localized_pending_candidate(kind, extra):
    # 各種別の日英候補が、投稿IDを持つpending状態で生成されることを確認する。
    generator = make_generator([draft(kind, **extra)])
    result = run(generator)
    candidate = result.posts[0].candidates[0]
    assert candidate.status == "pending"
    assert candidate.type == kind
    assert candidate.statement.model_dump() == STATEMENT
    assert candidate.id
    assert candidate.post_id == "post_0"
    assert candidate.id == "post_0_1"
    assert candidate.region == POST.region
    assert result.posts[0].post_index == 0
    config = generator.client.models.generate_content.call_args.kwargs["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema


@pytest.mark.parametrize("source", ["rule", "candidate"])
def test_semantic_duplicate_returns_reason_without_candidate(source):
    # 重複判定時は候補を作らず、重複先と理由を返すことを確認する。
    candidate = Candidate(
        id="c1",
        post_id="existing_post",
        region="sakai",
        statement=STATEMENT,
        type="add",
        status="pending",
    )
    generator = make_generator(
        [],
        [
            {
                "source": source,
                "id": "r1" if source == "rule" else "c1",
                "reason": "表現は異なるが意味が同じ",
            }
        ],
    )
    result = run(generator, candidates=[candidate])
    assert result.posts[0].candidates == []
    assert result.posts[0].duplicates[0].reason == "表現は異なるが意味が同じ"


def test_batch_compares_prior_generated_candidates_and_filters_region():
    # 同じ地域だけを比較し、先に生成した候補も後続の比較に使うことを確認する。
    other = RULE.model_copy(update={"id": "other", "region": "osaka"})
    generator = make_generator()
    run(generator, posts=[POST, POST], rules=[RULE, other])
    calls = generator.client.models.generate_content.call_args_list
    first = json.loads(calls[0].kwargs["contents"])
    second = json.loads(calls[1].kwargs["contents"])
    assert [r["id"] for r in first["rules"]] == ["r1"]
    assert len(second["candidates"]) == 1


@pytest.mark.parametrize(
    "updated,expected",
    [
        ("2023-11-08", 1),
        ("2023-11-09", 0),
        ("2020-02-29", 1),
    ],
)
def test_stale_calendar_year_boundary(updated, expected):
    # 3年経過日の当日と前日で、経年確認の生成有無が変わることを確認する。
    rule = RULE.model_copy(
        update={"updated_at": datetime.fromisoformat(updated + "T00:00:00+00:00")}
    )
    generator = make_generator()
    result = run(generator, posts=[], rules=[rule])
    assert len(result.stale_candidates) == expected
    generator.client.models.generate_content.assert_not_called()
    if expected:
        candidate = result.stale_candidates[0]
        assert candidate.type == "review"
        assert candidate.target_rule_id == rule.id
        assert candidate.status == "pending"
        assert candidate.statement == rule.statement


def test_stale_threshold_is_configurable_and_leap_day_clamps():
    # 判定年数を変更でき、2月29日の周年は平年の2月28日になることを確認する。
    rule = RULE.model_copy(
        update={"updated_at": datetime(2020, 2, 29, tzinfo=timezone.utc)}
    )
    generator = make_generator()
    result = run_candidate_batch(
        [], [rule], [], generator=generator, today=date(2023, 2, 28), stale_years=3
    )
    assert len(result.stale_candidates) == 1
    assert run(generator, posts=[], rules=[rule], stale_years=10).stale_candidates == []


@pytest.mark.parametrize("kind", ["review", "update"])
def test_existing_pending_review_prevents_repeat_age_candidate(kind):
    # pendingの更新・確認候補があれば経年確認を重ねて作らないことを確認する。
    rule = RULE.model_copy(
        update={"updated_at": datetime(2020, 1, 1, tzinfo=timezone.utc)}
    )
    candidate = Candidate(
        id="c1",
        post_id="existing_post",
        region="sakai",
        statement=STATEMENT,
        type=kind,
        target_rule_id="r1",
        review_reason="確認中",
        status="pending",
    )
    assert not run(
        make_generator(), posts=[], rules=[rule], candidates=[candidate]
    ).stale_candidates


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "null",
        "{}",
        '{"candidates":[]}',
        '{"duplicates":[]}',
        json.dumps({"candidates": [draft("delete")], "duplicates": []}),
        json.dumps({"candidates": [{"type": "add"}], "duplicates": []}),
        json.dumps({"candidates": [draft(status="approved")], "duplicates": []}),
        json.dumps({"candidates": [draft(id="chosen")], "duplicates": []}),
        json.dumps(
            {"candidates": [draft(statement={"ja": 123, "en": "x"})], "duplicates": []}
        ),
        "",
        None,
    ],
)
def test_invalid_gemini_output_fails(payload):
    # 不正JSON・必須項目不足・余計な項目を含むGemini応答を拒否することを確認する。
    generator = make_generator()
    generator.client.models.generate_content.return_value.text = payload
    with pytest.raises(CandidateGenerationError, match="Invalid Gemini JSON"):
        run(generator)


@pytest.mark.parametrize(
    "candidate",
    [
        draft("update"),
        draft("review"),
        draft("review", review_reason="確認が必要"),
        draft("review", target_rule_id="r1"),
        draft("review", target_rule_id="missing", review_reason="確認が必要"),
        draft("add", target_rule_id="r1"),
        draft("update", target_rule_id="other-region"),
    ],
)
def test_invalid_candidate_combinations_and_references(candidate):
    # 項目の組み合わせや対象ルールIDが不正な生成候補を拒否することを確認する。
    with pytest.raises(CandidateGenerationError):
        run(make_generator([candidate]))


def test_unknown_duplicate_reference_fails():
    # 入力に存在しない重複先IDを返した場合は失敗することを確認する。
    generator = make_generator(
        [], [{"source": "rule", "id": "missing", "reason": "same"}]
    )
    with pytest.raises(CandidateGenerationError):
        run(generator)


def test_empty_candidates_and_duplicates_are_normal_result():
    # ルールに該当しない投稿は、候補も重複もない正常結果として返す。
    result = run(make_generator(candidates=[], duplicates=[]))
    assert len(result.posts) == 1
    assert result.posts[0].candidates == []
    assert result.posts[0].duplicates == []
    assert result.stale_candidates == []


@pytest.mark.parametrize("ids", [[], [""], [" "], [None], ["a", "b"]])
def test_invalid_post_ids_fail_before_api(ids):
    # 投稿IDの件数不足・空値・不正な型を、API呼び出し前に拒否することを確認する。
    generator = make_generator()
    with pytest.raises(ValueError, match="post_ids"):
        run(generator, post_ids=ids)
    generator.client.models.generate_content.assert_not_called()


def test_duplicate_post_ids_are_rejected():
    # 同じバッチ内の投稿ID重複を拒否することを確認する。
    with pytest.raises(ValueError, match="unique"):
        run(make_generator(), posts=[POST, POST], post_ids=["p1", "p1"])


def test_stored_post_is_accepted_without_mutating_processing_status():
    # 保存済み投稿を受け付け、元の処理状態を変更せず投稿IDを引き継ぐことを確認する。
    stored = StoredPost(
        **POST.model_dump(),
        status="unprocessed",
        created_at=datetime(2026, 11, 8, tzinfo=timezone.utc),
        status_updated_at=datetime(2026, 11, 8, tzinfo=timezone.utc),
    )
    result = run(make_generator(), posts=[stored], post_ids=["saved_post"])
    assert result.posts[0].candidates[0].post_id == "saved_post"
    assert stored.status == "unprocessed"


def test_gemini_cannot_choose_post_id():
    # Geminiが投稿IDを応答に追加した場合は拒否することを確認する。
    with pytest.raises(CandidateGenerationError, match="Invalid Gemini JSON"):
        run(make_generator([draft(post_id="invented")]))


def test_empty_post_result_does_not_skip_later_posts():
    # 最初の投稿が候補0件でも、次の投稿の候補生成を継続する。
    generator = make_generator()
    generator.client.models.generate_content.side_effect = [
        Mock(text=json.dumps({"candidates": [], "duplicates": []})),
        Mock(text=json.dumps({"candidates": [draft()], "duplicates": []})),
    ]
    result = run(generator, posts=[POST, POST])
    assert [post.post_index for post in result.posts] == [0, 1]
    assert result.posts[0].candidates == []
    assert result.posts[0].duplicates == []
    assert len(result.posts[1].candidates) == 1
    assert result.posts[1].candidates[0].status == "pending"


def test_empty_post_result_still_generates_stale_rule_review():
    # 投稿の候補0件と、更新日からの確認候補生成は独立して処理する。
    rule = RULE.model_copy(
        update={"updated_at": datetime(2020, 1, 1, tzinfo=timezone.utc)}
    )
    result = run(make_generator(candidates=[]), rules=[rule])
    assert result.posts[0].candidates == []
    assert result.posts[0].duplicates == []
    assert len(result.stale_candidates) == 1
    assert result.stale_candidates[0].type == "review"
    assert result.stale_candidates[0].target_rule_id == rule.id
    assert result.stale_candidates[0].review_reason


def test_anniversary_beyond_date_limit_is_skipped():
    # Pythonの日付上限を超える周年でも例外にならず候補を作らない。
    rule = RULE.model_copy(
        update={"updated_at": datetime(9999, 1, 1, tzinfo=timezone.utc)}
    )
    result = run(make_generator(), posts=[], rules=[rule])
    assert result.stale_candidates == []


@pytest.mark.parametrize(
    "updated,reviewed,deadline",
    [
        ("2020-01-01", None, "2023-01-01"),
        ("2020-01-01", "2023-11-08T23:59:00Z", "2026-11-08"),
        ("2023-11-08", "2020-01-01T00:00:00Z", "2026-11-08"),
        ("2020-01-01", "2020-02-29T00:00:00Z", "2023-02-28"),
    ],
)
def test_stale_candidate_uses_latest_date_and_deterministic_id(
    updated, reviewed, deadline
):
    # 更新・確認の新しい日付から期限を決め、同じ入力なら同じCandidateを返す。
    rule = Rule(
        **{
            **RULE.model_dump(),
            "updated_at": updated + "T00:00:00Z",
            "last_reviewed_at": reviewed,
        }
    )
    before = rule.model_dump_json()
    result = run(make_generator(), posts=[], rules=[rule]).stale_candidates[0]
    assert isinstance(result, Candidate)
    assert result.source == "stale_rule"
    assert result.post_id is None
    assert result.type == "review"
    assert result.status == "pending"
    assert result.id == f"stale_r1_{deadline}"
    assert run(make_generator(), posts=[], rules=[rule]).stale_candidates[0] == result
    assert rule.model_dump_json() == before


@pytest.mark.parametrize(
    "today,expected",
    [
        (date(2026, 11, 7), 0),
        (date(2026, 11, 8), 1),
    ],
)
def test_review_time_moves_deadline(today, expected):
    # 確認日時が更新された場合だけ、その日付から3年間再生成しない。
    rule = Rule(
        **{
            **RULE.model_dump(),
            "updated_at": "2020-01-01T00:00:00Z",
            "last_reviewed_at": "2023-11-08T00:00:00Z",
        }
    )
    result = run_candidate_batch(
        [], [rule], [], generator=make_generator(), today=today
    )
    assert len(result.stale_candidates) == expected


def test_duplicate_rules_do_not_generate_duplicate_stale_candidates():
    # 同一バッチで同じルールを複数回受け取っても経年確認は1件にする。
    rule = RULE.model_copy(
        update={"updated_at": datetime(2020, 1, 1, tzinfo=timezone.utc)}
    )
    result = run(make_generator(), posts=[], rules=[rule, rule])
    assert len(result.stale_candidates) == 1


def test_review_time_beyond_anniversary_date_limit_is_skipped():
    # 最終確認日を基準にした場合も9999年を超える周年を作らない。
    rule = Rule(**{**RULE.model_dump(), "last_reviewed_at": "9999-01-01T00:00:00Z"})
    result = run(make_generator(), posts=[], rules=[rule])
    assert result.stale_candidates == []


def test_completed_candidate_alone_does_not_record_rule_review():
    # 採否状態だけでは確認日を推測しない。確認日時の更新は機能Dが担う。
    rule = RULE.model_copy(
        update={"updated_at": datetime(2020, 1, 1, tzinfo=timezone.utc)}
    )
    completed = Candidate(
        id="stale_r1_2023-01-01",
        source="stale_rule",
        type="review",
        status="approved",
        region="sakai",
        statement=STATEMENT,
        target_rule_id="r1",
        review_reason="経年確認",
    )
    result = run(make_generator(), posts=[], rules=[rule], candidates=[completed])
    assert len(result.stale_candidates) == 1
    assert result.stale_candidates[0].id == completed.id


@pytest.mark.parametrize("offset", [0])
@pytest.mark.parametrize(
    "today,expected",
    [
        (date(2026, 11, 6), 0),
        (date(2026, 11, 7), 1),
    ],
)
def test_utc_updated_at_anniversary_boundary(offset, today, expected):
    # UTC日時の暦日で、3年経過日の前日と当日を判定する。
    updated_at = datetime(2023, 11, 7, 18, tzinfo=timezone.utc).astimezone(
        timezone(timedelta(hours=offset))
    )
    payload = {**RULE.model_dump(), "updated_at": updated_at}
    result = run_candidate_batch(
        [], [payload], [], generator=make_generator(), today=today
    )
    assert len(result.stale_candidates) == expected
    assert payload["updated_at"] == updated_at


@pytest.mark.parametrize("hour", [0, 12])
def test_naive_updated_at_datetime_is_rejected(hour):
    # 午前0時も含め、タイムゾーン未定義の日時を暗黙に日付へ変換しない。
    payload = {**RULE.model_dump(), "updated_at": datetime(2023, 11, 7, hour)}
    generator = make_generator()
    with pytest.raises(ValidationError):
        run_candidate_batch([], [payload], [], generator=generator, today=TODAY)
    generator.client.models.generate_content.assert_not_called()


def test_batch_rejects_jst_updated_at():
    # JSTの更新日時を暗黙変換せず拒否し、Geminiも呼ばないことを確認する。
    rule = {
        **RULE.model_dump(),
        "updated_at": "2026-11-09T00:00:00+09:00",
    }
    generator = make_generator()

    with pytest.raises(ValidationError):
        run_candidate_batch(
            posts=[],
            rules=[rule],
            candidates=[],
            generator=generator,
            today=TODAY,
        )

    generator.client.models.generate_content.assert_not_called()


def test_default_today_uses_utc_at_jst_date_boundary():
    # JSTでは翌日になる時刻を固定し、既定の当日がUTCのままであることを確認する。
    rule = RULE.model_copy(
        update={"updated_at": datetime(2023, 11, 8, tzinfo=timezone.utc)}
    )

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            # 実行日時によらず、UTCとJSTの日付が異なる固定時刻を返す。
            assert tz is timezone.utc
            return datetime(2026, 11, 7, 18, tzinfo=timezone.utc)

    with patch("services.candidate_generation.datetime", FixedDatetime):
        result = run_candidate_batch([], [rule], [], generator=make_generator())
    assert result.stale_candidates == []


def test_api_error_is_sanitized():
    # API失敗時の例外表示に、元のエラーの秘密情報を含めないことを確認する。
    generator = make_generator()
    generator.client.models.generate_content.side_effect = RuntimeError("secret")
    with pytest.raises(CandidateGenerationError) as exc:
        run(generator)
    assert "secret" not in str(exc.value)
    assert exc.value.__suppress_context__


def test_input_models_and_containers_are_unchanged():
    # 候補生成後も、入力モデルの値と入力リストの件数が変わらないことを確認する。
    candidate = Candidate(
        id="c1",
        post_id="existing_post",
        region="sakai",
        statement=STATEMENT,
        type="add",
        status="pending",
    )
    posts, rules, candidates = [POST], [RULE], [candidate]
    before = [x.model_dump_json() for x in [POST, RULE, candidate]]
    run(make_generator(), posts=posts, rules=rules, candidates=candidates)
    assert [x.model_dump_json() for x in [POST, RULE, candidate]] == before
    assert (len(posts), len(rules), len(candidates)) == (1, 1, 1)


@pytest.mark.parametrize(
    "payload",
    [
        {"region": "sakai"},
        {"text": 123, "region": "sakai"},
    ],
)
def test_invalid_post_is_rejected_before_api(payload):
    # 必須項目不足や不正な型の投稿を、API呼び出し前に拒否することを確認する。
    generator = make_generator()
    with pytest.raises(ValidationError):
        run(generator, posts=[payload])
    generator.client.models.generate_content.assert_not_called()


@pytest.mark.parametrize(
    "changes",
    [
        {"type": None},
        {"type": "unknown"},
        {"target_rule_id": " "},
        {"type": "review", "review_reason": " "},
        {"type": "update"},
    ],
)
def test_candidate_schema_rejects_invalid_combinations(changes):
    # Candidateの不正な種別や項目の組み合わせを拒否することを確認する。
    with pytest.raises(ValidationError):
        Candidate(
            id="c1",
            post_id="existing_post",
            region="sakai",
            status="pending",
            **{**draft(), **changes},
        )


def test_candidate_type_is_required():
    # Candidateのtypeを省略すると検証エラーになることを確認する。
    with pytest.raises(ValidationError):
        Candidate(
            id="c1",
            post_id="existing_post",
            region="sakai",
            status="pending",
            statement=STATEMENT,
        )


def test_batch_default_date_works_without_timezone_database():
    # 判定日省略時も空バッチが正常終了し、APIを呼ばないことを確認する。
    generator = make_generator()
    result = run_candidate_batch([], [], [], generator=generator)
    assert result.posts == []
    assert result.stale_candidates == []
    generator.client.models.generate_content.assert_not_called()


def test_sdk_serializes_nonempty_string_constraints_without_network():
    # 実SDKで送信直前まで変換し、文字列制約が保持されることを確認する。
    with genai.Client(
        enterprise=True,
        project="test-project",
        location="global",
        credentials=AnonymousCredentials(),
    ) as client:
        with patch.object(client._api_client, "request") as request:
            request.side_effect = RuntimeError("stop before network")
            with pytest.raises(CandidateGenerationError):
                GeminiGenerator(client, "gemini-3.6-flash").generate({})
            request.assert_called_once()
            schema = request.call_args.args[2]["generationConfig"]["responseJsonSchema"]
            assert schema == GeminiOutput.model_json_schema()
            statement = schema["$defs"]["LocalizedStatement"]["properties"]["ja"]
            assert statement["minLength"] == 1
            assert statement["pattern"] == r"\S"


def test_factory_uses_adc_and_explicit_enterprise_settings(monkeypatch):
    # 環境設定とADCを使い、APIキーなしでクライアントを作ることを確認する。
    for key, value in {
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_CLOUD_LOCATION": "global",
        "GEMINI_MODEL": "configured-model",
    }.items():
        monkeypatch.setenv(key, value)
    with (
        patch("services.candidate_generation.load_dotenv"),
        patch("services.candidate_generation.google.auth.default") as auth,
        patch("services.candidate_generation.genai.Client") as client,
    ):
        credentials = Mock()
        auth.return_value = (credentials, "test-project")
        generator = GeminiGenerator.from_env()
        assert generator.model == "configured-model"
        assert client.call_args.kwargs["enterprise"] is True
        assert client.call_args.kwargs["credentials"] is credentials
        assert "api_key" not in client.call_args.kwargs
        generator.close()
        client.return_value.close.assert_called_once()


LOCATION = {"lat": 34.5738, "lng": 135.4795}


@pytest.mark.parametrize("location", [LOCATION, None])
def test_candidate_inherits_location_from_post(location):
    # 位置は Gemini に作らせず、元の Post の値をそのまま Candidate に入れる。
    post = Post(text="夜は騒がないでほしい", region="sakai", location=location)

    candidate = run(make_generator(), posts=[post]).posts[0].candidates[0]

    assert candidate.model_dump()["location"] == location


def test_stale_candidate_inherits_location_from_rule():
    rule = Rule(
        id="r1",
        region="sakai",
        statement=STATEMENT,
        updated_at="2020-01-01T00:00:00Z",
        location=LOCATION,
    )

    result = run(make_generator(), posts=[], rules=[rule]).stale_candidates[0]

    assert result.model_dump()["location"] == LOCATION
