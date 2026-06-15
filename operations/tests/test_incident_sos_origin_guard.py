# -*- coding: utf-8 -*-
"""Regression tests for SOS incident origin guard."""

from __future__ import annotations

from datetime import date, time
from uuid import UUID

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from clients.models import HopDong, MucTieu
from main.models import AuditLog
from operations.application.attendance_use_cases import TriggerSOSUseCase
from operations.models import BaoCaoSuCo, CaLamViec, ChamCong, PhanCongCaTruc, ViTriChot


ORG_ID = UUID("00000000-0000-0000-0000-000000000946")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class TriggerSOSOriginGuardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="sos-guard", email="sos-guard@scmdpro.test")
        self.staff = self.user.nhan_vien
        self.staff.tenant_id = ORG_ID
        self.staff.ma_nhan_vien = "SOS-001"
        self.staff.ho_ten = "Nhân viên SOS"
        self.staff.email = "sos-001@scmdpro.test"
        self.staff.save()
        self.contract = HopDong.objects.create(
            tenant_id=ORG_ID,
            so_hop_dong="HD-SOS-001",
            ngay_ky=date(2026, 1, 1),
            ngay_hieu_luc=date(2026, 1, 1),
            ngay_het_han=date(2026, 12, 31),
            gia_tri=0,
        )
        self.site = MucTieu.objects.create(
            hop_dong=self.contract,
            ten_muc_tieu="Mục tiêu SOS",
            dia_chi="Địa chỉ SOS",
        )
        self.post = ViTriChot.objects.create(tenant_id=ORG_ID, ten_vi_tri="Chốt SOS", muc_tieu=self.site)
        self.shift_type = CaLamViec.objects.create(
            tenant_id=ORG_ID,
            ten_ca="Ca SOS",
            gio_bat_dau=time(6, 0),
            gio_ket_thuc=time(18, 0),
        )
        self.shift = PhanCongCaTruc.objects.create(
            tenant_id=ORG_ID,
            nhan_vien=self.staff,
            vi_tri_chot=self.post,
            ca_lam_viec=self.shift_type,
            ngay_truc=timezone.localdate(),
        )

    def test_sos_inside_active_shift_creates_incident_with_shift_site_and_audit(self):
        ChamCong.objects.create(
            tenant_id=ORG_ID,
            ca_truc=self.shift,
            thoi_gian_check_in=timezone.now(),
            thoi_gian_check_out=None,
        )

        success, message, incident, error_code = TriggerSOSUseCase.execute(self.staff, "10.1", "106.1")

        self.assertTrue(success, message)
        self.assertIsNone(error_code)
        self.assertEqual(incident.ca_truc, self.shift)
        self.assertEqual(incident.muc_tieu, self.site)
        self.assertEqual(incident.muc_do, "NGUY_HIEM")
        self.assertTrue(
            AuditLog.objects.filter(
                module="operations",
                model_name="BaoCaoSuCo",
                object_id=str(incident.pk),
                changes__origin="mobile_sos",
            ).exists()
        )

    def test_sos_outside_active_shift_is_blocked_without_orphan_incident(self):
        success, message, incident, error_code = TriggerSOSUseCase.execute(self.staff, "10.1", "106.1")

        self.assertFalse(success)
        self.assertEqual(error_code, "NO_ACTIVE_SHIFT")
        self.assertIsNone(incident)
        self.assertIn("ca trực", message)
        self.assertFalse(BaoCaoSuCo.objects.exists())
