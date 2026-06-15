# -*- coding: utf-8 -*-
"""Regression tests for centralized admin audit helpers."""

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from main.audit_utils import record_admin_audit_action as compatibility_record_admin_audit_action
from main.models import AuditLog
from main.services.audit_service import (
    record_admin_audit_action,
    record_inventory_admin_audit_action,
)


class AdminAuditServiceTests(TestCase):
    def _request(self, user):
        request = RequestFactory(HTTP_USER_AGENT="SCMD-Pro-Test-Agent").post(
            "/admin/inventory/"
        )
        request.user = user
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        return request

    def test_record_admin_audit_action_persists_request_metadata(self):
        user = User.objects.create_user(
            username="audit-admin", email="audit-admin@scmd.local", password="password"
        )
        request = self._request(user)

        record_admin_audit_action(
            request,
            action=AuditLog.Action.UPDATE,
            module="inventory",
            model_name="VatTu",
            object_id="42",
            note="Central admin audit helper test",
            changes={"field": "value"},
        )

        log = AuditLog.objects.get(model_name="VatTu", object_id="42")
        self.assertEqual(log.user, user)
        self.assertEqual(log.action, AuditLog.Action.UPDATE)
        self.assertEqual(log.module, "inventory")
        self.assertEqual(log.changes, {"field": "value"})
        self.assertEqual(log.ip_address, "127.0.0.1")
        self.assertEqual(log.user_agent, "SCMD-Pro-Test-Agent")
        self.assertEqual(log.status, "SUCCESS")
        self.assertIsNotNone(log.checksum)

    def test_inventory_admin_audit_wrapper_sets_inventory_module(self):
        user = User.objects.create_user(
            username="inventory-audit-admin",
            email="inventory-audit-admin@scmd.local",
            password="password",
        )
        request = self._request(user)

        record_inventory_admin_audit_action(
            request,
            action=AuditLog.Action.CREATE,
            model_name="PhieuNhap",
            object_id="PN-001",
            note="Inventory admin service wrapper test",
            changes={"status": "DRAFT"},
        )

        log = AuditLog.objects.get(model_name="PhieuNhap", object_id="PN-001")
        self.assertEqual(log.module, "inventory")
        self.assertEqual(log.action, AuditLog.Action.CREATE)
        self.assertEqual(log.changes, {"status": "DRAFT"})
        self.assertEqual(log.user, user)

    def test_audit_utils_re_exports_admin_audit_helper_for_backward_compatibility(self):
        self.assertIs(compatibility_record_admin_audit_action, record_admin_audit_action)
