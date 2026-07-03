"""JWKS URL support + key-rotation behavior."""

import base64
import time
from unittest import mock

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from rest_framework import exceptions

from smarthr360_jwt_auth import conf, keys
from smarthr360_jwt_auth.authentication import JWTAuthentication

JWKS_URL = "http://auth:8000/.well-known/jwks.json"


def make_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return key, private_pem


def to_jwk(key, kid):
    numbers = key.public_key().public_numbers()

    def b64(value):
        raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return {"kty": "RSA", "use": "sig", "alg": "RS256", "kid": kid,
            "n": b64(numbers.n), "e": b64(numbers.e)}


def make_token(private_pem, kid=None, **overrides):
    payload = {
        "token_type": "access", "user_id": 1, "email": "a@b.c",
        "role": "HR", "groups": [], "iss": "smarthr360",
        "exp": int(time.time()) + 300,
    }
    payload.update(overrides)
    headers = {"kid": kid} if kid else None
    return jwt.encode(payload, private_pem, algorithm="RS256", headers=headers)


class FakeRequest:
    def __init__(self, token):
        self.META = {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _jwks_env(monkeypatch):
    monkeypatch.delenv("SMARTHR_JWT_PUBLIC_KEY", raising=False)
    monkeypatch.setenv("SMARTHR_JWT_JWKS_URL", JWKS_URL)
    conf.clear_cache()
    yield
    conf.clear_cache()


def patch_jwks(documents):
    """Patch the fetch to return successive JWKS documents."""
    it = iter(documents)
    last = documents[-1]

    def fake_fetch(url):
        assert url == JWKS_URL
        try:
            return next(it)
        except StopIteration:
            return last

    return mock.patch.object(keys, "_fetch_jwks", side_effect=fake_fetch)


def test_jwks_only_verification_no_pem():
    key, pem = make_keypair()
    with patch_jwks([[to_jwk(key, "k1")]]):
        user, _ = JWTAuthentication().authenticate(
            FakeRequest(make_token(pem, kid="k1"))
        )
    assert user.id == 1 and user.role == "HR"


def test_kid_matching_picks_correct_key_among_many():
    key_a, pem_a = make_keypair()
    key_b, pem_b = make_keypair()
    jwks = [to_jwk(key_a, "old"), to_jwk(key_b, "new")]
    with patch_jwks([jwks]):
        user, _ = JWTAuthentication().authenticate(
            FakeRequest(make_token(pem_b, kid="new"))
        )
        assert user.id == 1
        # and the other key still works too (rotation overlap window)
        user, _ = JWTAuthentication().authenticate(
            FakeRequest(make_token(pem_a, kid="old"))
        )
        assert user.id == 1


def test_token_without_kid_tries_all_keys():
    key_a, _ = make_keypair()
    key_b, pem_b = make_keypair()
    with patch_jwks([[to_jwk(key_a, "a"), to_jwk(key_b, "b")]]):
        user, _ = JWTAuthentication().authenticate(
            FakeRequest(make_token(pem_b))  # SimpleJWT-style: no kid header
        )
    assert user.id == 1


def test_rotation_unknown_kid_forces_one_refresh():
    key_old, _ = make_keypair()
    key_new, pem_new = make_keypair()
    docs = [
        [to_jwk(key_old, "old")],                      # cached (stale) doc
        [to_jwk(key_old, "old"), to_jwk(key_new, "new")],  # refreshed doc
    ]
    with patch_jwks(docs) as fetch:
        keys._jwks_keys()  # warm the cache with the stale document
        user, _ = JWTAuthentication().authenticate(
            FakeRequest(make_token(pem_new, kid="new"))
        )
        assert user.id == 1
        assert fetch.call_count == 2  # initial + forced refresh


def test_wrong_key_rejected_even_after_refresh():
    key_known, _ = make_keypair()
    _, pem_unknown = make_keypair()
    with patch_jwks([[to_jwk(key_known, "k1")]]):
        with pytest.raises(exceptions.AuthenticationFailed, match="known key"):
            JWTAuthentication().authenticate(FakeRequest(make_token(pem_unknown)))


def test_stale_cache_survives_auth_outage():
    key, pem = make_keypair()
    call = {"n": 0}

    def flaky_fetch(url):
        call["n"] += 1
        if call["n"] == 1:
            return [to_jwk(key, "k1")]
        raise OSError("auth is down")

    with mock.patch.object(keys, "_fetch_jwks", side_effect=flaky_fetch):
        keys._jwks_keys()                      # cache warmed
        keys._jwks_cache["fetched_at"] = 0.0   # force staleness
        user, _ = JWTAuthentication().authenticate(
            FakeRequest(make_token(pem, kid="k1"))
        )
    assert user.id == 1  # served from the stale cache


def test_expired_token_still_reported_as_expired():
    key, pem = make_keypair()
    with patch_jwks([[to_jwk(key, "k1")]]):
        token = make_token(pem, kid="k1", exp=int(time.time()) - 10)
        with pytest.raises(exceptions.AuthenticationFailed, match="expired"):
            JWTAuthentication().authenticate(FakeRequest(token))


def test_static_pem_and_jwks_combine(monkeypatch):
    key_jwks, pem_jwks = make_keypair()
    key_static, pem_static = make_keypair()
    static_pub = (
        key_static.public_key()
        .public_bytes(serialization.Encoding.PEM,
                      serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    monkeypatch.setenv("SMARTHR_JWT_PUBLIC_KEY", static_pub)
    conf.clear_cache()
    with patch_jwks([[to_jwk(key_jwks, "k1")]]):
        for pem in (pem_static, pem_jwks):
            user, _ = JWTAuthentication().authenticate(
                FakeRequest(make_token(pem))
            )
            assert user.id == 1


def test_spectacular_extension_registered():
    pytest.importorskip("drf_spectacular")
    import django
    from django.conf import settings as dj_settings

    if not dj_settings.configured:
        dj_settings.configure(
            INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
            REST_FRAMEWORK={},
        )
        django.setup()

    from drf_spectacular.extensions import OpenApiAuthenticationExtension

    import smarthr360_jwt_auth.schema  # noqa: F401 - registers the extension

    targets = [
        getattr(cls, "target_class", None)
        for cls in OpenApiAuthenticationExtension._registry
    ]
    assert "smarthr360_jwt_auth.authentication.JWTAuthentication" in targets
