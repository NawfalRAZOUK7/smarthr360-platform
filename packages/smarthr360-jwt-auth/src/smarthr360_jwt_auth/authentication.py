"""DRF authentication class verifying RS256 tokens locally."""

from __future__ import annotations

import jwt
from rest_framework import authentication, exceptions

from . import conf
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
        options = {"require": ["exp"]}
        audience = conf.get_audience()
        try:
            return jwt.decode(
                token,
                conf.get_public_key(),
                algorithms=["RS256"],
                issuer=conf.get_issuer(),
                audience=audience,
                leeway=conf.get_leeway(),
                options={**options, "verify_aud": audience is not None},
            )
        except jwt.ExpiredSignatureError as exc:
            raise exceptions.AuthenticationFailed("Token expired.") from exc
        except jwt.InvalidIssuerError as exc:
            raise exceptions.AuthenticationFailed("Invalid token issuer.") from exc
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed(f"Invalid token: {exc}") from exc

    def authenticate_header(self, request):  # pragma: no cover
        return f'{self.keyword} realm="{self.www_authenticate_realm}"'
