# -*- coding: utf-8 -*-
"""
Inventory access policies for SCMD Pro.

This module centralizes inventory object-scope and action checks. Warehouse
delegation is not implemented yet, so authorization currently requires:
- authenticated user
- business role approved for inventory operations
- organization-scoped object visibility
- Django functional permission for the requested action
"""

from __future__ import annotations

from typing import Type

from django.db import models
from rolepermissions.checkers import has_role

from core.policy_result import ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE, PolicyResult
from inventory.models import PhieuNhap, PhieuXuat


class InventoryScopePolicy:
    """Organization-scope helpers for inventory querysets."""

    @staticmethod
    def current_queryset(model: Type[models.Model]):
        manager = getattr(model, "objects", None)
        if manager is None or not hasattr(manager, "for_current"):
            return model.objects.none()
        return manager.for_current()

    @classmethod
    def scope_queryset(cls, model: Type[models.Model], queryset):
        ids = list(queryset.values_list("pk", flat=True))
        if not ids:
            return cls.current_queryset(model).none()
        return cls.current_queryset(model).filter(pk__in=ids)

    @classmethod
    def contains_object(cls, obj) -> bool:
        if obj is None or not getattr(obj, "pk", None):
            return False
        return cls.current_queryset(type(obj)).filter(pk=obj.pk).exists()


class InventoryDocumentPolicy:
    """Object-level policy for receipt/issue posting, voiding and deletion."""

    @staticmethod
    def _permission_for(document, action: str) -> str:
        opts = document._meta
        return f"{opts.app_label}.{action}_{opts.model_name}"

    @staticmethod
    def _deny_not_visible(
        message: str = "Không tìm thấy chứng từ kho hoặc không có quyền thao tác.",
    ) -> PolicyResult:
        return PolicyResult.deny(
            ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE,
            message,
            details={},
            effective_scope_level="INVENTORY",
            scope_source="inventory_policy",
        )

    @classmethod
    def _has_inventory_role(cls, user) -> bool:
        if not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_superuser", False):
            return True
        return has_role(user, "thu_kho") or has_role(user, "ban_giam_doc")

    @classmethod
    def can_view_document(cls, user, document) -> PolicyResult:
        if not getattr(user, "is_authenticated", False):
            return cls._deny_not_visible()
        if not isinstance(document, (PhieuNhap, PhieuXuat)):
            return cls._deny_not_visible()
        if document is None or not InventoryScopePolicy.contains_object(document):
            return cls._deny_not_visible()
        if not cls._has_inventory_role(user):
            return cls._deny_not_visible()
        if user.has_perm(cls._permission_for(document, "view")) or user.has_perm(
            cls._permission_for(document, "change")
        ):
            return PolicyResult.allow(
                message="Được xem chứng từ kho.",
                effective_scope_level="INVENTORY",
                scope_source="inventory_policy",
            )
        return cls._deny_not_visible()

    @classmethod
    def can_change_document(cls, user, document) -> PolicyResult:
        if not getattr(user, "is_authenticated", False):
            return cls._deny_not_visible()
        if not isinstance(document, (PhieuNhap, PhieuXuat)):
            return cls._deny_not_visible()
        if document is None or not InventoryScopePolicy.contains_object(document):
            return cls._deny_not_visible()
        if not cls._has_inventory_role(user):
            return cls._deny_not_visible()
        if not user.has_perm(cls._permission_for(document, "change")):
            return cls._deny_not_visible()
        return PolicyResult.allow(
            message="Được cập nhật chứng từ kho.",
            effective_scope_level="INVENTORY",
            scope_source="inventory_policy",
        )

    @classmethod
    def can_delete_document(cls, user, document) -> PolicyResult:
        change_result = cls.can_change_document(user, document)
        if not change_result.allowed:
            return change_result
        if not user.has_perm(cls._permission_for(document, "delete")):
            return cls._deny_not_visible()
        draft_state = type(document).TrangThai.DRAFT
        if document.trang_thai != draft_state:
            return PolicyResult.deny(
                ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE,
                "Chỉ được xóa chứng từ kho còn ở trạng thái Nháp.",
                details={},
                effective_scope_level="INVENTORY",
                scope_source="inventory_policy",
            )
        return PolicyResult.allow(
            message="Được xóa chứng từ kho nháp.",
            effective_scope_level="INVENTORY",
            scope_source="inventory_policy",
        )

    @classmethod
    def can_post_document(cls, user, document) -> PolicyResult:
        change_result = cls.can_change_document(user, document)
        if not change_result.allowed:
            return change_result
        draft_state = type(document).TrangThai.DRAFT
        if document.trang_thai != draft_state:
            return PolicyResult.deny(
                ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE,
                "Chỉ chứng từ kho Nháp mới được ghi sổ.",
                details={},
                effective_scope_level="INVENTORY",
                scope_source="inventory_policy",
            )
        return PolicyResult.allow(
            message="Được ghi sổ chứng từ kho.",
            effective_scope_level="INVENTORY",
            scope_source="inventory_policy",
        )

    @classmethod
    def can_void_document(cls, user, document) -> PolicyResult:
        change_result = cls.can_change_document(user, document)
        if not change_result.allowed:
            return change_result
        posted_state = type(document).TrangThai.POSTED
        if document.trang_thai != posted_state:
            return PolicyResult.deny(
                ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE,
                "Chỉ chứng từ kho đã ghi sổ mới được hủy/reversal.",
                details={},
                effective_scope_level="INVENTORY",
                scope_source="inventory_policy",
            )
        return PolicyResult.allow(
            message="Được hủy/reversal chứng từ kho.",
            effective_scope_level="INVENTORY",
            scope_source="inventory_policy",
        )


__all__ = ["InventoryScopePolicy", "InventoryDocumentPolicy"]
