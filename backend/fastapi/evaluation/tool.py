"""Independent evaluation runs; never reads or writes Firestore."""

import argparse
import hashlib
import html
import json
import os
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.candidate import Candidate
from schemas.common import NonEmptyString
from schemas.post import Post
from schemas.rule import Rule
from services.candidate_generation import (
    SYSTEM_INSTRUCTION,
    BatchResult,
    GeminiGenerator,
    GeminiOutput,
    run_candidate_batch,
)

ROOT = Path(__file__).parent
TODAY = date(2026, 11, 10)
Status = Literal["pass", "fail", "pending"]
CRITERIA = {
    "meaning": "日本語の意味・場所・時間・条件の保持",
    "japanese": "日本語表現の自然さ・丁寧さ",
    "english": "英語翻訳の正確性・条件保持",
    "classification": "種別分類の意味的妥当性",
    "duplication": "既存Rule・Candidateとの意味的な重複判断",
    "contradiction": "矛盾の検出・一方を断定しないこと",
    "splitting": "複数内容の分割・候補と意味の対応（順不同）",
    "unnecessary": "不要な候補がないこと",
    "hallucination": "原文にない事実・断定・条件の追加がないこと",
    "injection": "投稿内のAIへの不正な指示を無視すること",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Signature(StrictModel):
    type: Literal["add", "update", "review"]
    target_rule_id: NonEmptyString | None

    @model_validator(mode="after")
    def valid_target(self):
        if (self.type == "add") != (self.target_rule_id is None):
            raise ValueError("signature target does not match type")
        return self


class DuplicateTarget(StrictModel):
    source: Literal["rule", "candidate"]
    id: NonEmptyString


class Expected(StrictModel):
    candidate_count: list[int] = Field(min_length=1)
    candidate_signatures: list[Signature] | None
    duplicates: list[DuplicateTarget]
    meanings: list[NonEmptyString] = Field(min_length=1)
    conditions: list[NonEmptyString]
    forbidden: list[NonEmptyString] = Field(min_length=1)
    no_candidate_reason: NonEmptyString | None
    allowed_patterns: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_counts(self):
        if any(n < 0 for n in self.candidate_count):
            raise ValueError("negative candidate count")
        if len(set(self.candidate_count)) != len(self.candidate_count):
            raise ValueError("duplicate counts")
        if self.candidate_signatures is not None and self.candidate_count != [
            len(self.candidate_signatures)
        ]:
            raise ValueError("signatures require one exact count")
        if 0 in self.candidate_count and self.no_candidate_reason is None:
            raise ValueError("zero candidates requires explanation")
        return self


class Scenario(StrictModel):
    scenario_id: NonEmptyString = Field(pattern=r"^E\d{2}$")
    title: NonEmptyString
    description: NonEmptyString
    post: Post
    rules: list[Rule]
    candidates: list[Candidate]
    expected: Expected
    evaluation_criteria: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def consistent(self):
        if len(set(self.evaluation_criteria)) != len(self.evaluation_criteria):
            raise ValueError("duplicate criteria")
        if set(self.evaluation_criteria) - CRITERIA.keys():
            raise ValueError("unknown manual criterion")
        rules = {r.id: r for r in self.rules}
        candidates = {c.id: c for c in self.candidates}
        if len(rules) != len(self.rules) or len(candidates) != len(self.candidates):
            raise ValueError("duplicate input IDs")
        for item in [*self.rules, *self.candidates]:
            if item.region != self.post.region:
                raise ValueError("scenario region mismatch")
        for sig in self.expected.candidate_signatures or []:
            if sig.target_rule_id is not None and sig.target_rule_id not in rules:
                raise ValueError("unknown expected rule")
        for dup in self.expected.duplicates:
            targets = rules if dup.source == "rule" else candidates
            if dup.id not in targets or (
                dup.source == "candidate" and targets[dup.id].status == "rejected"
            ):
                raise ValueError("unknown expected duplicate")
        return self


class Judgement(StrictModel):
    status: Status = "pending"
    comment: str = ""


class Record(StrictModel):
    scenario_id: str
    mode: Literal["offline", "live"]
    started_at: str
    model: str
    prompt_hash: str
    input_hash: str
    today: str
    scenario: Scenario
    actual: dict | None = None
    elapsed_seconds: float = 0.0
    error_type: str | None = None
    automatic: dict[str, Judgement] = Field(default_factory=dict)
    manual: dict[str, Judgement]

    @model_validator(mode="after")
    def valid_record(self):
        if self.scenario_id != self.scenario.scenario_id:
            raise ValueError("record/scenario ID mismatch")
        if set(self.manual) != set(self.scenario.evaluation_criteria):
            raise ValueError("manual criteria must match scenario")
        return self


class Run(StrictModel):
    format_version: Literal[1] = 1
    records: list[Record]

    @model_validator(mode="after")
    def unique_records(self):
        ids = [r.scenario_id for r in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate run scenario IDs")
        return self


def load_scenarios(path=ROOT / "scenarios.json") -> list[Scenario]:
    scenarios = [
        Scenario.model_validate(x)
        for x in json.loads(Path(path).read_text(encoding="utf-8"))
    ]
    if len(scenarios) != 10 or {s.scenario_id for s in scenarios} != {
        f"E{i:02}" for i in range(1, 11)
    }:
        raise ValueError("exactly E01 through E10 are required")
    return scenarios


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def automatic(scenario: Scenario, actual: dict | None, error_type=None):
    names = [
        "execution",
        "schema",
        "references",
        "backend_fields",
        "candidate_count",
        "candidate_signatures",
        "duplicates",
    ]
    checks = {
        name: Judgement(comment="実行または構造エラーのため判定不能") for name in names
    }
    checks["execution"] = Judgement(status="fail" if error_type else "pass")
    if error_type:
        return checks
    try:
        result = BatchResult.model_validate(actual, strict=True)
        if set(actual) != {"posts", "stale_candidates"}:
            raise ValueError("unexpected batch fields")
        if len(result.posts) != 1:
            raise ValueError("expected one post result")
        post = result.posts[0]
        if set(actual["posts"][0]) != {
            "post_index",
            "post_id",
            "candidates",
            "duplicates",
        }:
            raise ValueError("unexpected post fields")
    except (ValueError, TypeError):
        checks["schema"] = Judgement(status="fail", comment="出力構造が不正")
        return checks
    checks["schema"] = Judgement(status="pass")
    rule_ids = {r.id for r in scenario.rules if r.region == scenario.post.region}
    candidate_ids = {
        c.id
        for c in scenario.candidates
        if c.region == scenario.post.region and c.status != "rejected"
    }
    refs = all(
        c.target_rule_id is None or c.target_rule_id in rule_ids
        for c in post.candidates
    ) and all(
        d.id in (rule_ids if d.source == "rule" else candidate_ids)
        for d in post.duplicates
    )
    checks["references"] = Judgement(
        status="pass" if refs else "fail",
        comment="入力内参照の整合性。意味的妥当性とは別",
    )
    post_id = f"eval-{scenario.scenario_id}"
    backend = (
        post.post_id == post_id
        and post.post_index == 0
        and not result.stale_candidates
        and all(
            c.post_id == post_id
            and c.source == "post"
            and c.region == scenario.post.region
            and c.status == "pending"
            and c.id == f"{post_id}_{i}"
            for i, c in enumerate(post.candidates, 1)
        )
    )
    checks["backend_fields"] = Judgement(status="pass" if backend else "fail")
    checks["candidate_count"] = Judgement(
        status="pass"
        if len(post.candidates) in scenario.expected.candidate_count
        else "fail",
        comment=f"実測 {len(post.candidates)}件",
    )
    signatures = scenario.expected.candidate_signatures
    if signatures is None:
        checks["candidate_signatures"] = Judgement(comment="分類が一意でないため目視")
    else:
        same = Counter((c.type, c.target_rule_id) for c in post.candidates) == Counter(
            (s.type, s.target_rule_id) for s in signatures
        )
        checks["candidate_signatures"] = Judgement(
            status="pass" if same else "fail",
            comment="種別・対象IDの多重集合で順不同比較。意味の対応は目視",
        )
    same = Counter((d.source, d.id) for d in post.duplicates) == Counter(
        (d.source, d.id) for d in scenario.expected.duplicates
    )
    checks["duplicates"] = Judgement(status="pass" if same else "fail")
    return checks


class OfflineGenerator:
    model = "offline-fixture-not-gemini"

    def __init__(self, response):
        self.response = response

    def generate(self, payload):
        return GeminiOutput.model_validate(self.response)

    def close(self):
        pass


def execute(scenario, mode="offline", factory=None):
    started = perf_counter()
    record = Record(
        scenario_id=scenario.scenario_id,
        mode=mode,
        started_at=datetime.now(timezone.utc).isoformat(),
        model="unavailable",
        prompt_hash=digest(SYSTEM_INSTRUCTION),
        input_hash=digest(scenario.model_dump(mode="json")),
        today=TODAY.isoformat(),
        scenario=scenario,
        manual={k: Judgement() for k in scenario.evaluation_criteria},
    )
    generator = None
    try:
        if factory is not None:
            generator = factory()
        elif mode == "live":
            generator = GeminiGenerator.from_env()
        else:
            responses = json.loads(
                (ROOT / "offline_responses.json").read_text(encoding="utf-8")
            )
            generator = OfflineGenerator(responses[scenario.scenario_id])
        record.model = generator.model
        result = run_candidate_batch(
            [scenario.post],
            scenario.rules,
            scenario.candidates,
            generator=generator,
            post_ids=[f"eval-{scenario.scenario_id}"],
            today=TODAY,
        )
        record.actual = result.model_dump(mode="json")
    except Exception as error:
        # Do not persist provider error messages, credentials or raw exception text.
        record.error_type = type(error).__name__
    finally:
        if generator is not None:
            try:
                generator.close()
            except Exception as error:
                record.error_type = record.error_type or type(error).__name__
    record.elapsed_seconds = perf_counter() - started
    record.automatic = automatic(scenario, record.actual, record.error_type)
    return record


def save_run(path, run):
    """Replace atomically so a failed write cannot truncate prior records."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(run.model_dump_json(indent=2))
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def load_run(path):
    return Run.model_validate_json(Path(path).read_text(encoding="utf-8"))


def counts(judgements):
    result = dict.fromkeys(["pass", "fail", "pending"], 0)
    for judgement in judgements:
        result[judgement.status] += 1
    denominator = sum(result.values())
    return {
        **result,
        "denominator": denominator,
        "pass_rate": result["pass"] / denominator if denominator else None,
    }


def overall(judgements):
    statuses = [j.status for j in judgements]
    if "fail" in statuses:
        return "fail"
    if not statuses or "pending" in statuses:
        return "pending"
    return "pass"


def summary(run):
    groups = {}
    for mode in ("offline", "live"):
        records = [r for r in run.records if r.mode == mode]
        if not records:
            continue
        groups[mode] = {
            "quality_evidence": mode == "live",
            "scenarios": len(records),
            "execution_success": sum(r.error_type is None for r in records),
            "execution_failure": sum(r.error_type is not None for r in records),
            "automatic": counts(j for r in records for j in r.automatic.values()),
            "manual": counts(j for r in records for j in r.manual.values()),
            "scenario_status_counts": {
                kind: counts(
                    Judgement(status=overall(getattr(r, kind).values()))
                    for r in records
                )
                for kind in ("automatic", "manual")
            },
            "by_scenario": {
                r.scenario_id: {
                    "execution": "fail" if r.error_type else "pass",
                    "automatic": overall(r.automatic.values()),
                    "manual": overall(r.manual.values()),
                }
                for r in records
            },
            "by_criterion": {
                kind: {
                    key: counts(
                        getattr(r, kind)[key]
                        for r in records
                        if key in getattr(r, kind)
                    )
                    for key in sorted({k for r in records for k in getattr(r, kind)})
                }
                for kind in ("automatic", "manual")
            },
        }
    return groups


def report(run, path):
    def pre(value):
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")
        return (
            "<pre>"
            + html.escape(json.dumps(value, ensure_ascii=False, indent=2))
            + "</pre>"
        )

    sections = []
    for r in run.records:
        s = r.scenario
        manual = "".join(
            "<li>"
            + html.escape(f"{k}: {CRITERIA[k]} — {v.status} {v.comment}")
            + "</li>"
            for k, v in r.manual.items()
        )
        sections.append(
            f"<section id='{s.scenario_id}'>"
            f"<h2>{html.escape(s.scenario_id + ' ' + s.title)}</h2>"
            f"<p>{html.escape(s.description)} / {r.mode}</p><div class='compare'>"
            "<article><h3>入力</h3>"
            + pre(
                {
                    "post": s.post.model_dump(mode="json"),
                    "rules": [x.model_dump(mode="json") for x in s.rules],
                    "candidates": [x.model_dump(mode="json") for x in s.candidates],
                }
            )
            + "</article><article><h3>期待結果（文章完全一致不要）</h3>"
            + pre(s.expected)
            + "</article><article><h3>生成結果</h3>"
            + pre({"actual": r.actual, "error_type": r.error_type})
            + "</article></div><h3>自動判定</h3>"
            + pre({k: v.model_dump() for k, v in r.automatic.items()})
            + "<h3>目視判定（CLIのreviewで保存）</h3><ul>"
            + manual
            + "</ul>"
            + "<p>同じ種別・対象IDの複数候補は、意味の対応を目視してください。</p>"
            + "</section>"
        )
    totals = summary(run)
    overview = "<table><tr><th>モード</th><th>ケース</th><th>実行成功/失敗</th>"
    overview += "<th>自動 pass/fail/pending</th><th>目視 pass/fail/pending</th></tr>"
    for mode, group in totals.items():
        overview += (
            f"<tr><td>{mode}</td><td>{group['scenarios']}</td>"
            f"<td>{group['execution_success']}/{group['execution_failure']}</td>"
        )
        for kind in ("automatic", "manual"):
            c = group[kind]
            overview += f"<td>{c['pass']}/{c['fail']}/{c['pending']}</td>"
        overview += "</tr>"
    overview += (
        "</table><nav>"
        + " | ".join(
            f"<a href='#{r.scenario_id}'>{r.scenario_id}</a>" for r in run.records
        )
        + "</nav>"
    )
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        "<!doctype html><html lang='ja'><meta charset='utf-8'>"
        "<title>Gemini候補品質評価</title><style>"
        "body{font-family:system-ui;margin:24px}section{border-top:2px solid #999}"
        ".compare{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f3f3;padding:12px}"
        "td,th{border:1px solid #aaa;padding:8px}table{border-collapse:collapse}"
        "nav{padding:16px 0}"
        "@media(max-width:900px){.compare{grid-template-columns:1fr}}"
        "</style><h1>Gemini候補品質評価</h1>"
        "<p>offlineは動作検証用でありGeminiの精度を示しません。pendingは未評価です。"
        "HTMLは閲覧用です。CLIで判定保存後、reportを再実行してください。</p>"
        + overview
        + "<details><summary>ケース別・項目別の詳細集計</summary>"
        + pre(totals)
        + "</details>"
        + "".join(sections)
        + "</html>",
        encoding="utf-8",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("run")
    start.add_argument("--live", action="store_true", help="実Geminiを呼ぶ明示指定")
    start.add_argument("--ids", nargs="+", help="例: E01 E02")
    start.add_argument("--limit", type=int, default=10)
    start.add_argument("--output", type=Path, required=True)
    for command in ("summary", "report", "review"):
        sub = commands.add_parser(command)
        sub.add_argument("result", type=Path)
        if command == "report":
            sub.add_argument("--output", type=Path, required=True)
        if command == "review":
            sub.add_argument("scenario_id")
            sub.add_argument("criterion", choices=sorted(CRITERIA))
            sub.add_argument("status", choices=["pass", "fail", "pending"])
            sub.add_argument("--comment", default="")
    args = parser.parse_args(argv)
    if args.command == "run":
        if not 1 <= args.limit <= 10:
            parser.error("--limit must be between 1 and 10")
        scenarios = load_scenarios()
        if args.ids:
            if len(set(args.ids)) != len(args.ids) or set(args.ids) - {
                s.scenario_id for s in scenarios
            }:
                parser.error("unknown or duplicate scenario ID")
            scenarios = [s for s in scenarios if s.scenario_id in args.ids]
        if args.output.exists():
            parser.error("output exists; choose a new run filename")
        run = Run(records=[])
        for scenario in scenarios[: args.limit]:
            run.records.append(execute(scenario, "live" if args.live else "offline"))
            save_run(args.output, run)
        print(json.dumps(summary(run), ensure_ascii=False, indent=2))
    else:
        run = load_run(args.result)
        if args.command == "review":
            record = next(
                (r for r in run.records if r.scenario_id == args.scenario_id), None
            )
            if record is None or args.criterion not in record.manual:
                parser.error("scenario or applicable criterion not found")
            record.manual[args.criterion] = Judgement(
                status=args.status, comment=args.comment
            )
            save_run(args.result, run)
        elif args.command == "report":
            if args.output.resolve() == args.result.resolve():
                parser.error("report must not overwrite result JSON")
            report(run, args.output)
        else:
            print(json.dumps(summary(run), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
