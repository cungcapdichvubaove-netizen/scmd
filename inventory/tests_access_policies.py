# -*- coding: utf-8 -*-
"""Regression tests for inventory access-scope hardening."""

import uuid

from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test import TestCase
from rolepermissions.roles import assign_role

from core.managers import TenantAwareManager
from inventory.access_policies import InventoryDocumentPolicy, InventoryScopePolicy
from inventory.models import LoaiVatTu, PhieuNhap


class InventoryAccessPolicyTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="inventory-policy-user")
        self.document = PhieuNhap.objects.create(ma_phieu="PN-SCOPE-001")

    def _grant_receipt_change(self):
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="inventory",
                codename__in=["view_phieunhap", "change_phieunhap", "delete_phieunhap"],
            )
        )

    def test_post_document_requires_inventory_permission(self):
        result = InventoryDocumentPolicy.can_post_document(self.user, self.document)
        self.assertFalse(result.allowed)
        self.assertEqual(result.error_code, "ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE")

    def test_post_document_allows_scoped_draft_with_permission(self):
        self._grant_receipt_change()
        assign_role(self.user, "thu_kho")
        result = InventoryDocumentPolicy.can_post_document(self.user, self.document)
        self.assertTrue(result.allowed)

    def test_post_document_denies_user_without_inventory_role_even_with_permission(self):
        self._grant_receipt_change()

        result = InventoryDocumentPolicy.can_post_document(self.user, self.document)

        self.assertFalse(result.allowed)
        self.assertEqual(result.error_code, "ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE")


    def test_document_policy_denies_unsupported_inventory_object_without_crashing(self):
        self._grant_receipt_change()
        assign_role(self.user, "thu_kho")
        unsupported_object = LoaiVatTu.objects.create(ten_loai="Unsupported policy object")

        change_result = InventoryDocumentPolicy.can_change_document(self.user, unsupported_object)
        post_result = InventoryDocumentPolicy.can_post_document(self.user, unsupported_object)
        void_result = InventoryDocumentPolicy.can_void_document(self.user, unsupported_object)

        self.assertFalse(change_result.allowed)
        self.assertFalse(post_result.allowed)
        self.assertFalse(void_result.allowed)
        self.assertEqual(change_result.error_code, "ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE")

    def test_tenant_aware_manager_hides_cross_organization_residue(self):
        category = LoaiVatTu.objects.create(ten_loai="Residue check")
        foreign_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE inventory_loaivattu SET tenant_id = %s WHERE id = %s",
                [str(foreign_tenant_id), category.pk],
            )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tenant_id FROM inventory_loaivattu WHERE id = %s",
                [category.pk],
            )
            db_tenant_id = cursor.fetchone()[0]

        self.assertNotEqual(str(db_tenant_id), str(settings.SCMD_ORGANIZATION_ID))
        self.assertIsInstance(LoaiVatTu.objects, TenantAwareManager)
        self.assertFalse(LoaiVatTu.objects.filter(pk=category.pk).exists())
        self.assertFalse(LoaiVatTu.objects.for_current().filter(pk=category.pk).exists())
        self.assertFalse(InventoryScopePolicy.contains_object(category))


class InventoryAdminScopeManagerContractTest(TestCase):
    def test_selected_from_queryset_re_reads_selected_rows_through_current_org_manager(self):
        visible = LoaiVatTu.objects.create(ten_loai="Visible selected category")
        residue = LoaiVatTu.objects.create(ten_loai="Cross org selected category")
        foreign_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE inventory_loaivattu SET tenant_id = %s WHERE id = %s",
                [str(foreign_tenant_id), residue.pk],
            )

        potentially_contaminated_queryset = LoaiVatTu._base_manager.filter(
            pk__in=[visible.pk, residue.pk]
        )
        selected = LoaiVatTu.objects.selected_from_queryset(potentially_contaminated_queryset)

        self.assertIn(visible.pk, set(selected.values_list("pk", flat=True)))
        self.assertNotIn(residue.pk, set(selected.values_list("pk", flat=True)))

    def test_inventory_admin_bulk_actions_do_not_call_scope_policy_queryset_directly(self):
        from pathlib import Path

        source = Path("inventory/admin.py").read_text(encoding="utf-8")
        self.assertNotIn("InventoryScopePolicy.scope_queryset", source)
        self.assertNotIn("def _audit_inventory_admin_action", source)
        self.assertNotIn("_audit_inventory_admin_action(", source)
        self.assertNotIn("AuditLog.objects.create(", source)
        self.assertIn(".objects.selected_from_queryset(queryset)", source)
        self.assertIn("record_inventory_admin_audit_action(", source)
