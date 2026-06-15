from datetime import date
from unittest.mock import patch

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission, User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from main.models import AuditLog
from users.admin import NhanVienAdmin
from users.models import NhanVien
from users.views import export_ly_lich_pdf


class UserExportAuditTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            "staffuser",
            "staff@test.com",
            "password",
            is_staff=True,
        )
        permission = Permission.objects.get(codename="view_nhanvien")
        self.staff_user.user_permissions.add(permission)
        self.nhan_vien = NhanVien.objects.create(
            ho_ten="PDF Tester",
            ngay_sinh=date(1998, 1, 1),
            gioi_tinh="M",
            so_cccd="000000000000",
            sdt_chinh="+84900000000",
            email="pdf.tester@example.com",
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )

    @patch("users.views.HTML.write_pdf", return_value=b"fake-pdf")
    def test_employee_profile_export_records_audit_log(self, _mock_pdf):
        request = self.factory.post(
            reverse("users:export-ly-lich", args=[self.nhan_vien.id]),
            {
                "bao_gom_anh_the": "on",
                "bao_gom_thong_tin_ca_nhan": "on",
            },
        )
        request.user = self.staff_user
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        request.META["HTTP_USER_AGENT"] = "phase0-test"

        response = export_ly_lich_pdf(request, self.nhan_vien.id)

        self.assertEqual(response.status_code, 200)
        audit_log = AuditLog.objects.filter(
            user=self.staff_user,
            module="users",
            model_name="NhanVien",
            object_id=str(self.nhan_vien.id),
            note="Export PDF ly lich nhan vien",
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.ip_address, "127.0.0.1")
        self.assertEqual(audit_log.user_id, self.staff_user.id)
        self.assertEqual(audit_log.changes["query_params"], {})
        self.assertIsNotNone(audit_log.timestamp)


class UserAdminExportAuditTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_superuser(
            "admin",
            "admin@example.com",
            "password",
        )
        self.nhan_vien = NhanVien.objects.create(
            ho_ten="Nhan vien in ho so",
            ngay_sinh=date(1990, 1, 1),
            gioi_tinh="M",
            so_cccd="123456789012",
            sdt_chinh="+84912345678",
            email="hoso@example.com",
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )
        self.admin = NhanVienAdmin(NhanVien, AdminSite())

    def test_admin_print_profile_records_audit_log(self):
        request = self.factory.get(f"/admin/users/nhanvien/{self.nhan_vien.id}/print-profile/")
        request.user = self.admin_user
        request.META["REMOTE_ADDR"] = "127.0.0.2"
        request.META["HTTP_USER_AGENT"] = "phase0-admin-test"

        response = self.admin.print_profile_view(request, self.nhan_vien.id)

        self.assertEqual(response.status_code, 200)
        audit_log = AuditLog.objects.filter(
            user=self.admin_user,
            module="users",
            model_name="NhanVien",
            object_id=str(self.nhan_vien.id),
            note="Export print ho so nhan vien",
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.ip_address, "127.0.0.2")
        self.assertEqual(audit_log.user_id, self.admin_user.id)
        self.assertEqual(audit_log.changes["query_params"], {})
        self.assertIsNotNone(audit_log.timestamp)


class UserExportOptionsPermissionTest(TestCase):
    def setUp(self):
        self.user_without_permission = User.objects.create_user(
            "hr_no_perm",
            "hr-no-perm@example.com",
            "password",
        )
        self.user_with_permission = User.objects.create_user(
            "hr_with_perm",
            "hr-with-perm@example.com",
            "password",
        )
        permission = Permission.objects.get(codename="view_nhanvien")
        self.user_with_permission.user_permissions.add(permission)
        self.nhan_vien = NhanVien.objects.create(
            ho_ten="Nhân viên bảo vệ export option",
            ma_nhan_vien="NV-HR-OPTION-01",
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )
        self.url = reverse("users:export-ly-lich-options", args=[self.nhan_vien.pk])

    def test_export_options_requires_view_employee_permission(self):
        self.client.force_login(self.user_without_permission)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_export_options_allows_user_with_view_employee_permission(self):
        self.client.force_login(self.user_with_permission)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.nhan_vien.ho_ten)
