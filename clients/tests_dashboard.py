from __future__ import annotations

from pathlib import Path

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse


class ClientsDashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="sales_exec", password="password")
        Group.objects.get_or_create(name="Kinh doanh")[0].user_set.add(self.user)
        self.client.login(username="sales_exec", password="password")

    def test_dashboard_view_loads_compact_sales_workspace(self):
        response = self.client.get(reverse("clients:dashboard_crm"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kinh doanh & CRM")
        self.assertContains(response, "sales-funnel-grid")
        self.assertContains(response, "sales-action-row")
        self.assertContains(response, "Lead cần chăm sóc")
        self.assertContains(response, "Hợp đồng cần tái ký trong 30 ngày")

    def test_dashboard_response_has_no_fake_cta_links(self):
        response = self.client.get(reverse("clients:dashboard_crm"))
        content = response.content.decode("utf-8")

        self.assertNotIn('href="#"', content)
        self.assertNotIn("javascript:void", content)


class ClientsDashboardTemplateContractTests(TestCase):
    def test_template_has_no_forbidden_runtime_links_or_cyber_copy(self):
        source = Path("clients/templates/clients/dashboard_crm.html").read_text(encoding="utf-8")

        self.assertNotIn('href="#"', source)
        self.assertNotIn("javascript:void", source)
        self.assertNotIn("War " + "Room", source)
        self.assertNotIn("Senti" + "nel", source)
        self.assertNotIn("SOC", source)
        self.assertNotIn("Cyber", source)

    def test_template_keeps_deduplicated_sales_markup(self):
        source = Path("clients/templates/clients/dashboard_crm.html").read_text(encoding="utf-8")

        self.assertIn("sales-funnel-grid", source)
        self.assertIn("sales-action-row", source)
        self.assertIn("sales-inline-item", source)
        self.assertNotIn("sales-priority-card", source)
        self.assertNotIn("sales-compact-kpi", source)
