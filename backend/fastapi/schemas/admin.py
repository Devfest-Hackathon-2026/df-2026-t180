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
    """

    model_config = ConfigDict(extra="forbid")

    action: Literal["approve", "reject"]
    statement: LocalizedStatement | None = None

    @model_validator(mode="after")
    def validate_statement(self) -> "CandidateDecision":
        if self.action == "reject" and self.statement is not None:
            raise ValueError("reject must not have statement")
        return self


class RuleEdit(BaseModel):
    """PATCH /api/admin/rules/{id} の本文。"""

    model_config = ConfigDict(extra="forbid")

    statement: LocalizedStatement


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


class AdminCandidate(Candidate):
    """管理画面向けの候補。元の投稿と対象ルールの現在の内容を添える。"""

    post: CandidatePost | None = None
    current: CandidateTarget | None = None


class CandidateDecisionResult(BaseModel):
    """採否の結果。採用で公開ルールが作成・更新された場合は rule に入る。"""

    candidate: Candidate
    rule: Rule | None = None
