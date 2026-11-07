from typing import Literal

from pydantic import BaseModel, ConfigDict

from schemas.common import LocalizedStatement, NonEmptyString


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    region: NonEmptyString
    statement: LocalizedStatement
    status: Literal["pending", "approved", "rejected"]
