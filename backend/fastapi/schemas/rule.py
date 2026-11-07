from datetime import date

from pydantic import BaseModel, ConfigDict

from schemas.common import LocalizedStatement, NonEmptyString


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    region: NonEmptyString
    statement: LocalizedStatement
    updated_at: date
