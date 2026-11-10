"""Evaluation infrastructure tests; no live API or Firestore access."""

import json
from copy import deepcopy
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from evaluation.tool import (
    ROOT,
    Expected,
    Judgement,
    Run,
    Scenario,
    automatic,
    execute,
    load_run,
    load_scenarios,
    main,
    report,
    save_run,
    summary,
)
from services.candidate_generation import GeminiGenerator


def test_dataset_has_exactly_ten_unique_schema_valid_scenarios():
    scenarios = load_scenarios()
    assert [s.scenario_id for s in scenarios] == [f"E{i:02}" for i in range(1, 11)]
    responses = json.loads(
        (ROOT / "offline_responses.json").read_text(encoding="utf-8")
    )
    assert set(responses) == {s.scenario_id for s in scenarios}
    for s in scenarios:
        assert Scenario.model_validate_json(s.model_dump_json()) == s
        assert s.post.region.startswith("fictional-")


@pytest.mark.parametrize(
    "change",
    [
        {"candidate_count": [-1]},
        {"candidate_count": [True]},
        {"candidate_count": [2]},
        {"candidate_count": [1, 1]},
        {"unexpected": True},
        {"meanings": []},
    ],
)
def test_invalid_expectations_rejected(change):
    payload = load_scenarios()[0].expected.model_dump()
    with pytest.raises(ValidationError):
        Expected.model_validate({**payload, **change})


def test_dataset_rejects_duplicate_ids_and_unknown_references(tmp_path):
    data = json.loads((ROOT / "scenarios.json").read_text(encoding="utf-8"))
    data[-1] = data[0]
    path = tmp_path / "scenarios.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_scenarios(path)
    payload = load_scenarios()[1].model_dump(mode="json")
    payload["expected"]["candidate_signatures"][0]["target_rule_id"] = "missing"
    with pytest.raises(ValidationError):
        Scenario.model_validate(payload)


def test_offline_all_cases_without_cloud(monkeypatch):
    def forbidden():
        pytest.fail("live factory must not be called offline")

    monkeypatch.setattr("evaluation.tool.GeminiGenerator.from_env", forbidden)
    records = [execute(s) for s in load_scenarios()]
    assert all(r.error_type is None for r in records)
    assert all(j.status != "fail" for r in records for j in r.automatic.values())
    assert all(j.status == "pending" for r in records for j in r.manual.values())
    assert all(not r.actual["stale_candidates"] for r in records)
    assert records[7].automatic["candidate_signatures"].status == "pending"


def test_structural_checks_fail_without_semantic_string_matching():
    s = load_scenarios()[0]
    actual = execute(s).actual
    actual["posts"][0]["candidates"][0]["statement"] = {
        "ja": "無関係な文章",
        "en": "An unrelated sentence.",
    }
    # Content is deliberately wrong: schema success is not semantic success.
    assert all(x.status == "pass" for x in automatic(s, actual).values())
    bad = deepcopy(actual)
    bad["posts"][0]["candidates"][0]["statement"]["en"] = " "
    assert automatic(s, bad)["schema"].status == "fail"
    bad = deepcopy(actual)
    bad["posts"][0]["candidates"][0]["unexpected"] = True
    assert automatic(s, bad)["schema"].status == "fail"
    bad = deepcopy(actual)
    bad["posts"][0]["candidates"] = []
    assert automatic(s, bad)["candidate_count"].status == "fail"
    bad = deepcopy(actual)
    bad["posts"][0]["post_index"] = "0"
    assert automatic(s, bad)["schema"].status == "fail"


def test_live_cli_uses_existing_generator_isolates_cases_and_checkpoints(
    tmp_path, monkeypatch
):
    responses = json.loads(
        (ROOT / "offline_responses.json").read_text(encoding="utf-8")
    )
    clients = []
    output = tmp_path / "live-mocked.json"

    def factory():
        index = len(clients)
        if index:
            # The previous completed case is already durable before the next call.
            assert len(load_run(output).records) == index
        client = Mock()
        clients.append(client)
        if index == 0:
            client.models.generate_content.side_effect = RuntimeError("private")
        else:
            client.models.generate_content.return_value.text = json.dumps(
                responses["E06"]
            )
        return GeminiGenerator(client, "mocked-sdk-never-network")

    monkeypatch.setattr("evaluation.tool.GeminiGenerator.from_env", factory)
    main(
        [
            "run",
            "--live",
            "--ids",
            "E01",
            "E06",
            "--limit",
            "2",
            "--output",
            str(output),
        ]
    )
    run = load_run(output)
    assert run.records[0].error_type == "CandidateGenerationError"
    assert run.records[1].error_type is None
    assert len(run.records[1].actual["posts"][0]["candidates"]) == 2
    for client in clients:
        payload = json.loads(
            client.models.generate_content.call_args.kwargs["contents"]
        )
        assert payload["candidates"] == []
        assert payload["rules"] == []
        client.close.assert_called_once()
    assert "private" not in output.read_text(encoding="utf-8")


