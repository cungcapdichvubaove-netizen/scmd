# -*- coding: utf-8 -*-
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from main.company_info import build_company_report_context, get_company_info, invalidate_company_info_cache
from main.models import CompanyInfo


ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class CompanyInfoSingletonTests(TestCase):
    def setUp(self):
        invalidate_company_info_cache(ORG_ID)
        CompanyInfo.objects.all().delete()

    def tearDown(self):
        invalidate_company_info_cache(ORG_ID)

    def test_company_info_is_singleton_per_organization(self):
        CompanyInfo.objects.create(ten_cong_ty="SCMD")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CompanyInfo.objects.create(ten_cong_ty="SCMD Duplicate")

    def test_get_company_info_returns_configured_singleton(self):
        profile = CompanyInfo.objects.create(ten_cong_ty="SCMD Pro", dia_chi="Hà Nội")
        invalidate_company_info_cache(ORG_ID)

        loaded = get_company_info()

        self.assertEqual(loaded.pk, profile.pk)
        self.assertEqual(build_company_report_context(loaded)["name"], "SCMD Pro")

    def test_company_info_manager_for_current_returns_configured_organization(self):
        profile = CompanyInfo.objects.create(ten_cong_ty="SCMD Pro")

        loaded = CompanyInfo.objects.for_current().get()

        self.assertEqual(loaded.pk, profile.pk)
        self.assertEqual(loaded.tenant_id, ORG_ID)
