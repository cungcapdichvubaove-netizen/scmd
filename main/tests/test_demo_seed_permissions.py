# -*- coding: utf-8 -*-
"""Runtime contract for KTC Việt Nam demo dashboard accounts."""

from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rolepermissions.checkers import has_permission, has_role

from clients.access_policies import SiteVisibilityPolicy
from users.models_assignment import NhanVienRegionAssignment

from main.dashboard_router import DashboardRouter
from main.management.commands.seed_scmd_demo import DASHBOARD_ACCOUNTS, DEFAULT_DEMO_PASSWORD


EXPECTED_WORKSPACE_BY_ROLE = {
    "ban_giam_doc": "dashboard:main",
    "nghiep_vu": "operations:dashboard_vanhanh",
    "quan_ly_vung": "operations:dashboard_vanhanh",
    "doi_truong": "operations:dashboard_vanhanh",
    "nhan_vien_bao_ve": "operations:mobile_dashboard",
    "ke_toan": "accounting:dashboard",
    "thu_kho": "inventory:dashboard",
    "nhan_su": "users:dashboard",
    "nhan_vien_kinh_doanh": "clients:dashboard_crm",
    "thanh_tra": "inspection:dashboard",
}


class DemoSeedDashboardPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "seed_scmd_demo",
            profile="light",
            password=DEFAULT_DEMO_PASSWORD,
            stdout=StringIO(),
        )

    def test_all_dashboard_accounts_login_route_and_open_workspace(self):
        for username, _full_name, _title, _department, role, is_staff, _branch_key in DASHBOARD_ACCOUNTS:
            with self.subTest(username=username):
                self.assertTrue(self.client.login(username=username, password=DEFAULT_DEMO_PASSWORD))
                user = User.objects.get(username=username)
                self.assertEqual(user.is_staff, is_staff)
                self.assertTrue(has_role(user, role))

                expected_route = EXPECTED_WORKSPACE_BY_ROLE[role]
                decision = DashboardRouter.resolve_decision(user)
                self.assertEqual(decision.route_name, expected_route)
                self.assertTrue(DashboardRouter.user_can_access(user, expected_route))

                response = self.client.get(reverse(expected_route))
                self.assertEqual(response.status_code, 200)
                self.client.logout()

    def test_guard_demo_accounts_login_and_resolve_to_mobile_workspace(self):
        for username in ("baove.hn001", "baove.dn001", "baove.sg001"):
            with self.subTest(username=username):
                self.assertTrue(self.client.login(username=username, password=DEFAULT_DEMO_PASSWORD))
                user = User.objects.get(username=username)
                self.assertFalse(user.is_staff)
                self.assertTrue(has_role(user, "nhan_vien_bao_ve"))
                self.assertTrue(has_permission(user, "xem_lich_truc_ca_nhan"))
                decision = DashboardRouter.resolve_decision(user)
                self.assertEqual(decision.route_name, "operations:mobile_dashboard")
                response = self.client.get(reverse("operations:mobile_dashboard"))
                self.assertEqual(response.status_code, 200)
                self.client.logout()

    def test_chihuy_dn01_core_role_and_permissions(self):
        user = User.objects.get(username="chihuy.dn01")
        self.assertTrue(has_role(user, "doi_truong"))
        self.assertTrue(has_permission(user, "giao_ca_truc"))
        self.assertTrue(user.has_perm("operations.view_phancongcatruc"))
        self.assertTrue(user.has_perm("operations.add_phancongcatruc"))
        self.assertTrue(user.has_perm("operations.change_phancongcatruc"))
        self.assertTrue(user.has_perm("operations.delete_phancongcatruc"))
        self.assertTrue(user.has_perm("operations.view_chamcong"))
        self.assertTrue(user.has_perm("operations.view_baocaosuco"))

    def test_bgd_schedule_contract_is_view_only(self):
        user = User.objects.get(username="tonggiamdoc.hanoi")
        self.assertTrue(has_role(user, "ban_giam_doc"))
        self.assertFalse(has_permission(user, "giao_ca_truc"))
        self.assertTrue(user.has_perm("operations.view_phancongcatruc"))
        self.assertFalse(user.has_perm("operations.add_phancongcatruc"))
        self.assertFalse(user.has_perm("operations.change_phancongcatruc"))
        self.assertFalse(user.has_perm("operations.delete_phancongcatruc"))


    def test_branch_directors_are_region_managers_not_company_bgd(self):
        for username, expected_region_text in (
            ("giamdocchinhanh.danang", "Đà Nẵng"),
            ("giamdocchinhanh.saigon", "Sài Gòn"),
        ):
            with self.subTest(username=username):
                user = User.objects.select_related("nhan_vien__chuc_danh__nhom_quyen").get(username=username)
                group_names = set(user.groups.values_list("name", flat=True))
                self.assertIn("Quản lý vùng", group_names)
                self.assertNotIn("Ban Giám đốc", group_names)
                self.assertTrue(has_role(user, "quan_ly_vung"))
                self.assertFalse(has_role(user, "ban_giam_doc"))
                self.assertEqual(user.nhan_vien.chuc_danh.nhom_quyen.name, "Quản lý vùng")

                visible_names = list(SiteVisibilityPolicy.managed_sites(user).values_list("ten_muc_tieu", flat=True))
                self.assertTrue(visible_names)
                self.assertTrue(all(expected_region_text in name for name in visible_names))

    def test_central_operations_accounts_are_nationwide_scope(self):
        all_demo_regions = {"Hà Nội", "Đà Nẵng", "Sài Gòn"}
        for username in ("truongvanhanh.hanoi", "dieuphoi.trungtam"):
            with self.subTest(username=username):
                user = User.objects.get(username=username)
                self.assertTrue(has_role(user, "nghiep_vu"))
                self.assertTrue(has_permission(user, "giao_ca_truc"))
                decision = DashboardRouter.resolve_decision(user)
                self.assertEqual(decision.route_name, "operations:dashboard_vanhanh")

                site_names = list(SiteVisibilityPolicy.managed_sites(user).values_list("ten_muc_tieu", flat=True))
                self.assertTrue(site_names)
                for region_text in all_demo_regions:
                    self.assertTrue(any(region_text in name for name in site_names), f"{username} missing {region_text} scope")
                self.assertFalse(
                    NhanVienRegionAssignment.objects.filter(
                        nhan_vien=user.nhan_vien,
                        reason__contains="DEMO-KTCVN",
                        status=NhanVienRegionAssignment.Status.ACTIVE,
                    ).exists(),
                    "Central operations scope must not be faked as one Hà Nội region assignment.",
                )

    def test_admin_cta_helper_requires_staff_console_access(self):
        from main.dashboard_cta import admin_url_if_permitted

        non_staff_user = User.objects.get(username="nhansu.hanoi")
        staff_user = User.objects.get(username="truongnhansu.hanoi")
        self.assertFalse(non_staff_user.is_staff)
        self.assertTrue(non_staff_user.has_perm("users.view_nhanvien"))
        self.assertIsNone(
            admin_url_if_permitted(non_staff_user, "admin:users_nhanvien_changelist", "users.view_nhanvien")
        )
        self.assertTrue(staff_user.is_staff)
        self.assertIsNotNone(
            admin_url_if_permitted(staff_user, "admin:users_nhanvien_changelist", "users.view_nhanvien")
        )

    def test_department_dashboard_core_permissions_are_seeded(self):
        checks = {
            "truongnhansu.hanoi": ["users.view_nhanvien", "users.add_nhanvien", "users.view_hopdonglaodong", "users.view_donnghiphep"],
            "ketoantruong.hanoi": ["accounting.view_bangluongthang", "accounting.view_tamungluong", "accounting.view_khoankhautrunhanvien"],
            "thukho.hanoi": ["inventory.view_vattu", "inventory.view_phieunhap", "inventory.view_phieuxuat", "inventory.view_phieuthuhoi"],
            "truongkinhdoanh.hanoi": ["clients.view_khachhangtiemnang", "clients.view_cohoikinhdoanh", "clients.view_hopdong"],
            "thanhtra.hanoi": ["inspection.view_dotthanhtra", "inspection.view_bienbanthanhtra", "inspection.view_bienbanvipham", "inspection.view_ghinhantuantra"],
        }
        for username, perm_codes in checks.items():
            with self.subTest(username=username):
                user = User.objects.get(username=username)
                for perm_code in perm_codes:
                    self.assertTrue(user.has_perm(perm_code), f"{username} missing {perm_code}")
