"""SmartHR360 shared JWT verification client.

Services install this package to verify RS256 tokens issued by
``smarthr360-auth`` WITHOUT any call to the auth service or its database.

Usage (Django settings)::

    REST_FRAMEWORK = {
        "DEFAULT_AUTHENTICATION_CLASSES": (
            "smarthr360_jwt_auth.authentication.JWTAuthentication",
        ),
    }

    # Environment (one of):
    #   SMARTHR_JWT_PUBLIC_KEY       PEM content of the auth public key
    #   SMARTHR_JWT_PUBLIC_KEY_FILE  path to the PEM file
"""

from .authentication import JWTAuthentication
from .user import TokenUser

# Optional drf-spectacular integration: registers the bearer security
# scheme so Swagger UIs get a working "Authorize" button. Skipped when
# spectacular is absent OR Django settings aren't configured (e.g. the
# package's own unit tests, plain scripts).
try:  # pragma: no cover - trivially environment-dependent
    from . import schema  # noqa: F401
except Exception:  # ImportError / ImproperlyConfigured
    pass

__all__ = ["JWTAuthentication", "TokenUser"]
__version__ = "1.1.0"
