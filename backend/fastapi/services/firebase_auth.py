"""Firebase ID トークンの検証。管理者 API の認証に使う。

firebase-admin は使わず、すでに依存に含まれる google-auth で検証する。
"""

import os
from functools import lru_cache
from typing import Protocol

from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


class InvalidToken(ValueError):
    """トークンが無効・期限切れ・別プロジェクト向けなど。理由は外に出さない。"""


class AuthNotConfigured(RuntimeError):
    """検証に使う Firebase のプロジェクトIDが設定されていない。"""


class TokenVerifier(Protocol):
    def __call__(self, token: str) -> str:
        """トークンを検証して Firebase UID を返す。無効なら InvalidToken。"""
        ...


class FirebaseTokenVerifier:
    def __init__(self, project_id: str) -> None:
        self._project_id = project_id
        self._request = google_requests.Request()

    def __call__(self, token: str) -> str:
        try:
            claims = id_token.verify_firebase_token(
                token, self._request, audience=self._project_id
            )
        except (ValueError, google_auth_exceptions.GoogleAuthError):
            raise InvalidToken("invalid Firebase ID token") from None
        uid = (claims or {}).get("sub")
        if not isinstance(uid, str) or not uid:
            raise InvalidToken("invalid Firebase ID token")
        return uid


# 検証器の作成は最初のリクエストまで遅らせる。
# 起動時やテスト時に設定がなくても動かせるようにするため。
@lru_cache
def get_token_verifier() -> TokenVerifier:
    project_id = os.getenv("FIREBASE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise AuthNotConfigured("FIREBASE_PROJECT_ID is not set")
    return FirebaseTokenVerifier(project_id)
