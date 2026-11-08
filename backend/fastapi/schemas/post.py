from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from schemas.common import NonEmptyString, UtcDatetime


class Post(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: NonEmptyString
    region: NonEmptyString
    reason: NonEmptyString | None = None


class StoredPost(Post):
    status: Literal["unprocessed", "processing", "processed"]
    status_updated_at: UtcDatetime
    created_at: UtcDatetime


class PostCreated(BaseModel):
    id: NonEmptyString


def new_stored_post(post: Post, now: datetime) -> StoredPost:
    return StoredPost(
        **post.model_dump(),
        status="unprocessed",
        status_updated_at=now,
        created_at=now,
    )