def test_atomic_save_failure_leaves_previous_run_intact(tmp_path, monkeypatch):
    path = tmp_path / "run.json"
    run = Run(records=[execute(load_scenarios()[0])])
    save_run(path, run)
    before = path.read_bytes()

    def unavailable(*args):
        raise OSError("replacement unavailable")

    monkeypatch.setattr("evaluation.tool.os.replace", unavailable)
    run.records.append(execute(load_scenarios()[1]))
    with pytest.raises(OSError):
        save_run(path, run)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


def test_reference_integrity_separate_from_expected_target():
    s = load_scenarios()[1]
    payload = s.model_dump(mode="json")
    other = deepcopy(payload["rules"][0])
    other["id"] = "other-valid-rule"
    payload["rules"].append(other)
    s = Scenario.model_validate(payload)
    actual = execute(s).actual
    actual["posts"][0]["candidates"][0]["target_rule_id"] = "other-valid-rule"
    checks = automatic(s, actual)
    assert checks["references"].status == "pass"
    assert checks["candidate_signatures"].status == "fail"
    actual["posts"][0]["candidates"][0]["target_rule_id"] = "missing"
    assert automatic(s, actual)["references"].status == "fail"


def test_duplicates_and_multiple_candidates_are_order_independent():
    s = load_scenarios()[5]
    actual = execute(s).actual
    actual["posts"][0]["candidates"].reverse()
    assert automatic(s, actual)["candidate_signatures"].status == "pass"
    s = load_scenarios()[3]
    actual = execute(s).actual
    actual["posts"][0]["duplicates"][0]["id"] = "wrong"
    checks = automatic(s, actual)
    assert checks["duplicates"].status == checks["references"].status == "fail"


def test_save_reload_review_report_and_escape(tmp_path):
    record = execute(load_scenarios()[0])
    path = tmp_path / "run.json"
    save_run(path, Run(records=[record]))
    main(
        [
            "review",
            str(path),
            "E01",
            "meaning",
            "fail",
            "--comment",
            "<script>x</script>",
        ]
    )
    restored = load_run(path)
    assert restored.records[0].manual["meaning"].status == "fail"
    assert restored.records[0].manual["meaning"].comment == "<script>x</script>"
    assert restored.records[0].manual["english"].status == "pending"
    target = tmp_path / "report.html"
    report(restored, target)
    page = target.read_text(encoding="utf-8")
    assert "&lt;script&gt;" in page and "<script>" not in page
    assert "青葉桟橋" in page and "期待結果" in page and "生成結果" in page
    with pytest.raises(SystemExit):
        main(["review", str(path), "E01", "injection", "pass"])
    assert load_run(path) == restored


def test_pending_excluded_from_numerator_and_inapplicable_from_denominator():
    record = execute(load_scenarios()[6])
    record.manual["classification"] = Judgement(status="pass")
    result = summary(Run(records=[record]))["offline"]
    assert result["quality_evidence"] is False
    assert result["manual"]["denominator"] == 3
    assert result["manual"]["pass"] == 1
    assert result["manual"]["pending"] == 2
    assert result["manual"]["pass_rate"] == 1 / 3
    assert result["by_scenario"]["E07"]["manual"] == "pending"
    assert "english" not in result["by_criterion"]["manual"]


def test_api_error_recorded_and_other_cases_preserved(tmp_path):
    broken = Mock(model="fake-live-model")
    broken.generate.side_effect = RuntimeError("secret credentials")
    failed = execute(load_scenarios()[0], mode="live", factory=lambda: broken)
    success = execute(load_scenarios()[1])
    run = Run(records=[failed, success])
    path = tmp_path / "run.json"
    save_run(path, run)
    assert "secret credentials" not in path.read_text(encoding="utf-8")
    assert failed.error_type == "RuntimeError"
    assert failed.automatic["execution"].status == "fail"
    assert failed.automatic["schema"].status == "pending"
    broken.close.assert_called_once()
    result = summary(load_run(path))
    assert result["live"]["execution_failure"] == 1
    assert result["live"]["execution_success"] == 0
    assert result["offline"]["scenarios"] == 1


def test_factory_error_recorded_and_cli_limits_without_live_calls(
    tmp_path, monkeypatch
):
    def broken():
        raise RuntimeError("ADC unavailable")

    record = execute(load_scenarios()[0], mode="live", factory=broken)
    assert record.error_type == "RuntimeError"
    monkeypatch.setattr("evaluation.tool.GeminiGenerator.from_env", broken)
    path = tmp_path / "run.json"
    main(["run", "--ids", "E01", "E06", "--limit", "1", "--output", str(path)])
    assert [r.scenario_id for r in load_run(path).records] == ["E01"]
    before = path.read_bytes()
    with pytest.raises(SystemExit):
        main(["run", "--output", str(path)])
    assert path.read_bytes() == before
    for flags in (["--limit", "0"], ["--ids", "E99"], ["--ids", "E01", "E01"]):
        with pytest.raises(SystemExit):
            main(["run", *flags, "--output", str(tmp_path / "unused.json")])
