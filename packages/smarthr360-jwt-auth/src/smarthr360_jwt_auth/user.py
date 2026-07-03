"""Lightweight request user built from verified token claims.

No database. Services must never store ForeignKeys to this object;
persist ``user.id`` (the auth service's user id) instead.
"""

from __future__ import annotations


class TokenUser:
    """Duck-types the parts of ``django.contrib.auth`` user that DRF and
    SmartHR360 role helpers rely on."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, payload: dict):
        self.payload = payload
        # SimpleJWT may serialize user_id as a string ("3"); normalize
        # to int so Python-side comparisons against DB integer fields
        # (`obj.user_id == request.user.id`) behave. Non-numeric ids
        # (UUID issuers) pass through unchanged.
        raw_id = payload.get("user_id")
        try:
            self.id = int(raw_id)
        except (TypeError, ValueError):
            self.id = raw_id
        self.pk = self.id
        self.email = payload.get("email", "")
        self.username = payload.get("username", "") or self.email
        self.role = payload.get("role", "EMPLOYEE")
        self.group_names: frozenset[str] = frozenset(payload.get("groups", []) or [])
        self.is_superuser = bool(payload.get("is_superuser", False))
        self.is_staff = bool(payload.get("is_staff", False))
        self.is_active = True

    def in_groups(self, names) -> bool:
        return bool(self.group_names.intersection(names))

    def get_username(self) -> str:
        return self.username

    def __str__(self) -> str:  # pragma: no cover
        return f"TokenUser(id={self.id}, role={self.role})"
