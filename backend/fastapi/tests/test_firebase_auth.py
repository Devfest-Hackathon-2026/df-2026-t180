"""Firebase ID トークン検証のテスト。

テスト用の RSA 鍵で実際に署名したトークンを使い、Firebase Admin SDK の署名・claim 検証と
公開鍵キャッシュの経路を通す。差し替えるのは公開鍵を返す HTTP 通信だけ。
"""

import base64
import io
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from email.utils import formatdate

import pytest
import requests
import urllib3
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from google.auth import crypt
from google.auth import jwt as google_jwt

from services import firebase_auth
from services.firebase_auth import (
    AuthNotConfigured,
    AuthUnavailable,
    FirebaseTokenVerifier,
    InvalidToken,
)


def make_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return private_pem, cert.public_bytes(serialization.Encoding.PEM).decode()


KEY_1 = make_key()
KEY_2 = make_key()
OTHER_KEY = make_key()


class _Body(io.BytesIO):
    """http.client の応答と同じく、読み終えると fp が None になる本文。

    cachecontrol はこれを見て「読み終えた」と判断し、応答をキャッシュに保存する。
    """

    def __init__(self, data):
        super().__init__(data)
        self.fp = self

    def read(self, *args):
        chunk = super().read(*args)
        if self.tell() >= len(self.getbuffer()):
            self.fp = None
        return chunk


class FakeKeyServer:
    """Google の公開鍵エンドポイントの代わり。取得回数を数え、応答を差し替えられる。"""

    def __init__(self):
        self.keys = {"k1": KEY_1[1]}
        self.max_age = 3600
        self.fetches = 0
        self.down = False

    def send(self, adapter, request):
        if "securetoken" not in request.url and "x509" not in request.url:
            raise AssertionError(f"unexpected request to {request.url}")
        self.fetches += 1
        if self.down:
            raise requests.exceptions.ConnectionError("network down")
        body = json.dumps(self.keys).encode()
        # requests と同じ形の応答を作り、cachecontrol が実際にキャッシュできるようにする
        raw = urllib3.HTTPResponse(
            body=_Body(body),
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
                "Cache-Control": f"public, max-age={self.max_age}",
                "Date": formatdate(usegmt=True),
            },
            status=200,
            preload_content=False,
            decode_content=False,
        )
        return adapter.build_response(request, raw)


@pytest.fixture
def key_server(monkeypatch):
    server = FakeKeyServer()
    monkeypatch.setattr(
        requests.adapters.HTTPAdapter,
        "send",
        lambda adapter, request, *args, **kwargs: server.send(adapter, request),
    )
    return server


@pytest.fixture
def project():
    # プロジェクトごとに SDK のアプリと鍵キャッシュが分かれるよう、毎回別のIDにする。
    return f"test-{uuid.uuid4().hex[:12]}"


def claims(project, **overrides):
    now = int(time.time())
    base = {
        "iss": f"https://securetoken.google.com/{project}",
        "aud": project,
        "sub": "admin_uid",
        "iat": now - 10,
        "exp": now + 3600,
        "auth_time": now - 60,
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


def sign(payload, key=KEY_1, kid="k1"):
    signer = crypt.RSASigner.from_string(key[0], key_id=kid)
    return google_jwt.encode(signer, payload).decode()


def raw_token(header, payload):
    def part(value):
        data = json.dumps(value).encode()
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    return f"{part(header)}.{part(payload)}.{part('signature')}"


# --- 正常系 ---------------------------------------------------------------------


def test_accepts_a_correctly_signed_token(key_server, project):
    verify = FirebaseTokenVerifier(project)

    assert verify(sign(claims(project))) == "admin_uid"


# --- claim・署名の異常系 ----------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://securetoken.google.com/another-project"},
        {"iss": "https://accounts.google.com"},
        {"aud": "another-project"},
        {"exp": int(time.time()) - 10},
        {"iat": int(time.time()) + 3600},
        {"sub": ""},
        {"sub": "a" * 129},
        {"sub": None},
        {"auth_time": int(time.time()) + 3600},
        {"auth_time": None},
        {"auth_time": "yesterday"},
        {"auth_time": True},
    ],
    ids=lambda o: ",".join(f"{k}={str(v)[:12]}" for k, v in o.items()),
)
def test_rejects_invalid_claims(key_server, project, overrides):
    verify = FirebaseTokenVerifier(project)

    with pytest.raises(InvalidToken):
        verify(sign(claims(project, **overrides)))


def test_accepts_a_128_character_uid(key_server, project):
    verify = FirebaseTokenVerifier(project)

    assert verify(sign(claims(project, sub="a" * 128))) == "a" * 128


