"""管理者による候補の採否と公開ルールの編集（機能D）。

DB を触らない純粋な関数で、#24 の方針を表す。

採否:

- 却下: どの種類でも公開ルールは変更しない。対象ルールが削除済みでも却下はできる
  （不要になった候補を片付けられるようにするため）
- add の採用: 公開ルールを新規作成（修正して採用なら修正した文で）
- update の採用: 対象ルールの文を置き換え、updated_at を更新
- review の「問題なし」: last_reviewed_at だけ更新（文と updated_at は変えない）
- review の「修正して採用」: 文を置き換え、updated_at と last_reviewed_at を更新

review は経年確認（source=stale_rule）と投稿との矛盾（source=post）の 2 種類があるが、
管理者が判断するのはどちらも「対象ルールの今の文は正しいか」なので、同じ 3 つの操作を
使う。何を確認すべきかは review_reason（と投稿由来なら元の投稿）を画面に出して伝える。

日時の役割:

- updated_at: 公開ルールの文が最後に変わった日時（利用者向けの「更新日」）
- last_reviewed_at: 管理者が最後に内容を確認した日時。review の採用で更新する
- 機能B の経年確認は、この 2 つのうち新しい方から年数を数える

候補の statement（Gemini の提案文）は採否で書き換えない。実際に公開・確認した文は
decided_statement に入れる。review の「問題なし」では確認した対象ルールの文、
「修正して採用」では修正後の文、add・update の採用では公開した文。却下では入れない。
提案と結果を別々に残し、Gemini の提案が後から追えるようにするため。

古い画面からの上書きを防ぐため、既存ルールを書き換える操作（update・review の採用、
直接編集）では、画面で表示していたルールの version を受け取り、今の version と
一致しなければ DecisionConflict にする。version はルールの保存内容から計算するので、
共通のスキーマや他機能の保存処理を変えずに使える。管理者の書き込みは必ず updated_at か
last_reviewed_at を進めるため、どの書き込みでも version は変わる。
"""

from datetime import datetime

from schemas.admin import CandidateDecision, RuleEdit
from schemas.candidate import Candidate
from schemas.rule import Rule
from services.rule_versions import rule_version


class DecisionConflict(ValueError):
    """今の状態では適用できない（判断済み、対象ルールが存在しない・変更済みなど）。409。"""


class DecisionInvalid(ValueError):
    """リクエストの内容が足りない（expected_version がないなど）。422。"""


def _check_version(rule: Rule, expected_version: str | None) -> None:
    if expected_version is None:
        raise DecisionInvalid("expected_version is required")
    if rule_version(rule) != expected_version:
        raise DecisionConflict("rule has changed since it was loaded")


def decide_candidate(
    candidate: Candidate,
    target: Rule | None,
    decision: CandidateDecision,
    *,
    now: datetime,
    new_rule_id: str,
) -> tuple[Candidate, Rule | None]:
    """判断後の候補と、作成・更新する公開ルール（なければ None）を返す。

    target には候補の target_rule_id が指すルールを渡す（add のとき・存在しないときは
    None）。new_rule_id は add を採用したときの新しい公開ルールのIDに使う。
    """
    if candidate.status != "pending":
        raise DecisionConflict("candidate is already decided")

    if decision.action == "reject":
        return candidate.model_copy(update={"status": "rejected"}), None

    if candidate.type == "add":
        statement = decision.statement or candidate.statement
        rule = Rule(
            id=new_rule_id,
            region=candidate.region,
            statement=statement,
            updated_at=now,
        )
        return _approved(candidate, rule), rule

    if target is None or target.id != candidate.target_rule_id:
        raise DecisionConflict("target rule does not exist")
    if target.region != candidate.region:
        # 保存データの不整合で、別の地域のルールを書き換えないようにする。
        raise DecisionConflict("target rule is in a different region")
    _check_version(target, decision.expected_version)

    if candidate.type == "review":
        if decision.statement is None:
            # 「問題なし」: 内容は今も正しい。文と updated_at は変えず確認日だけ進める。
            rule = target.model_copy(update={"last_reviewed_at": now})
        else:
            # 「修正して採用」: 内容を確認したうえで直したので、確認日も進める。
            rule = target.model_copy(
                update={
                    "statement": decision.statement,
                    "updated_at": now,
                    "last_reviewed_at": now,
                }
            )
        return _approved(candidate, rule), rule

    rule = target.model_copy(
        update={
            "statement": decision.statement or candidate.statement,
            "updated_at": now,
        }
    )
    return _approved(candidate, rule), rule


def _approved(candidate: Candidate, rule: Rule) -> Candidate:
    # 提案文（statement）はそのまま、公開・確認した文を decided_statement に残す。
    return candidate.model_copy(
        update={"status": "approved", "decided_statement": rule.statement}
    )


def edit_rule(rule: Rule, edit: RuleEdit, *, now: datetime) -> Rule:
    """管理者が公開ルールを直接編集する。文を置き換えて updated_at を進める。"""
    _check_version(rule, edit.expected_version)
    return rule.model_copy(update={"statement": edit.statement, "updated_at": now})
