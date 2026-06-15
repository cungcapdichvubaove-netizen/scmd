# -*- coding: utf-8 -*-
"""Regression tests for MobileCaTrucViewSet central scope policy usage."""

from __future__ import annotations

from datetime import time
from uuid import UUID
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from rolepermissions.roles import assign_role

from clients.models import HopDong, MucTieu
from operations.api_views import MobileCaTrucViewSet
from operations.models import CaLamViec, PhanCongCaTruc, ViTriChot
from users.models import LichSuCongTac, NhanVien


ORG_ID = UUID("00000000-0000-0000-0000-000000000322")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class MobileCaTrucViewSetScopeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.executive_user = User.objects.create_user(username="mobile-executive")
        self.accounting_user = User.objects.create_user(username="mobile-accountant")
        self.commander_user = User.objects.create_user(username="mobile-commander")
        self.area_user = User.objects.create_user(username="mobile-area")
        self.guard_a_user = User.objects.create_user(username="mobile-guard-a")
        self.guard_peer_user = User.objects.create_user(username="mobile-guard-peer")
        self.guard_b_user = User.objects.create_user(username="mobile-guard-b")

        assign_role(self.executive_user, "ban_giam_doc")
        assign_role(self.accounting_user, "ke_toan")
        assign_role(self.commander_user, "doi_truong")
        assign_role(self.area_user, "quan_ly_vung")
        assign_role(self.guard_a_user, "nhan_vien_bao_ve")
        assign_role(self.guard_peer_user, "nhan_vien_bao_ve")
        assign_role(self.guard_b_user, "nhan_vien_bao_ve")

        self.executive = self._staff("NV-MOB-EXEC", "Ban giám đốc", self.executive_user)
        self.accountant = self._staff("NV-MOB-ACC", "Kế toán", self.accounting_user)
        self.commander = self._staff("NV-MOB-CMD", "Chỉ huy", self.commander_user)
        self.area = self._staff("NV-MOB-AREA", "Quản lý vùng", self.area_user)
        self.guard_a = self._staff("NV-MOB-A", "Bảo vệ A", self.guard_a_user)
        self.guard_peer = self._staff("NV-MOB-PEER", "Bảo vệ cùng site", self.guard_peer_user)
        self.guard_b = self._staff("NV-MOB-B", "Bảo vệ B", self.guard_b_user)

        self.today = timezone.localdate()
        self.contract = HopDong.objects.create(
            so_hop_dong="HD-MOBILE-SCOPE",
            ngay_ky=self.today,
            ngay_hieu_luc=self.today,
            ngay_het_han=self.today,
            gia_tri=0,
        )
        self.site_a = self._site("Site A", quan_ly_muc_tieu=self.commander, quan_ly_vung=self.area)
        self.site_b = self._site("Site B", quan_ly_vung=self.area)
        self.site_c = self._site("Site C")
        self.post_a = self._post("Chốt A", self.site_a)
        self.post_b = self._post("Chốt B", self.site_b)
        self.post_c = self._post("Chốt C", self.site_c)
        self.shift_type = CaLamViec.objects.create(
            tenant_id=ORG_ID,
            ten_ca="Ca mobile",
            gio_bat_dau=time(6, 0),
            gio_ket_thuc=time(18, 0),
        )
        self._assign_current_site(self.guard_a, self.site_a)
        self._assign_current_site(self.guard_peer, self.site_a)
        self._assign_current_site(self.guard_b, self.site_b)
        self.shift_a = self._shift(self.guard_a, self.post_a)
        self.shift_peer = self._shift(self.guard_peer, self.post_a)
        self.shift_b = self._shift(self.guard_b, self.post_b)
        self.shift_c = self._shift(self.accountant, self.post_c)
        self.factory = APIRequestFactory()

    def _staff(self, code, name, user):
        staff = user.nhan_vien
        staff.ma_nhan_vien = code
        staff.ho_ten = name
        staff.tenant_id = ORG_ID
        staff.save()
        return staff

    def _site(self, name, **kwargs):
        return MucTieu.objects.create(hop_dong=self.contract, ten_muc_tieu=name, dia_chi=f"Địa chỉ {name}", **kwargs)

    def _post(self, name, site):
        return ViTriChot.objects.create(tenant_id=ORG_ID, ten_vi_tri=name, muc_tieu=site)

    def _assign_current_site(self, staff, site):
        return LichSuCongTac.objects.create(
            nhan_vien=staff,
            muc_tieu=site,
            ngay_bat_dau=self.today,
            ngay_ket_thuc=None,
        )

    def _shift(self, staff, post):
        return PhanCongCaTruc.objects.create(
            tenant_id=ORG_ID,
            nhan_vien=staff,
            vi_tri_chot=post,
            ca_lam_viec=self.shift_type,
            ngay_truc=self.today,
        )

    def _view_queryset_ids(self, user):
        view = MobileCaTrucViewSet()
        request = self.factory.get("/operations/ca-truc/")
        request.user = user
        view.request = request
        return set(view.get_queryset().values_list("pk", flat=True))

    def test_view_delegates_to_shift_visibility_policy(self):
        with patch("operations.api_views.ShiftVisibilityPolicy.visible_shifts") as visible_shifts:
            visible_shifts.return_value = PhanCongCaTruc.objects.filter(pk=self.shift_a.pk)
            ids = self._view_queryset_ids(self.guard_a_user)
        visible_shifts.assert_called_once_with(self.guard_a_user)
        self.assertEqual(ids, {self.shift_a.pk})

    def test_executive_and_accounting_keep_legacy_global_mobile_visibility(self):
        expected = {self.shift_a.pk, self.shift_peer.pk, self.shift_b.pk, self.shift_c.pk}
        self.assertEqual(self._view_queryset_ids(self.executive_user), expected)
        self.assertEqual(self._view_queryset_ids(self.accounting_user), expected)

    def test_commander_area_and_guard_are_not_over_scoped(self):
        self.assertEqual(self._view_queryset_ids(self.commander_user), {self.shift_a.pk, self.shift_peer.pk})
        self.assertEqual(self._view_queryset_ids(self.area_user), {self.shift_a.pk, self.shift_peer.pk, self.shift_b.pk})
        self.assertEqual(self._view_queryset_ids(self.guard_a_user), {self.shift_a.pk})
        self.assertNotIn(self.shift_peer.pk, self._view_queryset_ids(self.guard_a_user))
