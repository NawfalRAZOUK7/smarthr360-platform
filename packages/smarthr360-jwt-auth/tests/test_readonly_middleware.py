"""Tests: AUDITOR tokens are read-only, platform-wide.

The guarantee lives in middleware rather than permission_classes because
services set their own permission_classes on nearly every view, which
overrides DRF defaults. See smarthr360_jwt_auth.readonly.
"""

import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from smarthr360_jwt_auth import conf
from smarthr360_jwt_auth.readonly import AuditorReadOnlyMiddleware

SENTINEL = object()


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


class FakeRequest:
    """Minimal stand-in: the middleware only reads .method and .META."""

    def __init__(self, method, token=None):
        self.method = method
        self.META = {}
        if token is not None:
            self.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"


def make_token(private_pem, role="EMPLOYEE", groups=None, user_id=28):
    return jwt.encode(
        {
            "token_type": "access",
            "user_id": user_id,
            "email": f"u{user_id}@corp.com",
            "role": role,
            "groups": groups or [],
            "is_superuser": role == "ADMIN",
            "iss": "smarthr360",
            "exp": int(time.time()) + 300,
        },
        private_pem,
        algorithm="RS256",
    )


def run(request):
    middleware = AuditorReadOnlyMiddleware(lambda _req: SENTINEL)
    return middleware(request)


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_auditor_write_is_rejected(keypair, method):
    private_pem, _ = keypair
    token = make_token(private_pem, groups=["EMPLOYEE", "AUDITOR"])
    response = run(FakeRequest(method, token))
    assert response is not SENTINEL
    assert response.status_code == 403


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
def test_auditor_read_passes_through(keypair, method):
    private_pem, _ = keypair
    token = make_token(private_pem, groups=["EMPLOYEE", "AUDITOR"])
    assert run(FakeRequest(method, token)) is SENTINEL


def test_plain_employee_write_passes_through(keypair):
    private_pem, _ = keypair
    token = make_token(private_pem, groups=["EMPLOYEE"])
    assert run(FakeRequest("POST", token)) is SENTINEL


def test_admin_write_passes_through(keypair):
    """is_auditor() is true for admins; they must not be locked out."""
    private_pem, _ = keypair
    token = make_token(private_pem, role="ADMIN", groups=["AUDITOR"], user_id=1)
    assert run(FakeRequest("POST", token)) is SENTINEL


def test_unauthenticated_write_passes_through_to_drf():
    """No token: the middleware defers so DRF emits the real 401."""
    assert run(FakeRequest("POST")) is SENTINEL


def test_garbage_token_passes_through_to_drf():
    """Undecodable token: defer rather than masking DRF's auth error."""
    assert run(FakeRequest("POST", "not-a-jwt")) is SENTINEL
