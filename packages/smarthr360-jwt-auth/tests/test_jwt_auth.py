"""Tests: token verification + role helpers (no Django settings needed)."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from smarthr360_jwt_auth import conf
from smarthr360_jwt_auth.access import (
    has_hr_access,
    has_manager_access,
    is_admin,
    is_auditor,
)
from smarthr360_jwt_auth.authentication import JWTAuthentication
from smarthr360_jwt_auth.user import TokenUser
from rest_framework import exceptions


@pytest.fixture(scope="module")
def keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


@pytest.fixture(autouse=True)
def _configure_key(keypair, monkeypatch):
    _, public_pem = keypair
    monkeypatch.setenv("SMARTHR_JWT_PUBLIC_KEY", public_pem)
    conf.clear_cache()
    yield
    conf.clear_cache()


def make_token(private_pem, **overrides):
    payload = {
        "token_type": "access",
        "user_id": 42,
        "email": "jane@corp.com",
        "role": "HR",
        "groups": [],
        "iss": "smarthr360",
        "exp": int(time.time()) + 300,
    }
    payload.update(overrides)
    return jwt.encode(payload, private_pem, algorithm="RS256")


class FakeRequest:
    def __init__(self, token=None):
        self.META = {}
        if token:
            self.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"


def test_valid_token_returns_token_user(keypair):
    private_pem, _ = keypair
    user, _ = JWTAuthentication().authenticate(FakeRequest(make_token(private_pem)))
    assert isinstance(user, TokenUser)
    assert user.id == 42 and user.role == "HR" and user.is_authenticated


def test_expired_token_rejected(keypair):
    private_pem, _ = keypair
    token = make_token(private_pem, exp=int(time.time()) - 10)
    with pytest.raises(exceptions.AuthenticationFailed, match="expired"):
        JWTAuthentication().authenticate(FakeRequest(token))


def test_wrong_issuer_rejected(keypair):
    private_pem, _ = keypair
    token = make_token(private_pem, iss="evil")
    with pytest.raises(exceptions.AuthenticationFailed):
        JWTAuthentication().authenticate(FakeRequest(token))


def test_tampered_token_rejected(keypair):
    private_pem, _ = keypair
    token = make_token(private_pem)[:-6] + "abcdef"
    with pytest.raises(exceptions.AuthenticationFailed):
        JWTAuthentication().authenticate(FakeRequest(token))


def test_refresh_token_rejected(keypair):
    private_pem, _ = keypair
    token = make_token(private_pem, token_type="refresh")
    with pytest.raises(exceptions.AuthenticationFailed, match="access"):
        JWTAuthentication().authenticate(FakeRequest(token))


def test_no_header_returns_none():
    assert JWTAuthentication().authenticate(FakeRequest()) is None


def test_role_helpers():
    hr = TokenUser({"user_id": 1, "role": "HR"})
    admin = TokenUser({"user_id": 2, "role": "ADMIN"})
    emp = TokenUser({"user_id": 3, "role": "EMPLOYEE"})
    auditor = TokenUser({"user_id": 4, "role": "EMPLOYEE", "groups": ["AUDITOR"]})

    assert has_hr_access(hr) and has_hr_access(admin) and not has_hr_access(emp)
    assert is_admin(admin) and not is_admin(hr)
    assert has_manager_access(hr) and not has_manager_access(hr, include_hr=False)
    assert is_auditor(auditor) and not is_auditor(emp)
    assert not has_hr_access(None)
