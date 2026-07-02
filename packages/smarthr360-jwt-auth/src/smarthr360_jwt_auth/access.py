"""Claim-based role helpers.

Drop-in replacements for ``accounts.access`` in the legacy monolith:
same names, same semantics, but evaluated from JWT claims instead of
the auth database. Works with ``TokenUser`` and (inside the auth
service itself) with real Django users exposing ``role``/``groups``.
"""

from __future__ import annotations

# Group names mirror accounts/grouping.py in smarthr360-auth.
HR_GROUPS = frozenset({"HR", "HR_ADMIN"})
MANAGER_GROUPS = frozenset({"MANAGER", "MANAGER_ADMIN"})
EMPLOYEE_GROUPS = frozenset({"EMPLOYEE", "EMPLOYEE_ADMIN"})
AUDITOR_GROUPS = frozenset({"AUDITOR"})
SECURITY_ADMIN_GROUPS = frozenset({"SECURITY_ADMIN"})
SUPPORT_GROUPS = frozenset({"SUPPORT"})


def _is_authenticated(user) -> bool:
    return bool(user and getattr(user, "is_authenticated", False))


def _in_groups(user, names) -> bool:
    if not _is_authenticated(user):
        return False
    checker = getattr(user, "in_groups", None)
    if callable(checker):  # TokenUser
        return checker(names)
    groups = getattr(user, "groups", None)  # Django user fallback
    if groups is not None:
        return groups.filter(name__in=names).exists()
    return False


def is_admin(user) -> bool:
    return bool(
        _is_authenticated(user)
        and (getattr(user, "is_superuser", False) or getattr(user, "role", None) == "ADMIN")
    )


def is_hr(user) -> bool:
    if not _is_authenticated(user):
        return False
    return bool(getattr(user, "role", None) == "HR" or _in_groups(user, HR_GROUPS))


def is_manager(user) -> bool:
    if not _is_authenticated(user):
        return False
    return bool(getattr(user, "role", None) == "MANAGER" or _in_groups(user, MANAGER_GROUPS))


def is_employee(user) -> bool:
    if not _is_authenticated(user):
        return False
    return bool(getattr(user, "role", None) == "EMPLOYEE" or _in_groups(user, EMPLOYEE_GROUPS))


def has_hr_access(user) -> bool:
    return bool(is_admin(user) or is_hr(user))


def has_manager_access(user, *, include_hr: bool = True) -> bool:
    if is_admin(user) or is_manager(user):
        return True
    return bool(include_hr and is_hr(user))


def has_employee_access(user) -> bool:
    return bool(is_admin(user) or is_employee(user))


def is_auditor(user) -> bool:
    return bool(is_admin(user) or _in_groups(user, AUDITOR_GROUPS))


def is_security_admin(user) -> bool:
    return bool(is_admin(user) or _in_groups(user, SECURITY_ADMIN_GROUPS))


def is_support(user) -> bool:
    return bool(is_admin(user) or _in_groups(user, SUPPORT_GROUPS))
