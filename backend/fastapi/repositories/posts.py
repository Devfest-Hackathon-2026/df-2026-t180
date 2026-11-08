from functools import lru_cache
from typing import Protocol

from google.cloud import firestore

from schemas.post import StoredPost

POSTS_COLLECTION = "posts"


class PostRepository(Protocol):
    def add(self, post: StoredPost) -> str: ...


class FirestorePostRepository:
    def __init__(self, client: firestore.Client) -> None:
        self._collection = client.collection(POSTS_COLLECTION)

    def add(self, post: StoredPost) -> str:
        # ドキュメントIDは Firestore の自動IDを使う
        _, ref = self._collection.add(post.model_dump())
        return ref.id


# クライアントの作成は最初のリクエストまで遅らせる。
# 起動時やテスト時に Google Cloud の認証がなくても動かせるようにするため。
@lru_cache
def get_post_repository() -> PostRepository:
    return FirestorePostRepository(firestore.Client())
