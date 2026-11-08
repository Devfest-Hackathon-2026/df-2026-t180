from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from schemas.common import LocalizedStatement, NonEmptyString


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    region: NonEmptyString
    statement: LocalizedStatement
    status: Literal["pending", "approved", "rejected"]
    type: Literal["add", "update", "review"]
    target_rule_id: str | None = None
    review_reason: str | None = None

    @model_validator(mode="after")
    def validate_candidate_type(self) -> "Candidate":
        if self.target_rule_id is not None and not self.target_rule_id.strip():
            raise ValueError("target_rule_id must not be blank")
        if self.type == "add" and self.target_rule_id is not None:
            raise ValueError("add must not target an existing rule")
        if self.type in ("update", "review") and self.target_rule_id is None:
            raise ValueError(f"{self.type} requires target_rule_id")
        if self.type == "review" and (
            self.review_reason is None or not self.review_reason.strip()
        ):
            raise ValueError("review requires review_reason")
        return self
