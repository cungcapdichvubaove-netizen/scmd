# -*- coding: utf-8 -*-
"""Regression tests for shift visibility and scheduling action policies."""

from __future__ import annotations

from datetime import date, time
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse

from clients.models import HopDong, MucTieu
from core.policy_result import AccessScopeDenied
from core.policy_result import (
    ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE,
    ERR_SCOPE_SITE_OUT_OF_SCOPE,
    ERR_SCOPE_STAFF_OUT_OF_SCOPE,
)
from operations.application.scheduling_use_cases import ManageShiftAssignmentUseCase
from operations.access_policies import ShiftAssignmentPolicy, ShiftVisibilityPolicy
from operations.models import CaLamViec, PhanCongCaTruc, ViTriChot
from users.models import LichSuCongTac, NhanVien
from rolepermissions.roles import assign_role


ORG_ID = UUID("00000000-0000-0000-0000-000000000123")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class ShiftScopePolicyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.commander_user = User.objects.create_user(username="shift-commander-a")
        self.area_user = User.objects.create_user(username="shift-area-1")
        self.guard_a_user = User.objects.create_user(username="shift-guard-a")
        self.guard_a_peer_user = User.objects.create_user(username="shift-guard-a-peer")
        self.guard_b_user = User.objects.create_user(username="shift-guard-b")
        self.no_profile_user = User.objects.create_user(username="shift-no-profile")
        self._delete_signal_profile(self.no_profile_user)
        self.superuser = User.objects.create_superuser(
            username="shift-technical-admin",
            email="shift-technical-admin@scmdpro.local",
            password="test-pass",
        )
        self._delete_signal_profile(self.superuser)

        self.commander = self._staff("NV201", "Chỉ huy A", self.commander_user)
        self.area_manager = self._staff("NV202", "Quản lý vùng", self.area_user)
        self.guard_a = self._staff("NV203", "Nhân viên A", self.guard_a_user)
        self.guard_a_peer = self._staff("NV205", "Nhân viên cùng mục tiêu A", self.guard_a_peer_user)
        self.guard_b = self._staff("NV204", "Nhân viên B", self.guard_b_user)

        self._grant_shift_permissions(self.commander_user)
        self._grant_shift_permissions(self.area_user)
        self._grant_shift_permissions(self.guard_a_user)
        # ShiftAssignmentPolicy requires both Django model permissions and
        # the central business permission ``giao_ca_truc`` through
        # rolepermissions. The guard case intentionally receives the business
        # role to prove object scope still denies site-level mutation.
        assign_role(self.commander_user, "doi_truong")
        assign_role(self.area_user, "quan_ly_vung")
        assign_role(self.guard_a_user, "doi_truong")

        self.contract = HopDong.objects.create(
            so_hop_dong="HD-AS-SHIFT-001",
            ngay_ky=date(2026, 1, 1),
            ngay_hieu_luc=date(2026, 1, 1),
            ngay_het_han=date(2026, 12, 31),
            gia_tri=0,
        )
        self.site_a = self._site("Mục tiêu A", quan_ly_muc_tieu=self.commander, quan_ly_vung=self.area_manager)
        self.site_b = self._site("Mục tiêu B", quan_ly_vung=self.area_manager)
        self.site_c = self._site("Mục tiêu C")

        self.post_a = self._post("Chốt A", self.site_a)
        self.post_b = self._post("Chốt B", self.site_b)
        self.shift_type = CaLamViec.objects.create(
            tenant_id=ORG_ID,
            ten_ca="Ca ngày",
            gio_bat_dau=time(6, 0),
            gio_ket_thuc=time(18, 0),
        )

        self._assign_current_site(self.guard_a, self.site_a)
        self._assign_current_site(self.guard_a_peer, self.site_a)
        self._assign_current_site(self.guard_b, self.site_b)

        self.shift_a = PhanCongCaTruc.objects.create(
            tenant_id=ORG_ID,
            nhan_vien=self.guard_a,
            vi_tri_chot=self.post_a,
            ca_lam_viec=self.shift_type,
            ngay_truc=date(2026, 2, 1),
        )
        self.shift_a_peer = PhanCongCaTruc.objects.create(
            tenant_id=ORG_ID,
            nhan_vien=self.guard_a_peer,
            vi_tri_chot=self.post_a,
            ca_lam_viec=self.shift_type,
            ngay_truc=date(2026, 2, 1),
        )
        self.shift_b = PhanCongCaTruc.objects.create(
            tenant_id=ORG_ID,
            nhan_vien=self.guard_b,
            vi_tri_chot=self.post_b,
            ca_lam_viec=self.shift_type,
            ngay_truc=date(2026, 2, 1),
        )

    def _delete_signal_profile(self, user):
        NhanVien.objects.filter(user=user).delete()
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
        return NhanVien.objects.create(tenant_id=ORG_ID, ma_nhan_vien=code, ho_ten=name, user=user, **kwargs)

    def _grant_shift_permissions(self, user):
        content_type = ContentType.objects.get_for_model(PhanCongCaTruc)
        permissions = Permission.objects.filter(
            content_type=content_type,
            codename__in=["add_phancongcatruc", "change_phancongcatruc", "delete_phancongcatruc"],
        )
        user.user_permissions.add(*permissions)

    def _site(self, name, **kwargs):
        return MucTieu.objects.create(hop_dong=self.contract, ten_muc_tieu=name, dia_chi=f"Địa chỉ {name}", **kwargs)

    def _post(self, name, site):
        return ViTriChot.objects.create(tenant_id=ORG_ID, ten_vi_tri=name, muc_tieu=site)

    def _assign_current_site(self, staff, site):
        return LichSuCongTac.objects.create(
            nhan_vien=staff,
            muc_tieu=site,
            ngay_bat_dau=date(2026, 1, 1),
            ngay_ket_thuc=None,
        )

    def visible_shift_ids(self, user):
        return set(ShiftVisibilityPolicy.visible_shifts(user).values_list("id", flat=True))

    def test_site_commander_sees_only_direct_site_shifts(self):
        self.assertEqual(self.visible_shift_ids(self.commander_user), {self.shift_a.id, self.shift_a_peer.id})

    def test_area_manager_sees_managed_area_shifts(self):
        self.assertEqual(self.visible_shift_ids(self.area_user), {self.shift_a.id, self.shift_a_peer.id, self.shift_b.id})

    def test_guard_sees_own_shift_only(self):
        actual = self.visible_shift_ids(self.guard_a_user)
        self.assertEqual(actual, {self.shift_a.id})
        self.assertNotIn(self.shift_a_peer.id, actual)

    def test_missing_profile_does_not_widen_shift_scope(self):
        self.assertFalse(ShiftVisibilityPolicy.visible_shifts(self.no_profile_user).exists())

    def test_can_assign_shift_allows_staff_in_visible_site(self):
        result = ShiftAssignmentPolicy.can_assign_shift(self.commander_user, self.guard_a, self.site_a, date(2026, 2, 2))
        self.assertTrue(result.allowed)

    def test_can_assign_shift_denies_staff_outside_direct_site(self):
        result = ShiftAssignmentPolicy.can_assign_shift(self.commander_user, self.guard_b, self.site_a, date(2026, 2, 2))
        self.assertFalse(result.allowed)
        self.assertEqual(result.error_code, ERR_SCOPE_STAFF_OUT_OF_SCOPE)

    def test_can_assign_shift_denies_hidden_site(self):
        result = ShiftAssignmentPolicy.can_assign_shift(self.commander_user, self.guard_b, self.site_b, date(2026, 2, 2))
        self.assertFalse(result.allowed)
        self.assertEqual(result.error_code, ERR_SCOPE_SITE_OUT_OF_SCOPE)

    def test_guard_with_functional_permission_cannot_assign_shift_at_assigned_site(self):
        result = ShiftAssignmentPolicy.can_assign_shift(
            self.guard_a_user,
            self.guard_a_peer,
            self.site_a,
            date(2026, 2, 2),
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.error_code, ERR_SCOPE_SITE_OUT_OF_SCOPE)


    def test_add_shift_form_denies_hidden_site_before_rendering_candidates(self):
        assign_role(self.commander_user, "doi_truong")
        self.client.force_login(self.commander_user)
        url = reverse(
            "operations:them_ca_form",
            kwargs={
                "vi_tri_id": self.post_b.pk,
                "ca_id": self.shift_type.pk,
                "ngay": "2026-02-02",
            },
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)
        self.assertIn("Mục tiêu không thuộc phạm vi", response.content.decode("utf-8"))

    def test_manage_shift_assignment_use_case_denies_create_outside_scope(self):
        with self.assertRaises(AccessScopeDenied) as exc:
            ManageShiftAssignmentUseCase.execute(
                action="SAVE",
                actor_user=self.commander_user,
                nhan_vien_id=self.guard_b.pk,
                vi_tri_id=self.post_a.pk,
                ca_id=self.shift_type.pk,
                ngay_truc=date(2026, 2, 2),
                tenant_id=ORG_ID,
            )

        self.assertEqual(exc.exception.result.error_code, ERR_SCOPE_STAFF_OUT_OF_SCOPE)

    def test_manage_shift_assignment_use_case_denies_update_when_existing_shift_is_out_of_scope(self):
        with self.assertRaises(AccessScopeDenied) as exc:
            ManageShiftAssignmentUseCase.execute(
                action="SAVE",
                actor_user=self.commander_user,
                delete_old_id=self.shift_b.pk,
                nhan_vien_id=self.guard_a.pk,
                vi_tri_id=self.post_a.pk,
                ca_id=self.shift_type.pk,
                ngay_truc=date(2026, 2, 2),
                tenant_id=ORG_ID,
            )

        self.assertEqual(exc.exception.result.error_code, ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE)
        self.assertTrue(PhanCongCaTruc.objects.filter(pk=self.shift_b.pk).exists())

    def test_manage_shift_assignment_use_case_denies_delete_outside_scope(self):
        with self.assertRaises(AccessScopeDenied) as exc:
            ManageShiftAssignmentUseCase.execute(
                action="DELETE",
                actor_user=self.guard_a_user,
                delete_old_id=self.shift_b.pk,
                tenant_id=ORG_ID,
            )

        self.assertEqual(exc.exception.result.error_code, ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE)
        self.assertTrue(PhanCongCaTruc.objects.filter(pk=self.shift_b.pk).exists())


    def test_superuser_without_staff_profile_sees_all_shifts_for_admin_visibility(self):
        self.assertEqual(
            self.visible_shift_ids(self.superuser),
            {self.shift_a.id, self.shift_a_peer.id, self.shift_b.id},
        )
