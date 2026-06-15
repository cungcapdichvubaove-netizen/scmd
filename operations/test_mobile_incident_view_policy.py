# -*- coding: utf-8 -*-
"""Regression tests for MobileBaoCaoSuCoViewSet incident scope policy usage."""

from __future__ import annotations

from datetime import time
from unittest.mock import patch
from uuid import UUID

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from rolepermissions.roles import assign_role

from clients.models import HopDong, MucTieu
from operations.api_views import MobileBaoCaoSuCoViewSet
from operations.models import BaoCaoSuCo, CaLamViec, PhanCongCaTruc, ViTriChot
from users.models import LichSuCongTac, NhanVien


ORG_ID = UUID("00000000-0000-0000-0000-000000000424")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class MobileIncidentViewPolicyTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.executive_user = User.objects.create_user(username="incident-executive", email="incident-exec@example.com")
        self.accounting_user = User.objects.create_user(username="incident-accountant", email="incident-acc@example.com")
        self.commander_user = User.objects.create_user(username="incident-commander", email="incident-cmd@example.com")
        self.area_user = User.objects.create_user(username="incident-area", email="incident-area@example.com")
        self.guard_a_user = User.objects.create_user(username="incident-guard-a", email="incident-a@example.com")
        self.guard_peer_user = User.objects.create_user(username="incident-guard-peer", email="incident-peer@example.com")
        self.guard_b_user = User.objects.create_user(username="incident-guard-b", email="incident-b@example.com")
        self.no_profile_user = User.objects.create_user(username="incident-no-profile", email="incident-no-profile@example.com")

        assign_role(self.executive_user, "ban_giam_doc")
        assign_role(self.accounting_user, "ke_toan")
        assign_role(self.commander_user, "doi_truong")
        assign_role(self.area_user, "quan_ly_vung")
        assign_role(self.guard_a_user, "nhan_vien_bao_ve")
        assign_role(self.guard_peer_user, "nhan_vien_bao_ve")
        assign_role(self.guard_b_user, "nhan_vien_bao_ve")

        self.executive = self._staff("NV-INC-EXEC", "Ban giám đốc", self.executive_user)
        self.accountant = self._staff("NV-INC-ACC", "Kế toán", self.accounting_user)
        self.commander = self._staff("NV-INC-CMD", "Chỉ huy", self.commander_user)
        self.area = self._staff("NV-INC-AREA", "Quản lý vùng", self.area_user)
        self.guard_a = self._staff("NV-INC-A", "Bảo vệ A", self.guard_a_user)
        self.guard_peer = self._staff("NV-INC-PEER", "Bảo vệ cùng site", self.guard_peer_user)
        self.guard_b = self._staff("NV-INC-B", "Bảo vệ B", self.guard_b_user)
        NhanVien.objects.filter(user=self.no_profile_user).delete()

        self.today = timezone.localdate()
        self.contract = HopDong.objects.create(
            so_hop_dong="HD-MOBILE-INCIDENT-SCOPE",
            ngay_ky=self.today,
            ngay_hieu_luc=self.today,
            ngay_het_han=self.today,
            gia_tri=0,
        )
        self.site_a = self._site("Incident Site A", quan_ly_muc_tieu=self.commander, quan_ly_vung=self.area)
        self.site_b = self._site("Incident Site B", quan_ly_vung=self.area)
        self.site_c = self._site("Incident Site C")
        self.post_a = self._post("Incident Chốt A", self.site_a)
        self.post_b = self._post("Incident Chốt B", self.site_b)
        self.post_c = self._post("Incident Chốt C", self.site_c)
        self.shift_type = CaLamViec.objects.create(
            tenant_id=ORG_ID,
            ten_ca="Ca incident mobile",
            gio_bat_dau=time(6, 0),
            gio_ket_thuc=time(18, 0),
        )
        self._assign_current_site(self.guard_a, self.site_a)
        self._assign_current_site(self.guard_peer, self.site_a)
        self._assign_current_site(self.guard_b, self.site_b)
        self.shift_a = self._shift(self.guard_a, self.post_a)
        self.shift_peer = self._shift(self.guard_peer, self.post_a)
        self.shift_b = self._shift(self.guard_b, self.post_b)

        self.incident_guard_a = self._incident("Sự cố guard A", self.guard_a, self.site_a, self.shift_a)
        self.incident_peer_same_site = self._incident("Sự cố peer cùng site", self.guard_peer, self.site_a, None)
        self.incident_site_b = self._incident("Sự cố site B", self.guard_b, self.site_b, self.shift_b)
        self.incident_site_c_unassigned = self._incident("Sự cố site C không ca", self.accountant, self.site_c, None)
        self.factory = APIRequestFactory()

    def _staff(self, code, name, user):
        staff = user.nhan_vien
        staff.ma_nhan_vien = code
        staff.ho_ten = name
        staff.tenant_id = ORG_ID
        staff.email = user.email or None
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

    def _incident(self, title, reporter, site, shift):
        return BaoCaoSuCo.objects.create(
            tenant_id=ORG_ID,
            tieu_de=title,
            nhan_vien_bao_cao=reporter,
            muc_tieu=site,
            ca_truc=shift,
            mo_ta_chi_tiet=f"Nội dung {title}",
        )

    def _view_queryset_ids(self, user):
        view = MobileBaoCaoSuCoViewSet()
        request = self.factory.get("/operations/mobile/su-co/")
        request.user = user
        view.request = request
        return set(view.get_queryset().values_list("pk", flat=True))

    def test_mobile_incident_queryset_delegates_to_incident_visibility_policy(self):
        request = self.factory.get("/operations/mobile/su-co/")
        request.user = self.guard_a_user
        view = MobileBaoCaoSuCoViewSet()
        view.request = request

        with patch("operations.api_views.IncidentVisibilityPolicy.visible_incidents") as visible:
            visible.return_value = BaoCaoSuCo.objects.filter(pk=self.incident_guard_a.pk)
            qs = view.get_queryset()

        visible.assert_called_once_with(request.user)
        self.assertEqual(set(qs.values_list("pk", flat=True)), {self.incident_guard_a.pk})

    def test_executive_and_accounting_keep_legacy_global_incident_visibility(self):
        expected = {
            self.incident_guard_a.pk,
            self.incident_peer_same_site.pk,
            self.incident_site_b.pk,
            self.incident_site_c_unassigned.pk,
        }
        self.assertEqual(self._view_queryset_ids(self.executive_user), expected)
        self.assertEqual(self._view_queryset_ids(self.accounting_user), expected)

    def test_guard_sees_own_incident_and_own_shift_incidents_only(self):
        self.assertEqual(self._view_queryset_ids(self.guard_a_user), {self.incident_guard_a.pk})
        self.assertNotIn(self.incident_peer_same_site.pk, self._view_queryset_ids(self.guard_a_user))

    def test_commander_and_area_manager_see_incidents_for_managed_sites(self):
        self.assertEqual(
            self._view_queryset_ids(self.commander_user),
            {self.incident_guard_a.pk, self.incident_peer_same_site.pk},
        )
        self.assertEqual(
            self._view_queryset_ids(self.area_user),
            {self.incident_guard_a.pk, self.incident_peer_same_site.pk, self.incident_site_b.pk},
        )
        self.assertNotIn(self.incident_site_c_unassigned.pk, self._view_queryset_ids(self.area_user))

    def test_user_without_staff_profile_fails_closed_unless_global_role(self):
        self.assertEqual(self._view_queryset_ids(self.no_profile_user), set())
