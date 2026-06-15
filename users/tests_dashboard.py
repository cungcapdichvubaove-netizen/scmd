from __future__ import annotations

from pathlib import Path

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse


class UsersDashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="hr_exec", password="password")
        Group.objects.get_or_create(name="Phòng Hành chính Nhân sự")[0].user_set.add(self.user)
        self.client.login(username="hr_exec", password="password")

    def test_dashboard_view_loads_compact_hr_workspace(self):
        response = self.client.get(reverse("users:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "hr-main-grid")
        self.assertContains(response, "hr-metrics")
        self.assertContains(response, "hr-table")
        self.assertContains(response, "Kiểm soát hồ sơ HR")

    def test_dashboard_response_has_no_fake_cta_links(self):
        response = self.client.get(reverse("users:dashboard"))
        content = response.content.decode("utf-8")

        self.assertNotIn('href="#"', content)
        self.assertNotIn("javascript:void", content)


class UsersDashboardTemplateContractTests(TestCase):
    def test_template_has_no_forbidden_runtime_links_or_cyber_copy(self):
        source = Path("users/templates/users/dashboard_hr.html").read_text(encoding="utf-8")

        self.assertNotIn('href="#"', source)
        self.assertNotIn("javascript:void", source)
        self.assertNotIn("War " + "Room", source)
        self.assertNotIn("Senti" + "nel", source)
        self.assertNotIn("SOC", source)
        self.assertNotIn("Cyber", source)

    def test_template_keeps_deduplicated_hr_markup(self):
        source = Path("users/templates/users/dashboard_hr.html").read_text(encoding="utf-8")

        self.assertIn("hr-main-grid", source)
        self.assertIn("control_checks", source)
        self.assertIn("Kiểm soát hồ sơ HR", source)
        self.assertNotIn("scmd-workstrip", source)
