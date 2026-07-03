"""Configuration for token verification.

Resolution order for every setting:
1. Django ``settings.SMARTHR_JWT_AUTH`` dict (if Django is configured)
2. Environment variables
3. Defaults
"""

from __future__ import annotations

import os
from functools import lru_cache


def _django_conf() -> dict:
    try:
        from django.conf import settings

        if settings.configured:
            return getattr(settings, "SMARTHR_JWT_AUTH", {}) or {}
    except Exception:  # pragma: no cover - Django not installed/configured
        pass
    return {}


def _get(name: str, env: str, default=None):
    conf = _django_conf()
    if name in conf:
        return conf[name]
    return os.environ.get(env, default)


@lru_cache(maxsize=1)
def _resolve_public_key() -> str | None:
    key = _get("PUBLIC_KEY", "SMARTHR_JWT_PUBLIC_KEY")
    if key:
        # Allow escaped newlines in env vars ("-----BEGIN...\n...")
        return key.replace("\\n", "\n")
    path = _get("PUBLIC_KEY_FILE", "SMARTHR_JWT_PUBLIC_KEY_FILE")
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return None


def get_public_key(required: bool = True) -> str | None:
    """Return the static PEM public key, if configured.

    With a JWKS URL configured the static key is optional; `required`
    preserves the historical hard-failure for PEM-only setups.
    """
    key = _resolve_public_key()
    if key is None and required and not get_jwks_url():
        raise RuntimeError(
            "smarthr360-jwt-auth: no verification key configured. Set "
            "SMARTHR_JWT_PUBLIC_KEY / SMARTHR_JWT_PUBLIC_KEY_FILE or "
            "SMARTHR_JWT_JWKS_URL (env), or the SMARTHR_JWT_AUTH dict "
            "in Django settings."
        )
    return key


def get_jwks_url() -> str | None:
    """JWKS document URL (e.g. auth's /.well-known/jwks.json)."""
    return _get("JWKS_URL", "SMARTHR_JWT_JWKS_URL", None)


def get_jwks_cache_seconds() -> int:
    return int(_get("JWKS_CACHE_SECONDS", "SMARTHR_JWT_JWKS_CACHE_SECONDS", 3600))


def get_issuer() -> str:
    return _get("ISSUER", "SMARTHR_JWT_ISSUER", "smarthr360")


def get_audience() -> str | None:
    return _get("AUDIENCE", "SMARTHR_JWT_AUDIENCE", None)


def get_leeway() -> int:
    return int(_get("LEEWAY", "SMARTHR_JWT_LEEWAY", 0))


def clear_cache() -> None:
    """Testing helper: reset the cached public key (and JWKS cache)."""
    _resolve_public_key.cache_clear()
    from . import keys

    keys.clear_cache()
