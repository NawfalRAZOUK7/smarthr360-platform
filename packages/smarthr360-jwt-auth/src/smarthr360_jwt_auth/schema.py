"""drf-spectacular integration (optional).

Importing this module registers an OpenAPI security scheme for
``JWTAuthentication`` so every service's Swagger UI shows a working
"Authorize" button (paste a bearer token once, try any endpoint).

The import is attempted automatically from the package ``__init__``;
services without drf-spectacular are unaffected.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class SmartHRJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "smarthr360_jwt_auth.authentication.JWTAuthentication"
    name = "smartHRBearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "RS256 access token issued by smarthr360-auth "
                "(POST /api/auth/login/). Paste the `access` value."
            ),
        }
