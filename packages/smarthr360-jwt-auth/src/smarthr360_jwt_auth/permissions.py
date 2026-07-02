"""DRF permission classes mirroring accounts/permissions.py, claim-based."""

from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission

from . import access


class IsAdminRole(BasePermission):
    message = "Admin role required."

    def has_permission(self, request, view):
        return access.is_admin(request.user)


class IsHRRole(BasePermission):
    message = "HR or Admin role required."

    def has_permission(self, request, view):
        return access.has_hr_access(request.user)


class IsManagerOrAbove(BasePermission):
    message = "Manager, HR or Admin role required."

    def has_permission(self, request, view):
        return access.has_manager_access(request.user)


class IsEmployee(BasePermission):
    message = "Employee role required."

    def has_permission(self, request, view):
        return access.has_employee_access(request.user)


class ReadOnlyOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return False
        if request.method in SAFE_METHODS:
            return True
        return access.is_admin(user)


class IsAuditorReadOnly(BasePermission):
    message = "Auditor access is read-only."

    def has_permission(self, request, view):
        if request.method not in SAFE_METHODS:
            return False
        return access.is_auditor(request.user)


class IsHROrAuditorReadOnly(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if request.method in SAFE_METHODS:
            return access.has_hr_access(user) or access.is_auditor(user)
        return access.has_hr_access(user)


class IsManagerOrAuditorReadOnly(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if request.method in SAFE_METHODS:
            return access.has_manager_access(user) or access.is_auditor(user)
        return access.has_manager_access(user)


class IsSelfOrHR(BasePermission):
    """Object-level: owner (obj.user_id == request.user.id) or HR/Admin."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if access.has_hr_access(user):
            return True
        owner_id = getattr(obj, "user_id", None)
        return owner_id is not None and str(owner_id) == str(getattr(user, "id", None))
