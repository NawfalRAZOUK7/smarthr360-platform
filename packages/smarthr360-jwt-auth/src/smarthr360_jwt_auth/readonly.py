"""Platform-wide read-only enforcement for auditor tokens.

The AUDITOR group exists so personas like the public demo guest can browse
everything and change nothing. That guarantee is enforced here, as middleware,
rather than through ``permission_classes``: almost every view in the platform
sets its own ``permission_classes``, which overrides DRF's
``DEFAULT_PERMISSION_CLASSES``, so a default-based rule would apply only to the
views that happen not to declare one — and every new endpoint would silently
reopen the hole.

Middleware runs before routing, so the rule holds for any endpoint, present or
future, without each view opting in.
"""

from __future__ import annotations

from django.http import JsonResponse
from rest_framework.permissions import SAFE_METHODS

from . import access
from .authentication import JWTAuthentication

MESSAGE = "Auditor access is read-only."


class AuditorReadOnlyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in SAFE_METHODS:
            user = self._token_user(request)
            # is_auditor() is true for admins as well (it answers "may view
            # audit surfaces"), so admins are exempted before the check.
            if (
                user is not None
                and not access.is_admin(user)
                and access.is_auditor(user)
            ):
                return JsonResponse({"detail": MESSAGE}, status=403)
        return self.get_response(request)

    @staticmethod
    def _token_user(request):
        """Return the token user, or None if there isn't a usable one.

        Any decoding or verification problem returns None so the request
        proceeds and DRF's own authentication produces the real 401 — this
        middleware's job is restricting auditors, not reporting auth errors.
        """
        try:
            result = JWTAuthentication().authenticate(request)
        except Exception:
            return None
        return result[0] if result else None
