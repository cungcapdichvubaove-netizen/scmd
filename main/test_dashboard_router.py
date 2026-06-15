from django.contrib.auth.models import Group, User
from django.test import TestCase

from main.dashboard_router import DashboardRouter


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

    def test_unmapped_user_falls_back_to_mobile_dashboard(self):
        user = User.objects.create_user("guard", "guard@test.com", "password")

        decision = DashboardRouter.resolve_decision(user)

        self.assertEqual(decision.route_name, "operations:mobile_dashboard")
        self.assertFalse(decision.matched)