@pytest.mark.parametrize(
    "token_for",
    [
        # 別の鍵で署名した（署名が合わない）
        lambda p: sign(claims(p), key=OTHER_KEY, kid="k1"),
        # 公開鍵に存在しない kid
        lambda p: sign(claims(p), kid="unknown"),
    ],
    ids=["wrong-signature", "unknown-kid"],
)
def test_rejects_bad_signatures(key_server, project, token_for):
    verify = FirebaseTokenVerifier(project)

    with pytest.raises(InvalidToken):
        verify(token_for(project))


@pytest.mark.parametrize(
    "header",
    [
        {"alg": ["RS256"], "kid": "k1", "typ": "JWT"},
        {"alg": {"name": "RS256"}, "kid": "k1", "typ": "JWT"},
        {"alg": None, "kid": "k1", "typ": "JWT"},
        {"alg": "HS256", "kid": "k1", "typ": "JWT"},
        {"alg": "none", "kid": "k1", "typ": "JWT"},
        {"alg": "RS256", "kid": ["k1"], "typ": "JWT"},
        {"alg": "RS256", "kid": {"id": "k1"}, "typ": "JWT"},
        {"alg": "RS256", "kid": None, "typ": "JWT"},
        {"alg": "RS256", "typ": "JWT"},
    ],
    ids=lambda h: f"alg={h.get('alg')!r},kid={h.get('kid')!r}",
)
def test_rejects_malformed_headers_without_crashing(key_server, project, header):
    verify = FirebaseTokenVerifier(project)

    with pytest.raises(InvalidToken) as error:
        verify(raw_token(header, claims(project)))
    # 内部の例外や詳細は外に出さない。
    assert str(error.value) == "invalid Firebase ID token"


@pytest.mark.parametrize("token", ["", "abc", "a.b", "a.b.c.d", "....", "🙂.🙂.🙂"])
def test_rejects_garbage(key_server, project, token):
    verify = FirebaseTokenVerifier(project)

    with pytest.raises(InvalidToken):
        verify(token)


# --- 公開鍵のキャッシュ ------------------------------------------------------------


def test_reuses_cached_keys_within_max_age(key_server, project):
    verify = FirebaseTokenVerifier(project)

    verify(sign(claims(project)))
    verify(sign(claims(project)))
    verify(sign(claims(project)))

    assert key_server.fetches == 1


def test_fetches_again_when_the_cache_expires(key_server, project):
    key_server.max_age = 0
    verify = FirebaseTokenVerifier(project)

    verify(sign(claims(project)))
    verify(sign(claims(project)))

    assert key_server.fetches == 2


def test_follows_key_rotation_after_expiry(key_server, project):
    key_server.max_age = 0
    verify = FirebaseTokenVerifier(project)
    assert verify(sign(claims(project))) == "admin_uid"

    # Google が新しい鍵 k2 を公開し、k1 を外した。
    key_server.keys = {"k2": KEY_2[1]}

    assert verify(sign(claims(project), key=KEY_2, kid="k2")) == "admin_uid"
    with pytest.raises(InvalidToken):
        verify(sign(claims(project), key=KEY_1, kid="k1"))


def test_network_failure_is_unavailable_not_invalid(key_server, project):
    key_server.down = True
    verify = FirebaseTokenVerifier(project)

    with pytest.raises(AuthUnavailable):
        verify(sign(claims(project)))


def test_cached_keys_keep_working_during_a_short_outage(key_server, project):
    verify = FirebaseTokenVerifier(project)
    verify(sign(claims(project)))

    key_server.down = True

    assert verify(sign(claims(project))) == "admin_uid"
    assert key_server.fetches == 1


# --- 設定 -------------------------------------------------------------------------


@pytest.fixture
def no_dotenv(monkeypatch):
    # 手元の .env に左右されないよう、テストでは読み込まない。
    monkeypatch.setattr(firebase_auth, "load_dotenv", lambda: None)
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    firebase_auth.get_token_verifier.cache_clear()
    yield monkeypatch
    firebase_auth.get_token_verifier.cache_clear()


def test_project_id_is_required(no_dotenv):
    with pytest.raises(AuthNotConfigured):
        firebase_auth.get_token_verifier()


def test_reads_project_id_from_dotenv(no_dotenv):
    no_dotenv.setattr(
        firebase_auth,
        "load_dotenv",
        lambda: no_dotenv.setenv("FIREBASE_PROJECT_ID", "from-dotenv"),
    )

    assert firebase_auth.get_token_verifier()._project_id == "from-dotenv"


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"FIREBASE_PROJECT_ID": "fb-project"}, "fb-project"),
        ({"GOOGLE_CLOUD_PROJECT": "gcp-project"}, "gcp-project"),
        (
            {"FIREBASE_PROJECT_ID": "fb-project", "GOOGLE_CLOUD_PROJECT": "gcp"},
            "fb-project",
        ),
    ],
)
def test_project_id_comes_from_env(no_dotenv, env, expected):
    for key, value in env.items():
        no_dotenv.setenv(key, value)

    assert firebase_auth.get_token_verifier()._project_id == expected
