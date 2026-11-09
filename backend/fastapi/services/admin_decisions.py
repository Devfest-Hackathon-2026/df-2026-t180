"""管理者による候補の採否（機能D）。

DB を触らない純粋な関数で、#24 の方針を表す。

- 却下: どの種類でも公開ルールは変更しない
- add の採用: 公開ルールを新規作成（修正して採用なら修正した文で）
- update の採用: 対象ルールの文を置き換え、updated_at を更新
- review の「問題なし」: last_reviewed_at だけ更新（文と updated_at は変えない）
- review の「修正して採用」: 文を置き換え、updated_at を更新
"""

from datetime import datetime

from schemas.admin import CandidateDecision
from schemas.candidate import Candidate
from schemas.common import LocalizedStatement
from schemas.rule import Rule


class DecisionConflict(ValueError):
    """採否を適用できない状態（すでに判断済み、対象ルールが存在しないなど）。"""


def decide_candidate(
    candidate: Candidate,
    target: Rule | None,
    decision: CandidateDecision,
    *,
    now: datetime,
    new_rule_id: str,
) -> tuple[Candidate, Rule | None]:
    """判断後の候補と、作成・更新する公開ルール（なければ None）を返す。

    target には候補の target_rule_id が指すルールを渡す（add のときは None）。
    new_rule_id は add を採用したときの新しい公開ルールのIDに使う。
    """
    if candidate.status != "pending":
        raise DecisionConflict("candidate is already decided")

    if decision.action == "reject":
        return candidate.model_copy(update={"status": "rejected"}), None

    statement = decision.statement or candidate.statement
    # 公開した文を候補にも残し、何が公開されたか後から追えるようにする。
    approved = candidate.model_copy(
        update={"status": "approved", "statement": statement}
    )

    if candidate.type == "add":
        rule = Rule(
            id=new_rule_id,
            region=candidate.region,
            statement=statement,
            updated_at=now,
            location=candidate.location,
        )
        return approved, rule

    if target is None or target.id != candidate.target_rule_id:
        raise DecisionConflict("target rule does not exist")

    if candidate.type == "review" and decision.statement is None:
        # 「問題なし」: 内容は今も正しい。文と updated_at は変えず、確認日だけ進める。
        return approved, target.model_copy(update={"last_reviewed_at": now})

    return approved, target.model_copy(
        update={"statement": statement, "updated_at": now}
    )


def edit_rule(rule: Rule, statement: LocalizedStatement, *, now: datetime) -> Rule:
    """管理者が公開ルールを直接編集する。文を置き換えて updated_at を進める。"""
    return rule.model_copy(update={"statement": statement, "updated_at": now})
