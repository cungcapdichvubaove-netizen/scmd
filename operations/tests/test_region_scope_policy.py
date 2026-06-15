# -*- coding: utf-8 -*-
"""Regression tests for REGION scope enforcement."""

from __future__ import annotations

from datetime import date, time
from uuid import UUID

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rolepermissions.roles import assign_role

from clients.access_policies import RegionVisibilityPolicy, SiteVisibilityPolicy
from clients.models import HopDong, MucTieu
from operations.access_policies import ShiftVisibilityPolicy
from operations.models import CaLamViec, PhanCongCaTruc, ViTriChot
from users.models import NhanVien
from users.models_assignment import NhanVienRegionAssignment, Region


ORG_ID = UUID("00000000-0000-0000-0000-000000000512")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class RegionScopePolicyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.area_user = User.objects.create_user(username="region-area")
        self.office_user = User.objects.create_user(username="region-office")
        self.guard_north_user = User.objects.create_user(username="region-guard-north")
        self.guard_south_user = User.objects.create_user(username="region-guard-south")
        self.guard_legacy_user = User.objects.create_user(username="region-guard-legacy")

        assign_role(self.area_user, "quan_ly_vung")
        assign_role(self.guard_north_user, "nhan_vien_bao_ve")
        assign_role(self.guard_south_user, "nhan_vien_bao_ve")
        assign_role(self.guard_legacy_user, "nhan_vien_bao_ve")

        self.area_staff = self._staff("NV-RG-AREA", "Quản lý vùng", self.area_user)
        self.office_staff = self._staff("NV-RG-OFF", "Nhân viên văn phòng", self.office_user)
        self.guard_north = self._staff("NV-RG-N", "Bảo vệ Bắc", self.guard_north_user)
        self.guard_south = self._staff("NV-RG-S", "Bảo vệ Nam", self.guard_south_user)
        self.guard_legacy = self._staff("NV-RG-L", "Bảo vệ Legacy", self.guard_legacy_user)

        self.region_north = Region.objects.create(ma_vung="BAC", ten_vung="Vùng Bắc")
        self.region_south = Region.objects.create(ma_vung="NAM", ten_vung="Vùng Nam")
        NhanVienRegionAssignment.objects.create(
            nhan_vien=self.area_staff,
            region=self.region_north,
            starts_at=date(2026, 1, 1),
        )
        NhanVienRegionAssignment.objects.create(
            nhan_vien=self.office_staff,
            region=self.region_north,
            starts_at=date(2026, 1, 1),
        )

        self.contract = HopDong.objects.create(
            so_hop_dong="HD-REGION-001",
            ngay_ky=date(2026, 1, 1),
            ngay_hieu_luc=date(2026, 1, 1),
            ngay_het_han=date(2026, 12, 31),
            gia_tri=0,
        )
        self.site_north = self._site("Mục tiêu Bắc", region=self.region_north, quan_ly_vung=self.area_staff)
        self.site_south_wrong = self._site("Mục tiêu Nam", region=self.region_south, quan_ly_vung=self.area_staff)
        self.site_legacy = self._site("Mục tiêu Legacy", quan_ly_vung=self.area_staff)

        self.shift_type = CaLamViec.objects.create(
            tenant_id=ORG_ID,
            ten_ca="Ca vùng",
            gio_bat_dau=time(6, 0),
            gio_ket_thuc=time(18, 0),
        )
        self.shift_north = self._shift(self.guard_north, self.site_north, "Chốt Bắc")
        self.shift_south = self._shift(self.guard_south, self.site_south_wrong, "Chốt Nam")
        self.shift_legacy = self._shift(self.guard_legacy, self.site_legacy, "Chốt Legacy")

    def _staff(self, code, name, user):
        staff = user.nhan_vien
        staff.ma_nhan_vien = code
        staff.ho_ten = name
        staff.tenant_id = ORG_ID
        staff.save()
        return staff

    def _site(self, name, **kwargs):
        return MucTieu.objects.create(
            hop_dong=self.contract,
            ten_muc_tieu=name,
            dia_chi=f"Địa chỉ {name}",
            **kwargs,
        )

    def _shift(self, staff, site, post_name):
        post = ViTriChot.objects.create(tenant_id=ORG_ID, ten_vi_tri=post_name, muc_tieu=site)
        return PhanCongCaTruc.objects.create(
            tenant_id=ORG_ID,
            nhan_vien=staff,
            vi_tri_chot=post,
            ca_lam_viec=self.shift_type,
            ngay_truc=date(2026, 2, 1),
        )

    def test_region_visibility_policy_returns_only_assigned_region_sites(self):
        managed_ids = set(
            RegionVisibilityPolicy.managed_sites(self.area_user).values_list("pk", flat=True)
        )

        self.assertIn(self.site_north.pk, managed_ids)
        self.assertIn(self.site_legacy.pk, managed_ids)
        self.assertNotIn(self.site_south_wrong.pk, managed_ids)

    def test_region_assignment_without_quan_ly_vung_role_does_not_grant_region_scope(self):
        self.assertFalse(RegionVisibilityPolicy.managed_regions(self.office_user).exists())
        self.assertFalse(RegionVisibilityPolicy.managed_sites(self.office_user).exists())

    def test_shift_visibility_uses_region_scope_not_legacy_quan_ly_vung_only(self):
        visible_ids = set(ShiftVisibilityPolicy.visible_shifts(self.area_user).values_list("pk", flat=True))

        self.assertIn(self.shift_north.pk, visible_ids)
        self.assertIn(self.shift_legacy.pk, visible_ids)
        self.assertNotIn(self.shift_south.pk, visible_ids)

    def test_site_visibility_managed_sites_reuses_region_scope_binding(self):
        managed_ids = set(SiteVisibilityPolicy.managed_sites(self.area_user).values_list("pk", flat=True))

        self.assertEqual(managed_ids, {self.site_north.pk, self.site_legacy.pk})
