# -*- coding: utf-8 -*-
"""Regression tests for mobile dashboard organization scope."""

from __future__ import annotations

from datetime import time
from unittest.mock import patch
from uuid import UUID, uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware

from clients.models import HopDong, MucTieu
from operations.application.attendance_use_cases import GetMobileDashboardUseCase
from operations.models import CaLamViec, ChamCong, PhanCongCaTruc, ViTriChot
from users.models import NhanVien
from operations.views import mobile_cham_cong_view


ORG_ID = UUID("00000000-0000-0000-0000-000000000323")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class MobileDashboardScopeTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        user = get_user_model().objects.create_user(username="mobile-dashboard-guard")
        self.staff = user.nhan_vien
        self.staff.ma_nhan_vien = "NV-MOB-DASH"
        self.staff.ho_ten = "Guard dashboard"
        self.staff.save()
        contract = HopDong.objects.create(
            so_hop_dong="HD-MOB-DASH",
            ngay_ky=self.today,
            ngay_hieu_luc=self.today,
            ngay_het_han=self.today,
            gia_tri=0,
        )
        site = MucTieu.objects.create(hop_dong=contract, ten_muc_tieu="Dashboard Site", dia_chi="Địa chỉ")
        post = ViTriChot.objects.create(tenant_id=ORG_ID, ten_vi_tri="Dashboard Post", muc_tieu=site)
        shift_type = CaLamViec.objects.create(
            tenant_id=ORG_ID,
            ten_ca="Ca dashboard",
            gio_bat_dau=time(0, 0),
            gio_ket_thuc=time(23, 59),
        )
        self.shift = PhanCongCaTruc.objects.create(
            tenant_id=ORG_ID,
            nhan_vien=self.staff,
            vi_tri_chot=post,
            ca_lam_viec=shift_type,
            ngay_truc=self.today,
        )

    def test_dashboard_does_not_return_cross_organization_shift_residue(self):
        rogue_tenant_id = uuid4()
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE operations_phancongcatruc SET tenant_id = %s WHERE id = %s",
                [str(rogue_tenant_id), self.shift.pk],
            )

        shift, status, alive_check = GetMobileDashboardUseCase.execute(self.staff)
        self.assertIsNone(shift)
        self.assertFalse(status)
        self.assertIsNone(alive_check)

    def test_dashboard_execute_returns_three_tuple_for_active_checked_in_shift(self):
        ChamCong.objects.create(
            tenant_id=ORG_ID,
            ca_truc=self.shift,
            thoi_gian_check_in=timezone.now(),
            thoi_gian_check_out=None,
        )

        result = GetMobileDashboardUseCase.execute(self.staff)

        self.assertEqual(len(result), 3)
        shift, status, alive_check = result
        self.assertEqual(shift, self.shift)
        self.assertTrue(status)
        self.assertIsNone(alive_check)

    def test_dashboard_execute_returns_three_tuple_for_upcoming_or_unchecked_shift(self):
        result = GetMobileDashboardUseCase.execute(self.staff)

        self.assertEqual(len(result), 3)
        shift, status, alive_check = result
        self.assertEqual(shift, self.shift)
        self.assertFalse(status)
        self.assertIsNone(alive_check)

    def test_dashboard_execute_returns_three_tuple_when_no_shift_exists(self):
        PhanCongCaTruc.objects.filter(pk=self.shift.pk).delete()

        result = GetMobileDashboardUseCase.execute(self.staff)

        self.assertEqual(result, (None, False, None))

    def test_mobile_cham_cong_view_unpacks_dashboard_contract_without_value_error(self):
        request = RequestFactory().post(
            "/operations/mobile/cham-cong/",
            data={"action": "check_in", "lat": "", "lng": "", "note": ""},
        )
        request.user = self.staff.user
        SessionMiddleware(lambda _request: None).process_request(request)
        request.session.save()
        request._messages = FallbackStorage(request)

        with patch(
            "operations.views.CheckInUseCase.execute",
            return_value=(True, "OK", {}, None),
        ) as mocked_checkin:
            response = mobile_cham_cong_view(request)

        self.assertEqual(response.status_code, 302)
        mocked_checkin.assert_called_once()

