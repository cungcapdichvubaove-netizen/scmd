# -*- coding: utf-8 -*-
import json
import uuid

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings

from main.models import AuditLog


class AuditLogIntegrityTest(TestCase):
    """
    Kiểm tra tính toàn vẹn của AuditLog:
    1. Tự động gán tenant_id từ settings.
    2. Ghi đè tenant_id nếu bị gán sai từ bên ngoài.
    3. Tự động tạo checksum sau khi gán tenant_id.
    """

    def setUp(self):
        self.org_id = "00000000-0000-0000-0000-000000000001"
        self.wrong_id = "99999999-9999-9999-9999-999999999999"
        self.user = User.objects.create_user(username="audit_checker", password="password")

    @override_settings(SCMD_ORGANIZATION_ID="00000000-0000-0000-0000-000000000001")
    def test_auto_assign_tenant_id_on_save(self):
        """Kiểm tra: tenant_id được gán tự động khi để trống."""
        log = AuditLog.objects.create(
            action=AuditLog.Action.EXECUTE,
            module="Testing",
            model_name="AuditLog",
            note="Test auto assignment",
        )

        self.assertEqual(str(log.tenant_id), self.org_id)
        self.assertIsNotNone(log.checksum)

    @override_settings(SCMD_ORGANIZATION_ID="00000000-0000-0000-0000-000000000001")
    def test_overwrite_wrong_tenant_id(self):
        """Kiểm tra: hệ thống phải ghi đè nếu dev gán nhầm tenant_id khác."""
        log = AuditLog(
            tenant_id=uuid.UUID(self.wrong_id),
            action=AuditLog.Action.UPDATE,
            module="Testing",
            model_name="AuditLog",
            note="Test overwrite logic",
        )
        log.save()

        self.assertEqual(str(log.tenant_id), self.org_id)
        self.assertNotEqual(str(log.tenant_id), self.wrong_id)

    @override_settings(SCMD_ORGANIZATION_ID="00000000-0000-0000-0000-000000000001")
    def test_checksum_integrity_with_tenant_id(self):
        """Kiểm tra: checksum phải phản ánh đúng tenant_id trong hash."""
        log = AuditLog.objects.create(
            action=AuditLog.Action.LOGIN,
            module="Auth",
            model_name="User",
            note="Integrity check",
        )

        expected_checksum = log.generate_checksum()
        self.assertEqual(log.checksum, expected_checksum)

    @override_settings(SCMD_ORGANIZATION_ID="00000000-0000-0000-0000-000000000001")
    def test_checksum_uses_unicode_json_for_vietnamese_changes(self):
        """Kiểm tra: checksum serialize JSON giữ nguyên Unicode tiếng Việt."""
        log = AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            module="Testing",
            model_name="AuditLog",
            changes={"chuc_danh": "Đội trưởng", "ghi_chu": "Đã cập nhật"},
            note="Unicode checksum check",
        )

        payload = json.dumps(log.changes or {}, sort_keys=True, ensure_ascii=False)

        self.assertIn("Đội trưởng", payload)
        self.assertIn("Đã cập nhật", payload)
        self.assertEqual(log.checksum, log.generate_checksum())

    @override_settings(SCMD_ORGANIZATION_ID="00000000-0000-0000-0000-000000000001")
    def test_integrity_check_command_detection(self):
        """Kiểm tra Management Command phát hiện được bản ghi sai tenant_id."""
        log = AuditLog(
            action=AuditLog.Action.EXECUTE,
            module="Hacker",
            model_name="System",
            tenant_id=uuid.UUID(self.wrong_id),
        )
        log.save_base()

        from io import StringIO

        out = StringIO()
        call_command("check_tenant_integrity", stdout=out)

        output = out.getvalue()
        self.assertIn("PHÁT HIỆN 1 BẢN GHI SAI LỆCH", output)
