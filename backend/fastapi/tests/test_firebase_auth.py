import pytest
from google.auth import exceptions as google_auth_exceptions

from services import firebase_auth
from services.firebase_auth import (
    AuthNotConfigured,
    FirebaseTokenVerifier,
    InvalidToken,
)


@pytest.fixture
def verifier(monkeypatch):
    calls = {}

    def fake_verify(token, request, audience):
        calls["audience"] = audience
        if token == "good":
            return {"sub": "uid_1"}
        if token == "no-subject":
            return {"aud": audience}
        if token == "expired":
            raise ValueError("Token expired")
        raise google_auth_exceptions.TransportError("could not fetch keys")

    monkeypatch.setattr(firebase_auth.id_token, "verify_firebase_token", fake_verify)
    return FirebaseTokenVerifier("hack26-project"), calls


def test_returns_uid_for_a_valid_token(verifier):
    check, calls = verifier

    assert check("good") == "uid_1"
    # 別プロジェクト向けのトークンを受け付けないよう、自分のプロジェクトIDで検証する。
    assert calls["audience"] == "hack26-project"


@pytest.mark.parametrize("token", ["no-subject", "expired", "network-error"])
def test_invalid_tokens_raise_without_details(verifier, token):
    check, _ = verifier

    with pytest.raises(InvalidToken) as error:
        check(token)
    assert str(error.value) == "invalid Firebase ID token"


def test_project_id_is_required(monkeypatch):
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    firebase_auth.get_token_verifier.cache_clear()

    with pytest.raises(AuthNotConfigured):
        firebase_auth.get_token_verifier()
    firebase_auth.get_token_verifier.cache_clear()


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
def test_project_id_comes_from_env(monkeypatch, env, expected):
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    firebase_auth.get_token_verifier.cache_clear()

    assert firebase_auth.get_token_verifier()._project_id == expected
    firebase_auth.get_token_verifier.cache_clear()
