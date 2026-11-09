from pydantic import BaseModel, ConfigDict

from schemas.common import LocalizedStatement, NonEmptyString


class Region(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    name: LocalizedStatement
