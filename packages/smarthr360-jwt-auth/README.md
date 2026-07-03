# smarthr360-jwt-auth

Shared RS256 JWT verification client for SmartHR360 microservices.
Verifies tokens issued by `smarthr360-auth` **locally** (no network call,
no shared database) and exposes claim-based role helpers and DRF
permission classes that mirror the legacy `accounts.access` /
`accounts.permissions` APIs.

## Install

```bash
pip install "smarthr360-jwt-auth @ git+https://github.com/NawfalRAZOUK7/smarthr360.git#subdirectory=packages/smarthr360-jwt-auth"
# or, inside the umbrella checkout:
pip install -e packages/smarthr360-jwt-auth
```

## Configure (each service)

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "smarthr360_jwt_auth.authentication.JWTAuthentication",
    ),
}
```

Environment:

| Variable | Meaning |
|---|---|
| `SMARTHR_JWT_PUBLIC_KEY` | static PEM public key (escaped `\n` allowed) |
| `SMARTHR_JWT_PUBLIC_KEY_FILE` | …or path to the PEM file |
| `SMARTHR_JWT_JWKS_URL` | …or fetch keys from auth's `/.well-known/jwks.json` (cached) |
| `SMARTHR_JWT_JWKS_CACHE_SECONDS` | JWKS cache TTL (default 3600) |
| `SMARTHR_JWT_ISSUER` | expected `iss` claim (default `smarthr360`) |

Static PEM and JWKS can be combined; at least one is required.

### Key rotation

Zero-downtime rotation is supported out of the box: keys are matched by
`kid` when the token header carries one; tokens without a `kid`
(SimpleJWT default) are verified against **every** key in the JWKS —
cheap, since a rotating JWKS holds 2-3 keys at most. An unknown `kid`
triggers one forced JWKS refresh (the "new key just published" case),
and a stale cache keeps serving if auth is briefly unreachable.

Rotation procedure: publish the new key in auth's JWKS *alongside* the
old one → switch auth's signing key → retire the old key after the
refresh-token lifetime.

### Swagger "Authorize" button

When drf-spectacular is installed, importing the package registers a
bearer security scheme automatically — every service's `/docs/` gets a
working **Authorize** button (paste an access token, try any endpoint).

## Use

```python
from smarthr360_jwt_auth.access import has_hr_access, has_manager_access
from smarthr360_jwt_auth.permissions import IsHRRole, IsManagerOrAbove, IsSelfOrHR

class EmployeeProfileViewSet(ModelViewSet):
    permission_classes = [IsSelfOrHR]
```

`request.user` is a `TokenUser` (`id`, `email`, `role`, `group_names`) —
persist `request.user.id` as `user_id`; never ForeignKey to another
service's tables.

## Test

```bash
pip install -e ".[dev]" && pytest
```
