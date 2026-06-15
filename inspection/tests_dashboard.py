from __future__ import annotations

from pathlib import Path

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse


class InspectionDashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="inspection_exec", password="password")
        Group.objects.get_or_create(name="Thanh tra")[0].user_set.add(self.user)
        self.client.login(username="inspection_exec", password="password")

    def test_dashboard_view_loads_deduplicated_sections(self):
        response = self.client.get(reverse("inspection:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thanh tra & Giám sát")
        self.assertContains(response, "Việc cần xử lý")
        self.assertContains(response, "Nhịp vận hành tuần")
        self.assertContains(response, "Đối chiếu tuần tra vận hành")
        self.assertContains(response, "Mục tiêu không đạt")
        self.assertContains(response, "Vi phạm chờ duyệt")
        self.assertContains(response, "Lịch đào tạo sắp tới")

    def test_dashboard_response_has_no_fake_cta_links(self):
        response = self.client.get(reverse("inspection:dashboard"))
        content = response.content.decode("utf-8")

        self.assertNotIn('href="#"', content)
        self.assertNotIn("javascript:void", content)


class InspectionDashboardTemplateContractTests(TestCase):
    def test_template_has_no_forbidden_runtime_links_or_cyber_copy(self):
        source = Path("inspection/templates/inspection/dashboard.html").read_text(encoding="utf-8")

        self.assertNotIn('href="#"', source)
        self.assertNotIn("javascript:void", source)
        self.assertNotIn("War " + "Room", source)
        self.assertNotIn("Senti" + "nel", source)
        self.assertNotIn("SOC", source)
        self.assertNotIn("Cyber", source)

    def test_template_keeps_deduplicated_dashboard_markup(self):
        source = Path("inspection/templates/inspection/dashboard.html").read_text(encoding="utf-8")

        self.assertIn("ix-priority__card", source)
        self.assertIn("ix-grid", source)
        self.assertIn("ix-secondary-grid", source)
        self.assertNotIn("idt-metrics", source)
        self.assertNotIn("Tóm tắt điều hành", source)
