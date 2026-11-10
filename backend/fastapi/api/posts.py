from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, status

from repositories.posts import PostRepository, get_post_repository
from schemas.post import Post, PostCreated, new_stored_post

router = APIRouter()


@router.post("/api/posts", status_code=status.HTTP_201_CREATED)
def create_post(
    post: Post,
    repository: Annotated[PostRepository, Depends(get_post_repository)],
) -> PostCreated:
    stored = new_stored_post(post, datetime.now(timezone.utc))
    return PostCreated(id=repository.add(stored))
