# -*- coding: utf-8 -*-
"""Regression tests for direct staff visibility policy."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rolepermissions.roles import assign_role

from clients.models import CoHoiKinhDoanh, HopDong, KhachHangTiemNang, MucTieu
from users.access_policies import StaffVisibilityPolicy
from users.models import LichSuCongTac, NhanVien
from users.models_assignment import NhanVienRegionAssignment, Region


ORG_ID = UUID("00000000-0000-0000-0000-000000000123")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class StaffVisibilityPolicyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.commander_user = User.objects.create_user(username="staff-commander-a")
        self.area_user = User.objects.create_user(username="staff-area-1")
        self.guard_a_user = User.objects.create_user(username="staff-guard-a")
        self.guard_a_peer_user = User.objects.create_user(username="staff-guard-a-peer")
        self.guard_b_user = User.objects.create_user(username="staff-guard-b")
        self.no_profile_user = User.objects.create_user(username="staff-no-profile")
        self._delete_signal_profile(self.no_profile_user)
        self.superuser = User.objects.create_superuser(
            username="staff-technical-admin",
            email="staff-technical-admin@scmdpro.local",
            password="test-pass",
        )
        self._delete_signal_profile(self.superuser)

        self.commander = self._staff("NV101", "Chỉ huy A", self.commander_user)
        self.area_manager = self._staff("NV102", "Quản lý vùng 1", self.area_user)
        assign_role(self.area_user, "quan_ly_vung")
        self.guard_a = self._staff("NV103", "Nhân viên A", self.guard_a_user)
        self.guard_a_peer = self._staff("NV106", "Nhân viên cùng mục tiêu A", self.guard_a_peer_user)
        self.guard_b = self._staff("NV104", "Nhân viên B", self.guard_b_user)
        self.inactive_guard_a = self._staff(
            "NV105",
            "Nhân viên nghỉ việc A",
            None,
            trang_thai_lam_viec=NhanVien.TrangThaiLamViec.NGHI_VIEC,
        )

        self.region_a = Region.objects.create(
            tenant_id=ORG_ID,
            ma_vung="KV-STAFF-01",
            ten_vung="Khu vực 1",
        )
        NhanVienRegionAssignment.objects.create(
            tenant_id=ORG_ID,
            nhan_vien=self.area_manager,
            region=self.region_a,
            starts_at=date(2026, 1, 1),
            status=NhanVienRegionAssignment.Status.ACTIVE,
        )

        self.region_contract = self._contract("HD-AS-STAFF-001", region=self.region_a)
        self.outside_contract = self._contract("HD-AS-STAFF-002")
        self.site_a = self._site("Mục tiêu A", self.region_contract, quan_ly_muc_tieu=self.commander, quan_ly_vung=self.area_manager)
        self.site_b = self._site("Mục tiêu B", self.region_contract, quan_ly_vung=self.area_manager)
        self.site_c = self._site("Mục tiêu C", self.outside_contract)

        self._assign_current_site(self.guard_a, self.site_a)
        self._assign_current_site(self.guard_a_peer, self.site_a)
        self._assign_current_site(self.inactive_guard_a, self.site_a)
        self._assign_current_site(self.guard_b, self.site_b)

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

    def visible_staff_ids(self, user):
        return set(StaffVisibilityPolicy.visible_staff(user).values_list("id", flat=True))

    def scheduling_staff_ids(self, user, site):
        return set(
            StaffVisibilityPolicy.visible_staff_for_scheduling(user, site).values_list("id", flat=True)
        )

    def test_site_commander_sees_staff_in_direct_site_but_not_other_site(self):
        actual = self.visible_staff_ids(self.commander_user)
        self.assertIn(self.commander.id, actual)
        self.assertIn(self.guard_a.id, actual)
        self.assertIn(self.guard_a_peer.id, actual)
        self.assertIn(self.inactive_guard_a.id, actual)
        self.assertNotIn(self.guard_b.id, actual)

    def test_area_manager_sees_staff_in_managed_area_sites_only(self):
        actual = self.visible_staff_ids(self.area_user)
        self.assertIn(self.guard_a.id, actual)
        self.assertIn(self.guard_a_peer.id, actual)
        self.assertIn(self.guard_b.id, actual)
        self.assertIn(self.area_manager.id, actual)
        self.assertNotIn(self.commander.id, actual)

    def test_guard_assignment_does_not_reveal_peer_staff_at_same_site(self):
        actual = self.visible_staff_ids(self.guard_a_user)
        self.assertEqual(actual, {self.guard_a.id})
        self.assertNotIn(self.guard_a_peer.id, actual)

    def test_missing_profile_does_not_widen_staff_scope(self):
        self.assertFalse(StaffVisibilityPolicy.visible_staff(self.no_profile_user).exists())

    def test_scheduling_visibility_requires_visible_site_and_active_staff(self):
        actual = self.scheduling_staff_ids(self.commander_user, self.site_a)
        self.assertEqual(actual, {self.guard_a.id, self.guard_a_peer.id})

    def test_scheduling_visibility_denies_hidden_site_without_action_policy(self):
        self.assertFalse(
            StaffVisibilityPolicy.visible_staff_for_scheduling(self.commander_user, self.site_b).exists()
        )

    def test_scheduling_visibility_rejects_missing_site(self):
        self.assertFalse(
            StaffVisibilityPolicy.visible_staff_for_scheduling(self.commander_user, None).exists()
        )

    def test_guard_with_only_assignment_has_no_scheduling_candidates(self):
        self.assertFalse(
            StaffVisibilityPolicy.visible_staff_for_scheduling(self.guard_a_user, self.site_a).exists()
        )


    def test_superuser_without_staff_profile_sees_all_staff_for_admin_visibility(self):
        actual = self.visible_staff_ids(self.superuser)
        expected = set(NhanVien.objects.for_tenant(ORG_ID).values_list("id", flat=True))
        self.assertEqual(actual, expected)

    def test_superuser_without_staff_profile_sees_active_scheduling_candidates(self):
        actual = self.scheduling_staff_ids(self.superuser, self.site_a)
        self.assertIn(self.guard_a.id, actual)
        self.assertIn(self.guard_a_peer.id, actual)
        self.assertNotIn(self.inactive_guard_a.id, actual)
