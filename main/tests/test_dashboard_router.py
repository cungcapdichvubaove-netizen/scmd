# -*- coding: utf-8 -*-
from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from rolepermissions.roles import assign_role

from main.dashboard_router import DashboardRouter
from users.models import ChucDanh, PhongBan

class DashboardRouterTests(TestCase):
    def test_superuser_routes_to_admin(self):
        user = User.objects.create_superuser("admin", "admin@test.com", "password")
        decision = DashboardRouter.resolve_decision(user)
        self.assertEqual(decision.route_name, "admin:index")
        self.assertTrue(decision.matched)
        self.assertEqual(decision.source, "superuser")

    def test_ban_giam_doc_group_routes_to_executive_dashboard(self):
        user = User.objects.create_user("ceo", "ceo@test.com", "password")
        group, _ = Group.objects.get_or_create(name="BanGiamDoc")
        user.groups.add(group)

        decision = DashboardRouter.resolve_decision(user)
        self.assertEqual(decision.route_name, "dashboard:main")
        self.assertEqual(decision.source, "django-group")

    def test_kho_group_routes_to_inventory_dashboard(self):
        user = User.objects.create_user("kho", "kho@test.com", "password")
        group, _ = Group.objects.get_or_create(name="Kho")
        user.groups.add(group)

        decision = DashboardRouter.resolve_decision(user)
        self.assertEqual(decision.route_name, "inventory:dashboard")

    def test_thu_kho_role_routes_to_inventory_dashboard(self):
        user = User.objects.create_user("warehouse", "warehouse@test.com", "password")
        assign_role(user, "thu_kho")

        decision = DashboardRouter.resolve_decision(user)

        self.assertEqual(decision.route_name, "inventory:dashboard")
        self.assertEqual(decision.source, "rolepermissions")

    def test_ke_toan_role_cannot_access_inventory_dashboard(self):
        user = User.objects.create_user("accountant", "accountant@test.com", "password")
        assign_role(user, "ke_toan")

        self.assertFalse(DashboardRouter.user_can_access(user, "inventory:dashboard"))
        self.assertTrue(DashboardRouter.user_can_access(user, "accounting:dashboard"))

    def test_unmapped_user_falls_back_to_mobile_dashboard(self):
        """User không có group sẽ mặc định xem dashboard mobile của nhân viên bảo vệ."""
        user = User.objects.create_user("guard", "guard@test.com", "password")
        decision = DashboardRouter.resolve_decision(user)
        self.assertEqual(decision.route_name, "main:access_pending")
        self.assertFalse(decision.matched)
    def test_dashboard_access_allows_matching_workspace_group(self):
        user = User.objects.create_user("ops", "ops@test.com", "password")
        group, _ = Group.objects.get_or_create(name="Phòng Nghiệp vụ")
        user.groups.add(group)

        self.assertTrue(DashboardRouter.user_can_access(user, "operations:dashboard_vanhanh"))
        self.assertTrue(DashboardRouter.user_can_access(user, "operations:dashboard_xep_lich"))
        self.assertFalse(DashboardRouter.user_can_access(user, "accounting:dashboard"))

    def test_dashboard_access_denies_unmapped_authenticated_user(self):
        user = User.objects.create_user("unmapped", "unmapped@test.com", "password")

        self.assertFalse(DashboardRouter.user_can_access(user, "dashboard:main"))
        self.assertFalse(DashboardRouter.user_can_access(user, "operations:dashboard_vanhanh"))

    def test_superuser_can_access_all_registered_dashboards(self):
        user = User.objects.create_superuser("root", "root@test.com", "password")

        for route_name in DashboardRouter.DASHBOARD_ACCESS_RULES:
            self.assertTrue(DashboardRouter.user_can_access(user, route_name))

    def test_guard_title_takes_priority_over_operations_department(self):
        user = User.objects.create_user("guard-profile", "guard-profile@test.com", "password")
        phong_ban = PhongBan.objects.create(ten_phong_ban="Phòng Nghiệp vụ")
        chuc_danh = ChucDanh.objects.create(ten_chuc_danh="Guard")

        nhan_vien = user.nhan_vien
        nhan_vien.ho_ten = "Guard Profile"
        nhan_vien.ngay_sinh = date(2000, 1, 1)
        nhan_vien.gioi_tinh = "M"
        nhan_vien.sdt_chinh = "+84900000001"
        nhan_vien.phong_ban = phong_ban
        nhan_vien.chuc_danh = chuc_danh
        nhan_vien.save()

        decision = DashboardRouter.resolve_decision(user)
        self.assertEqual(decision.route_name, "operations:mobile_dashboard")
        self.assertEqual(decision.source, "employee-profile")

    def test_guard_group_is_preferred_over_operations_group(self):
        user = User.objects.create_user("guard-group", "guard-group@test.com", "password")
        guard_group, _ = Group.objects.get_or_create(name="Guard")
        operations_group, _ = Group.objects.get_or_create(name="Phòng Nghiệp vụ")
        user.groups.add(guard_group, operations_group)

        decision = DashboardRouter.resolve_decision(user)
        self.assertEqual(decision.route_name, "operations:mobile_dashboard")
        self.assertEqual(decision.source, "django-group")

    def test_business_guard_is_redirected_away_from_admin_root(self):
        user = User.objects.create_user("guard-admin-root", "guard-admin-root@test.com", "password", is_staff=True)
        phong_ban = PhongBan.objects.create(ten_phong_ban="Phòng Nghiệp vụ")
        chuc_danh = ChucDanh.objects.create(ten_chuc_danh="Guard")

        nhan_vien = user.nhan_vien
        nhan_vien.ho_ten = "Guard Admin Root"
        nhan_vien.ngay_sinh = date(2000, 1, 2)
        nhan_vien.gioi_tinh = "M"
        nhan_vien.sdt_chinh = "+84900000002"
        nhan_vien.phong_ban = phong_ban
        nhan_vien.chuc_danh = chuc_danh
        nhan_vien.save()

        self.client.force_login(user)
        response = self.client.get("/admin/")

        self.assertRedirects(response, reverse("operations:mobile_dashboard"))
        self.assertFalse(DashboardRouter.user_can_access_admin_console(user))
