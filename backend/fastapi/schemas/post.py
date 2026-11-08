from typing import Literal

from pydantic import BaseModel, ConfigDict

from schemas.common import NonEmptyString, UtcDatetime


class Post(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: NonEmptyString
    region: NonEmptyString
    reason: str | None = None


class StoredPost(Post):
    status: Literal["unprocessed", "processing", "processed"]
    status_updated_at: UtcDatetime
    created_at: UtcDatetime
