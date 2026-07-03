"""Verification-key resolution: static PEM and/or JWKS URL, with
rotation support.

Sources (both optional, combinable):
  - static PEM: SMARTHR_JWT_PUBLIC_KEY / SMARTHR_JWT_PUBLIC_KEY_FILE
  - JWKS URL:   SMARTHR_JWT_JWKS_URL (e.g. the auth service's
                /.well-known/jwks.json), cached for
                SMARTHR_JWT_JWKS_CACHE_SECONDS (default 3600)

Rotation model:
  - keys are addressed by `kid` when the token header carries one;
  - tokens WITHOUT a kid (SimpleJWT default) are verified against every
    known key — JWKS documents stay small (1-3 keys during a rotation),
    so try-all is cheap and makes zero-downtime rotation work today;
  - a kid that isn't in the cached JWKS triggers ONE forced refresh
    (the "new key just published" case) before failing.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.request

import jwt as pyjwt

from . import conf

_lock = threading.Lock()
_jwks_cache: dict = {"keys": [], "fetched_at": 0.0}


class KeyResolutionError(Exception):
    pass


def _fetch_jwks(url: str) -> list[dict]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
        payload = json.load(response)
    keys = payload.get("keys", payload)
    if not isinstance(keys, list) or not keys:
        raise KeyResolutionError(f"invalid JWKS payload from {url}")
    return keys


def _jwks_keys(force_refresh: bool = False) -> list[dict]:
    """Return the cached JWKS entries, refreshing when stale/forced."""
    url = conf.get_jwks_url()
    if not url:
        return []
    ttl = conf.get_jwks_cache_seconds()
    with _lock:
        stale = (time.monotonic() - _jwks_cache["fetched_at"]) > ttl
        if force_refresh or stale or not _jwks_cache["keys"]:
            try:
                _jwks_cache["keys"] = _fetch_jwks(url)
                _jwks_cache["fetched_at"] = time.monotonic()
            except Exception as exc:
                if not _jwks_cache["keys"]:
                    raise KeyResolutionError(
                        f"unable to fetch JWKS from {url}: {exc}"
                    ) from exc
                # keep serving the stale cache if auth is briefly down
        return list(_jwks_cache["keys"])


def _jwk_to_key(entry: dict):
    return pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(entry))


def get_verification_keys(kid: str | None = None,
                          force_refresh: bool = False) -> list:
    """Candidate public keys for verifying one token.

    With a `kid`: the matching JWKS key only (plus the static PEM as a
    safety net). Without: every known key (static PEM first).
    """
    candidates: list = []

    static_pem = conf.get_public_key(required=False)
    jwks_entries = _jwks_keys(force_refresh=force_refresh)

    if kid:
        for entry in jwks_entries:
            if entry.get("kid") == kid:
                candidates.append(_jwk_to_key(entry))
        if static_pem:
            candidates.append(static_pem)
    else:
        if static_pem:
            candidates.append(static_pem)
        candidates.extend(_jwk_to_key(e) for e in jwks_entries)

    if not candidates:
        raise KeyResolutionError(
            "no verification keys available: configure "
            "SMARTHR_JWT_PUBLIC_KEY(_FILE) and/or SMARTHR_JWT_JWKS_URL."
        )
    return candidates


def clear_cache() -> None:
    """Testing helper."""
    with _lock:
        _jwks_cache["keys"] = []
        _jwks_cache["fetched_at"] = 0.0
