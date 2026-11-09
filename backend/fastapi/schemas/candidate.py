from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from schemas.common import LocalizedStatement, Location, NonEmptyString


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    source: Literal["post", "stale_rule"] = "post"
    post_id: NonEmptyString | None = None
    region: NonEmptyString
    statement: LocalizedStatement
    status: Literal["pending", "approved", "rejected"]
    type: Literal["add", "update", "review"]
    target_rule_id: NonEmptyString | None = None
    review_reason: NonEmptyString | None = None
    location: Location | None = None
    # 管理者が実際に公開・確認した文（機能D が採用時に入れる）。statement は Gemini の
    # 提案文のまま残す。却下・未判断では None。
    decided_statement: LocalizedStatement | None = None
    # 候補を作るときに Gemini が参照した対象ルールの版（機能B が入れる。#39）。
    # 機能D はこれが今の版と違えば「生成後にルールが変更されています」と表示する。
    target_rule_version: NonEmptyString | None = None

    @model_validator(mode="after")
    def validate_candidate_type(self) -> "Candidate":
        if self.source == "post" and self.post_id is None:
            raise ValueError("post source requires post_id")
        if self.source == "stale_rule":
            if self.post_id is not None:
                raise ValueError("stale_rule source must not have post_id")
            if self.type != "review":
                raise ValueError("stale_rule source requires review type")
        if self.type == "add" and self.target_rule_id is not None:
            raise ValueError("add must not target an existing rule")
        if self.type == "add" and self.target_rule_version is not None:
            raise ValueError("add must not have target_rule_version")
        if self.type in ("update", "review") and self.target_rule_id is None:
            raise ValueError(f"{self.type} requires target_rule_id")
        if self.type == "review" and self.review_reason is None:
            raise ValueError("review requires review_reason")
        return self
