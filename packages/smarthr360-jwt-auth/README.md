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
| `SMARTHR_JWT_PUBLIC_KEY` | PEM content of the auth public key (escaped `\n` allowed) |
| `SMARTHR_JWT_PUBLIC_KEY_FILE` | …or path to the PEM file |
| `SMARTHR_JWT_ISSUER` | expected `iss` claim (default `smarthr360`) |

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
