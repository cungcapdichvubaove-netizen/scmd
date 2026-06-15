# -*- coding: utf-8 -*-
"""Regression tests for the CompanyInfo admin operations UI."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings

from main.admin import CompanyInfoAdmin
from main.models import CompanyInfo


ORG_ID = UUID("00000000-0000-0000-0000-000000000456")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class CompanyInfoAdminUITests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_superuser(
            username="company-ui-root",
            email="company-ui-root@scmdpro.local",
            password="test-pass",
        )
        self.model_admin = CompanyInfoAdmin(CompanyInfo, AdminSite())

    def _request(self):
        request = self.factory.get("/admin/main/companyinfo/")
        request.user = self.user
        return request

    def test_companyinfo_admin_uses_compact_changelist_template(self):
        self.assertEqual(
            self.model_admin.change_list_template,
            "admin/main/companyinfo/change_list.html",
        )
        template = Path("templates/admin/main/companyinfo/change_list.html").read_text(encoding="utf-8")

        self.assertIn("scmd-company-page", template)
        self.assertIn("scmd-company-strip", template)
        self.assertNotIn("<style", template.lower())

    def test_companyinfo_admin_completion_context_reports_missing_fields(self):
        CompanyInfo.objects.create(
            ten_cong_ty="SCMD Test",
            ma_so_thue="",
            dia_chi="",
            dien_thoai="",
            email="",
        )

        context = self.model_admin._company_profile_context(self._request())

        self.assertEqual(context["scmd_company_completion"], 17)
        self.assertGreaterEqual(context["scmd_company_missing_count"], 1)
        self.assertIn("main/companyinfo", context["scmd_company_primary_url"])
        self.assertIn("change", context["scmd_company_primary_url"])

    def test_companyinfo_admin_list_headers_are_vietnamese_and_actionable(self):
        list_display = self.model_admin.get_list_display(self._request())

        self.assertIn("company_identity", list_display)
        self.assertIn("profile_actions", list_display)
        self.assertEqual(str(self.model_admin.company_identity.short_description), "Thông tin công ty")
        self.assertEqual(str(self.model_admin.contact_display.short_description), "Liên hệ")
