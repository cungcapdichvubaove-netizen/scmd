# -*- coding: utf-8 -*-
"""Regression tests for HR admin audit logging."""

from __future__ import annotations

from uuid import UUID

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings

from main.models import AuditLog
from users.admin import NhanVienAdmin
from users.models import NhanVien


ORG_ID = UUID("00000000-0000-0000-0000-000000000324")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class NhanVienAdminAuditTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            username="hr-admin-audit",
            password="password",
            email="hr-admin-audit@example.com",
        )
        self.staff_user = User.objects.create_user(username="hr-admin-target")
        self.staff = self.staff_user.nhan_vien
        self.staff.ma_nhan_vien = "NV-HR-AUDIT"
        self.staff.ho_ten = "Nhân viên audit"
        self.staff.save()
        self.model_admin = NhanVienAdmin(NhanVien, AdminSite())
        self.factory = RequestFactory()

    def test_save_model_creates_audit_log(self):
        request = self.factory.post("/admin/users/nhanvien/%s/change/" % self.staff.pk)
        request.user = self.admin_user
        self.staff.ho_ten = "Nhân viên audit đã sửa"

        self.model_admin.save_model(request, self.staff, form=None, change=True)

        audit = AuditLog.objects.filter(
            module="users",
            model_name="NhanVien",
            object_id=str(self.staff.pk),
            action=AuditLog.Action.UPDATE,
        ).latest("timestamp")
        self.assertEqual(audit.user, self.admin_user)
        self.assertEqual(audit.changes["after"]["ho_ten"], "Nhân viên audit đã sửa")
        self.assertIn("before", audit.changes)
