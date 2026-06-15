# -*- coding: utf-8 -*-
from django.test import TestCase

from main.decorators import application_audit_log
from main.models import AuditLog


class ApplicationAuditLogDecoratorTests(TestCase):
    def test_object_id_field_resolves_from_kwargs(self):
        @application_audit_log(
            module="accounting",
            model_name="BangLuongThang",
            action=AuditLog.Action.ACCESS,
            object_id_field="bang_luong",
        )
        def execute(*, bang_luong, tenant_id=None):
            return {"ok": True}

        execute(bang_luong=123, tenant_id="00000000-0000-0000-0000-000000000001")

        log = AuditLog.objects.get(
            model_name="BangLuongThang",
            action=AuditLog.Action.ACCESS,
        )
        self.assertEqual(log.object_id, "123")
        self.assertEqual(log.status, "SUCCESS")

    def test_object_id_resolver_is_supported(self):
        @application_audit_log(
            module="accounting",
            model_name="ChiTietLuong",
            object_id_resolver=lambda *args, **kwargs: kwargs["payroll_id"],
        )
        def execute(*, payroll_id, tenant_id=None):
            return {"ok": True}

        execute(payroll_id=456, tenant_id="00000000-0000-0000-0000-000000000001")

        log = AuditLog.objects.get(model_name="ChiTietLuong", object_id="456")
        self.assertEqual(log.status, "SUCCESS")

    def test_failure_is_logged_and_reraised(self):
        @application_audit_log(
            module="operations",
            model_name="KiemTraQuanSo",
            object_id_field="check_id",
        )
        def execute(*, check_id, tenant_id=None):
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            execute(check_id="abc-123", tenant_id="00000000-0000-0000-0000-000000000001")

        log = AuditLog.objects.get(model_name="KiemTraQuanSo", object_id="abc-123")
        self.assertEqual(log.status, "FAILED")
        self.assertIn("boom", log.note)
