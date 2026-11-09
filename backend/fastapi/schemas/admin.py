from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from schemas.candidate import Candidate
from schemas.common import LocalizedStatement, NonEmptyString, UtcDatetime
from schemas.rule import Rule


class Admin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    firebase_uid: NonEmptyString
    employee_name: NonEmptyString


class CandidateDecision(BaseModel):
    """PATCH /api/admin/candidates/{id} の本文。

    approve に statement を付けると「修正して採用」になる。reject には付けられない。

    update・review の approve では、管理画面で表示していた対象ルールの version
    （一覧の current.version）を expected_version に入れる。その後ルールが
    変わっていれば 409。
    add と reject では使わない。
    """

    model_config = ConfigDict(extra="forbid")

    action: Literal["approve", "reject"]
    statement: LocalizedStatement | None = None
    expected_version: NonEmptyString | None = None

    @model_validator(mode="after")
    def validate_statement(self) -> "CandidateDecision":
        if self.action == "reject" and self.statement is not None:
            raise ValueError("reject must not have statement")
        return self


class RuleEdit(BaseModel):
    """PATCH /api/admin/rules/{id} の本文。"""

    model_config = ConfigDict(extra="forbid")

    statement: LocalizedStatement
    # 編集画面で表示していたルールの version。その後ルールが変わっていれば 409。
    expected_version: NonEmptyString


class CandidatePost(BaseModel):
    """候補の元になった住民の投稿。管理画面で採否判断の材料として表示する。"""

    text: NonEmptyString
    reason: NonEmptyString | None = None
    created_at: UtcDatetime


class CandidateTarget(BaseModel):
    """更新・経年確認の対象になっている公開ルールの現在の内容。"""

    statement: LocalizedStatement
    updated_at: UtcDatetime
    last_reviewed_at: UtcDatetime | None = None
    version: NonEmptyString


class AdminRule(Rule):
    """管理画面向けの公開ルール。編集時に送り返す version を添える。"""

    version: NonEmptyString


class AdminCandidate(Candidate):
    """管理画面向けの候補。元の投稿と対象ルールの現在の内容を添える。

    rule_changed_since_generated は、候補の生成時に Gemini が参照したルールの版
    （target_rule_version）と今の版が違うとき True。版が記録されていない候補では False。
    """

    post: CandidatePost | None = None
    current: CandidateTarget | None = None
    rule_changed_since_generated: bool = False


class CandidateDecisionResult(BaseModel):
    """採否の結果。採用で公開ルールが作成・更新された場合は rule に入る。"""

    candidate: Candidate
    rule: AdminRule | None = None
