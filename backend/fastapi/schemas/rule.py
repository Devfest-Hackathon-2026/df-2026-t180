from pydantic import BaseModel, ConfigDict

from schemas.common import LocalizedStatement, NonEmptyString, UtcDatetime


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    region: NonEmptyString
    statement: LocalizedStatement
    updated_at: UtcDatetime
    last_reviewed_at: UtcDatetime | None = None
