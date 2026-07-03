"""DRF authentication class verifying RS256 tokens locally."""

from __future__ import annotations

import jwt
from rest_framework import authentication, exceptions

from . import conf, keys
from .user import TokenUser


class JWTAuthentication(authentication.BaseAuthentication):
    """Verify ``Authorization: Bearer <token>`` against the auth service's
    RS256 public key. No network call, no database."""

    keyword = "Bearer"
    www_authenticate_realm = "api"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request)
        if not header:
            return None
        parts = header.split()
        if parts[0].decode().lower() != self.keyword.lower():
            return None
        if len(parts) != 2:
            raise exceptions.AuthenticationFailed(
                "Invalid Authorization header format. Expected 'Bearer <token>'."
            )

        token = parts[1].decode()
        payload = self._decode(token)

        if payload.get("token_type") not in (None, "access"):
            raise exceptions.AuthenticationFailed("Only access tokens are accepted.")
        if "user_id" not in payload:
            raise exceptions.AuthenticationFailed("Token has no user_id claim.")

        return (TokenUser(payload), token)

    def _decode(self, token: str) -> dict:
        """Verify against every candidate key (static PEM and/or JWKS).

        Rotation-aware: kid-addressed keys are matched exactly; a kid
        missing from the cached JWKS triggers one forced refresh; tokens
        without a kid are tried against all known keys.
        """
        audience = conf.get_audience()
        decode_kwargs = {
            "algorithms": ["RS256"],
            "issuer": conf.get_issuer(),
            "audience": audience,
            "leeway": conf.get_leeway(),
            "options": {"require": ["exp"], "verify_aud": audience is not None},
        }

        try:
            kid = jwt.get_unverified_header(token).get("kid")
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed(f"Invalid token: {exc}") from exc

        def try_keys(force_refresh: bool) -> dict | None:
            try:
                candidates = keys.get_verification_keys(
                    kid=kid, force_refresh=force_refresh
                )
            except keys.KeyResolutionError as exc:
                # An unknown kid can leave zero candidates on the first
                # pass — let the forced-refresh pass have a chance.
                if force_refresh or not conf.get_jwks_url():
                    raise exceptions.AuthenticationFailed(str(exc)) from exc
                return None
            for key in candidates:
                try:
                    return jwt.decode(token, key, **decode_kwargs)
                except jwt.ExpiredSignatureError as exc:
                    # signature matched this key -> genuinely expired
                    raise exceptions.AuthenticationFailed("Token expired.") from exc
                except jwt.InvalidIssuerError as exc:
                    raise exceptions.AuthenticationFailed(
                        "Invalid token issuer."
                    ) from exc
                except jwt.InvalidSignatureError:
                    continue  # wrong key — try the next candidate
                except jwt.InvalidTokenError as exc:
                    raise exceptions.AuthenticationFailed(
                        f"Invalid token: {exc}"
                    ) from exc
            return None

        payload = try_keys(force_refresh=False)
        if payload is None and conf.get_jwks_url():
            # rotation case: a newly-published key may not be cached yet
            payload = try_keys(force_refresh=True)
        if payload is None:
            raise exceptions.AuthenticationFailed(
                "Invalid token: signature does not match any known key."
            )
        return payload

    def authenticate_header(self, request):  # pragma: no cover
        return f'{self.keyword} realm="{self.www_authenticate_realm}"'
