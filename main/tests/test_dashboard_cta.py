# -*- coding: utf-8 -*-
"""Dashboard CTA authorization regression tests."""

from pathlib import Path

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from rolepermissions.roles import assign_role

from main.dashboard_cta import admin_url_if_permitted, can_render_admin_cta
from main.services.operations_ux import AdminOperationsUXProvider


class DashboardCTAAdminGateTests(TestCase):
    def test_superuser_sees_admin_url(self):
        user = User.objects.create_superuser("root", "root@example.com", "password")

        url = admin_url_if_permitted(user, "admin:users_nhanvien_changelist", "users.view_nhanvien")

        self.assertTrue(can_render_admin_cta(user, "users.view_nhanvien"))
        self.assertEqual(url, "/admin/users/nhanvien/")

    def test_staff_technical_user_with_permission_sees_admin_url(self):
        user = User.objects.create_user("tech", "tech@example.com", "password", is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename="view_nhanvien"))

        url = admin_url_if_permitted(user, "admin:users_nhanvien_changelist", "users.view_nhanvien")

        self.assertEqual(url, "/admin/users/nhanvien/")

    def test_business_role_staff_does_not_get_fake_admin_url(self):
        user = User.objects.create_user("ops", "ops@example.com", "password", is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename="view_baocaosuco"))
        assign_role(user, "doi_truong")

        url = admin_url_if_permitted(
            user,
            "admin:operations_baocaosuco_changelist",
            "operations.view_baocaosuco",
        )

        self.assertFalse(can_render_admin_cta(user, "operations.view_baocaosuco"))
        self.assertIsNone(url)

    def test_authenticated_non_staff_user_with_permission_does_not_get_admin_url(self):
        user = User.objects.create_user("business", "business@example.com", "password")
        user.user_permissions.add(Permission.objects.get(codename="view_nhanvien"))

        url = admin_url_if_permitted(user, "admin:users_nhanvien_changelist", "users.view_nhanvien")

        self.assertIsNone(url)

    def test_operations_ux_header_does_not_emit_admin_links_for_business_role(self):
        user = User.objects.create_user("ops_header", "ops-header@example.com", "password", is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename="view_baocaosuco"))
        assign_role(user, "doi_truong")

        header = AdminOperationsUXProvider.home_header_for_user(user, {"scope:operations", "doi_truong"})

        self.assertFalse(any(action["url"].startswith("/admin/") for action in header["actions"]))

    def test_business_templates_do_not_hardcode_admin_urls(self):
        project_root = Path(__file__).resolve().parents[2]
        template_paths = [
            "clients/templates/clients/pipeline.html",
            "operations/templates/operations/danh_sach_muc_tieu.html",
            "operations/templates/operations/chi_tiet_muc_tieu.html",
            "reports/templates/reports/bao_cao_su_co.html",
        ]

        for relative_path in template_paths:
            template = (project_root / relative_path).read_text(encoding="utf-8")
            self.assertNotIn('/admin/', template, msg=relative_path)
