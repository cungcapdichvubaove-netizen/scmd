# -*- coding: utf-8 -*-
"""Authorization policy for asset recovery/offboarding inventory workflows."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from rolepermissions.checkers import has_role


class AssetRecoveryPermissionPolicy:
    """Least-privilege policy for Phase F asset recovery workflows."""

    VIEW_ROLES = ("thu_kho", "ban_giam_doc", "nhan_su", "ke_toan")
    WAREHOUSE_WRITE_ROLES = ("thu_kho", "ban_giam_doc")

    @staticmethod
    def _is_authenticated(user) -> bool:
        return bool(getattr(user, "is_authenticated", False))

    @classmethod
    def _has_any_role(cls, user, roles) -> bool:
        if not cls._is_authenticated(user):
            return False
        if getattr(user, "is_superuser", False):
            return True
        return any(has_role(user, role) for role in roles)

    @classmethod
    def can_view(cls, user) -> bool:
        return cls._has_any_role(user, cls.VIEW_ROLES)

    @classmethod
    def can_create(cls, user) -> bool:
        return cls._has_any_role(user, cls.WAREHOUSE_WRITE_ROLES)

    @classmethod
    def can_post(cls, user) -> bool:
        return cls._has_any_role(user, cls.WAREHOUSE_WRITE_ROLES)

    @classmethod
    def can_void(cls, user) -> bool:
        return cls._has_any_role(user, cls.WAREHOUSE_WRITE_ROLES)

    @classmethod
    def can_approve_damage_report(cls, user) -> bool:
        return cls._has_any_role(user, cls.WAREHOUSE_WRITE_ROLES + ("ke_toan",))

    @staticmethod
    def require(allowed: bool, message: str):
        if not allowed:
            raise PermissionDenied(message)


__all__ = ["AssetRecoveryPermissionPolicy"]
