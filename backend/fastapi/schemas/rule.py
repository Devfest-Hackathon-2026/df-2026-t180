from pydantic import BaseModel, ConfigDict

from schemas.common import LocalizedStatement, Location, NonEmptyString, UtcDatetime


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    region: NonEmptyString
    statement: LocalizedStatement
    updated_at: UtcDatetime
    last_reviewed_at: UtcDatetime | None = None
    location: Location | None = None
