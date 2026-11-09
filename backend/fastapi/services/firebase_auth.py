"""Firebase ID トークンの検証。管理者 API の認証に使う。

Firebase Admin SDK（firebase-admin）の verify_id_token を使う。採用理由（google-auth の
verify_firebase_token を直接使う方法との比較）:

- Firebase 固有の要件（alg=RS256 と kid の有無、iss、aud、sub の形式と 128 文字以内、
  iat・exp）を SDK がまとめて検証する。google-auth だけでは iss・sub の上限・alg/kid を
  自前で書く必要があった
- 公開鍵の取得結果を Cache-Control の max-age に従ってキャッシュする（cachecontrol）。
  期限切れ時は再取得し、鍵のローテーションにも追従する
- 公開鍵を取得できないときは CertificateFetchError を返すので、不正なトークン（401）と
  一時的な通信障害（503）を区別できる
- 追加の依存は firebase-admin のみ（google-auth・google-cloud-firestore と共存できる）

SDK が検証しない auth_time（認証日時）は、ここで「過去の日時であること」を確認する。
また SDK は時刻が NaN や Infinity のときに比較をすり抜けるため、exp・iat・auth_time が
有限の数値であることもここで確認する（exp=Infinity の無期限トークンなどを防ぐ）。

トークンの失効（Firebase 側でのアカウント無効化・リフレッシュトークンの失効）は
確認しない（check_revoked=False）。管理者権限の取り消しは Firestore の admins から
UID を削除して行い、次のリクエストから即座に 403 になる。失効確認を有効にすると
管理者のリクエストごとに Firebase への通信が増えるため、必要になった時点で有効にする。
"""

import math
import os
import threading
import time
from collections.abc import Callable
from functools import lru_cache
from typing import Protocol

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from google.auth.credentials import AnonymousCredentials

APP_NAME = "admin-api"


class InvalidToken(ValueError):
    """トークンが無効・期限切れ・形式不正など。理由は外に出さない。"""


class AuthUnavailable(RuntimeError):
    """公開鍵を取得できないなど、一時的に検証できない状態。"""


class AuthNotConfigured(RuntimeError):
    """検証に使う Firebase のプロジェクトIDが設定されていない。"""


class TokenVerifier(Protocol):
    def __call__(self, token: str) -> str:
        """トークンを検証して Firebase UID を返す。

        無効なら InvalidToken、一時的に検証できなければ AuthUnavailable。
        """
        ...


class _NoCredentials(credentials.Base):
    """トークンの検証はプロジェクトIDと Google の公開鍵だけで行える。認証情報は不要。

    既定の認証情報（ADC）を探しに行くと、手元ではメタデータサーバーへの通信が発生する。
    """

    def get_credential(self):
        return AnonymousCredentials()


_app_lock = threading.Lock()


def _app(project_id: str) -> firebase_admin.App:
    # 最初のリクエストが同時に来ても初期化は 1 回だけにする（2 回目の
    # initialize_app は「既にある」というエラーになるため）。
    name = f"{APP_NAME}-{project_id}"
    with _app_lock:
        try:
            return firebase_admin.get_app(name)
        except ValueError:
            return firebase_admin.initialize_app(
                _NoCredentials(), options={"projectId": project_id}, name=name
            )


def _time_claim(claims: dict, name: str) -> float:
    """exp・iat・auth_time を有限の数値として取り出す。そうでなければ InvalidToken。"""
    value = claims.get(name)
    if (
        not isinstance(value, int | float)
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise InvalidToken("invalid Firebase ID token")
    return value


class FirebaseTokenVerifier:
    def __init__(
        self, project_id: str, *, clock: Callable[[], float] = time.time
    ) -> None:
        self._project_id = project_id
        self._app = _app(project_id)
        self._clock = clock

    def __call__(self, token: str) -> str:
        try:
            claims = firebase_auth.verify_id_token(token, app=self._app)
        except firebase_auth.CertificateFetchError:
            raise AuthUnavailable("could not fetch Firebase public keys") from None
        except Exception:
            # 形式不正（alg が配列など）も含め、検証できないトークンはすべて 401。
            # 内部の例外の内容はレスポンスに出さない。
            raise InvalidToken("invalid Firebase ID token") from None

        now = self._clock()
        expires = _time_claim(claims, "exp")
        issued = _time_claim(claims, "iat")
        signed_in = _time_claim(claims, "auth_time")
        # SDK も exp・iat を確認するが、NaN では比較が常に偽になり通ってしまうため、
        # 有限の値であることを確かめてから改めて比べる（時計のずれは SDK と同じく 0）。
        if expires <= now or issued > now or signed_in > now:
            raise InvalidToken("invalid Firebase ID token")
        uid = claims.get("uid")
        if not isinstance(uid, str) or not uid:
            raise InvalidToken("invalid Firebase ID token")
        return uid


# 検証器の作成は最初のリクエストまで遅らせる。
# 起動時やテスト時に設定がなくても動かせるようにするため。
@lru_cache
def get_token_verifier() -> TokenVerifier:
    # .env の FIREBASE_PROJECT_ID / GOOGLE_CLOUD_PROJECT も読む（環境変数が優先）。
    load_dotenv()
    project_id = os.getenv("FIREBASE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise AuthNotConfigured("FIREBASE_PROJECT_ID is not set")
    return FirebaseTokenVerifier(project_id)
