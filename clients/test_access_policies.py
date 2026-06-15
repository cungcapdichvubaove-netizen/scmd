# -*- coding: utf-8 -*-
"""Regression tests for direct site visibility policy."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rolepermissions.roles import assign_role

from clients.access_policies import SiteVisibilityPolicy
from clients.models import CoHoiKinhDoanh, HopDong, KhachHangTiemNang, MucTieu
from users.models import LichSuCongTac, NhanVien
from users.models_assignment import NhanVienRegionAssignment, Region


ORG_ID = UUID("00000000-0000-0000-0000-000000000123")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class SiteVisibilityPolicyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.commander_user = User.objects.create_user(username="commander-a")
        self.area_user = User.objects.create_user(username="area-1")
        self.guard_user = User.objects.create_user(username="guard-a")
        self.no_profile_user = User.objects.create_user(username="no-profile")
        self._delete_signal_profile(self.no_profile_user)
        self.superuser = User.objects.create_superuser(
            username="site-technical-admin",
            email="site-technical-admin@scmdpro.local",
            password="test-pass",
        )
        self._delete_signal_profile(self.superuser)

        self.commander = self._staff("NV001", "Chỉ huy A", self.commander_user)
        self.area_manager = self._staff("NV002", "Quản lý vùng 1", self.area_user)
        assign_role(self.area_user, "quan_ly_vung")
        self.guard = self._staff("NV003", "Nhân viên A", self.guard_user)

        self.region_a = Region.objects.create(
            tenant_id=ORG_ID,
            ma_vung="KV-SITE-01",
            ten_vung="Khu vực 1",
        )
        NhanVienRegionAssignment.objects.create(
            tenant_id=ORG_ID,
            nhan_vien=self.area_manager,
            region=self.region_a,
            starts_at=date(2026, 1, 1),
            status=NhanVienRegionAssignment.Status.ACTIVE,
        )

        self.region_contract = self._contract("HD-AS-001", region=self.region_a)
        self.outside_contract = self._contract("HD-AS-002")
        self.site_a = self._site("Mục tiêu A", self.region_contract, quan_ly_muc_tieu=self.commander, quan_ly_vung=self.area_manager)
        self.site_b = self._site("Mục tiêu B", self.region_contract, quan_ly_vung=self.area_manager)
        self.site_c = self._site("Mục tiêu C", self.outside_contract)

        self._assign_current_site(self.guard, self.site_a)

    def _delete_signal_profile(self, user):
        NhanVien.objects.filter(user=user).delete()
        # Clear any reverse one-to-one cache that may have been populated by
        # users.signals.create_user_profile during User.objects.create_user().
        getattr(user, "_state", None).fields_cache.pop("nhan_vien", None)

    def _staff(self, code, name, user=None, **kwargs):
        if user is not None:
            try:
                staff = user.nhan_vien
            except NhanVien.DoesNotExist:
                staff = None

            if staff is not None:
                staff.tenant_id = ORG_ID
                staff.ma_nhan_vien = code
                staff.ho_ten = name
                for field, value in kwargs.items():
                    setattr(staff, field, value)
                staff.save()
                return staff

        return NhanVien.objects.create(
            tenant_id=ORG_ID,
            ma_nhan_vien=code,
            ho_ten=name,
            user=user,
            **kwargs,
        )

    def _contract(self, contract_no, *, region=None):
        customer = KhachHangTiemNang.objects.create(
            tenant_id=ORG_ID,
            ten_cong_ty=f"Khách hàng {contract_no}",
            sdt="0900000000",
        )
        opportunity = CoHoiKinhDoanh.objects.create(
            tenant_id=ORG_ID,
            khach_hang_tiem_nang=customer,
            ten_co_hoi=f"Cơ hội {contract_no}",
            region=region,
        )
        return HopDong.objects.create(
            tenant_id=ORG_ID,
            co_hoi=opportunity,
            so_hop_dong=contract_no,
            ngay_ky=date(2026, 1, 1),
            ngay_hieu_luc=date(2026, 1, 1),
            ngay_het_han=date(2026, 12, 31),
            gia_tri=0,
        )

    def _site(self, name, contract, **kwargs):
        return MucTieu.objects.create(
            hop_dong=contract,
            ten_muc_tieu=name,
            dia_chi=f"Địa chỉ {name}",
            **kwargs,
        )

    def _assign_current_site(self, staff, site):
        return LichSuCongTac.objects.create(
            nhan_vien=staff,
            muc_tieu=site,
            ngay_bat_dau=date(2026, 1, 1),
            ngay_ket_thuc=None,
        )

    def assert_visible_site_ids(self, user, expected_ids):
        actual_ids = set(SiteVisibilityPolicy.visible_sites(user).values_list("id", flat=True))
        self.assertEqual(actual_ids, set(expected_ids))

    def test_site_commander_sees_only_direct_site(self):
        self.assert_visible_site_ids(self.commander_user, [self.site_a.id])

    def test_area_manager_sees_sites_in_managed_area_only(self):
        self.assert_visible_site_ids(self.area_user, [self.site_a.id, self.site_b.id])

    def test_guard_sees_current_assigned_site_only(self):
        self.assert_visible_site_ids(self.guard_user, [self.site_a.id])


    def test_guard_assignment_is_not_management_scope(self):
        self.assertFalse(SiteVisibilityPolicy.managed_sites(self.guard_user).exists())
        assigned_ids = set(SiteVisibilityPolicy.assigned_sites(self.guard_user).values_list("id", flat=True))
        self.assertEqual(assigned_ids, {self.site_a.id})

    def test_site_commander_management_scope_excludes_assignment_only_sites(self):
        managed_ids = set(SiteVisibilityPolicy.managed_sites(self.commander_user).values_list("id", flat=True))
        self.assertEqual(managed_ids, {self.site_a.id})

    def test_missing_profile_does_not_widen_site_scope(self):
        self.assertFalse(SiteVisibilityPolicy.visible_sites(self.no_profile_user).exists())

    def test_anonymous_user_does_not_widen_site_scope(self):
        class Anonymous:
            is_authenticated = False

        self.assertFalse(SiteVisibilityPolicy.visible_sites(Anonymous()).exists())


    def test_superuser_without_staff_profile_sees_all_sites_for_admin_visibility(self):
        expected = set(MucTieu.objects.for_tenant(ORG_ID).values_list("id", flat=True))
        self.assertEqual(set(SiteVisibilityPolicy.visible_sites(self.superuser).values_list("id", flat=True)), expected)
        self.assertEqual(set(SiteVisibilityPolicy.managed_sites(self.superuser).values_list("id", flat=True)), expected)
