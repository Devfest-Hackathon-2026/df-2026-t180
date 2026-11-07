from pydantic import BaseModel, ConfigDict

from schemas.common import NonEmptyString


class Post(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: NonEmptyString
    region: NonEmptyString
    reason: str | None = None
