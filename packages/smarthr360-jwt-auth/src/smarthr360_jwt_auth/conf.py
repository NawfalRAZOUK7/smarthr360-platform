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
def get_public_key() -> str:
    """Return the PEM public key used to verify tokens."""
    key = _get("PUBLIC_KEY", "SMARTHR_JWT_PUBLIC_KEY")
    if key:
        # Allow escaped newlines in env vars ("-----BEGIN...\n...")
        return key.replace("\\n", "\n")
    path = _get("PUBLIC_KEY_FILE", "SMARTHR_JWT_PUBLIC_KEY_FILE")
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    raise RuntimeError(
        "smarthr360-jwt-auth: no public key configured. Set SMARTHR_JWT_PUBLIC_KEY "
        "or SMARTHR_JWT_PUBLIC_KEY_FILE (env), or SMARTHR_JWT_AUTH['PUBLIC_KEY'] "
        "in Django settings."
    )


def get_issuer() -> str:
    return _get("ISSUER", "SMARTHR_JWT_ISSUER", "smarthr360")


def get_audience() -> str | None:
    return _get("AUDIENCE", "SMARTHR_JWT_AUDIENCE", None)


def get_leeway() -> int:
    return int(_get("LEEWAY", "SMARTHR_JWT_LEEWAY", 0))


def clear_cache() -> None:
    """Testing helper: reset the cached public key."""
    get_public_key.cache_clear()
