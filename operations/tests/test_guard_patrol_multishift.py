# -*- coding: utf-8 -*-
"""Multi-shift guard patrol selection tests."""

from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from operations.application.guard_patrol_use_cases import ListGuardPatrolTasksUseCase, StartGuardPatrolSessionUseCase
from operations.models import CaLamViec, LichTuanTraVanHanh, NhiemVuTuanTraCa, PhanCongCaTruc
from operations.tests.test_guard_patrol_domain import GuardPatrolDomainFixture


class GuardPatrolMultiShiftTest(GuardPatrolDomainFixture):
    def setUp(self):
        super().setUp()
        PhanCongCaTruc.objects.filter(pk=self.shift.pk).delete()
        self.morning = CaLamViec.objects.create(
            ten_ca="Ca sáng multi",
            gio_bat_dau=time(6, 0),
            gio_ket_thuc=time(14, 0),
            tenant_id=self.tenant_id,
        )
        self.afternoon = CaLamViec.objects.create(
            ten_ca="Ca chiều multi",
            gio_bat_dau=time(14, 0),
            gio_ket_thuc=time(22, 0),
            tenant_id=self.tenant_id,
        )
        self.night = CaLamViec.objects.create(
            ten_ca="Ca đêm multi",
            gio_bat_dau=time(22, 0),
            gio_ket_thuc=time(6, 0),
            tenant_id=self.tenant_id,
        )

    def _aware_today(self, hour, minute=0):
        raw = datetime.combine(timezone.localdate(), time(hour, minute))
        return timezone.make_aware(raw, timezone.get_current_timezone())

    def _create_shift(self, ca, ngay=None):
        return PhanCongCaTruc.objects.create(
            nhan_vien=self.guard,
            vi_tri_chot=self.post,
            ca_lam_viec=ca,
            ngay_truc=ngay or timezone.localdate(),
            tenant_id=self.tenant_id,
        )

    def _create_schedule_for_ca(self, ca):
        return LichTuanTraVanHanh.objects.create(
            muc_tieu=self.site,
            vi_tri_chot=self.post,
            ca_lam_viec=ca,
            tuyen_tuan_tra=self.route,
            tan_suat_luot_bat_buoc=1,
            khung_gio_bat_dau=ca.gio_bat_dau,
            khung_gio_ket_thuc=ca.gio_ket_thuc,
            grace_minutes=15,
            yeu_cau_gps=False,
            yeu_cau_anh=False,
            tenant_id=self.tenant_id,
        )

    def test_selects_current_shift_when_guard_has_two_shifts_today(self):
        morning_shift = self._create_shift(self.morning)
        afternoon_shift = self._create_shift(self.afternoon)
        self._create_schedule_for_ca(self.morning)
        self._create_schedule_for_ca(self.afternoon)
        now = self._aware_today(15, 0)

        with patch("operations.application.guard_patrol_use_cases.timezone.now", return_value=now):
            context = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user, at=now)

        self.assertEqual(context["ca_hien_tai"], afternoon_shift)
        self.assertEqual(len(context["nhiem_vu_tuan_tra"]), 1)
        self.assertEqual(context["nhiem_vu_tuan_tra"][0].phan_cong_ca_truc_id, afternoon_shift.pk)
        self.assertFalse(NhiemVuTuanTraCa.objects.filter(phan_cong_ca_truc=morning_shift).exists())

    def test_completed_morning_shift_does_not_enable_legacy_fallback_for_afternoon(self):
        self._create_shift(self.morning)
        afternoon_shift = self._create_shift(self.afternoon)
        self._create_schedule_for_ca(self.afternoon)
        now = self._aware_today(15, 0)

        with patch("operations.application.guard_patrol_use_cases.timezone.now", return_value=now):
            context = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user, at=now)
            task = context["nhiem_vu_tuan_tra"][0]
            task.trang_thai = NhiemVuTuanTraCa.TrangThai.COMPLETED_VALID
            task.save(update_fields=["trang_thai", "updated_at"])
            context_after = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user, at=now)

        self.assertEqual(context_after["ca_hien_tai"], afternoon_shift)
        self.assertFalse(context_after["legacy_fallback_allowed"])
        self.assertEqual(context_after["lo_trinhs"], [])
        self.assertEqual(context_after["nhiem_vu_tuan_tra"][0].trang_thai, NhiemVuTuanTraCa.TrangThai.COMPLETED_VALID)

    def test_cross_midnight_shift_from_yesterday_is_current_after_midnight(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        night_shift = self._create_shift(self.night, ngay=yesterday)
        self._create_schedule_for_ca(self.night)
        now = self._aware_today(2, 0)

        with patch("operations.application.guard_patrol_use_cases.timezone.now", return_value=now):
            context = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user, at=now)

        self.assertEqual(context["ca_hien_tai"], night_shift)
        self.assertEqual(context["nhiem_vu_tuan_tra"][0].phan_cong_ca_truc_id, night_shift.pk)

    def test_cannot_start_task_outside_current_shift_window(self):
        morning_shift = self._create_shift(self.morning)
        self._create_schedule_for_ca(self.morning)
        # Materialize during morning, then try to start at afternoon time.
        morning_now = self._aware_today(7, 0)
        with patch("operations.application.guard_patrol_use_cases.timezone.now", return_value=morning_now):
            task = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user, at=morning_now)["nhiem_vu_tuan_tra"][0]

        afternoon_now = self._aware_today(15, 0)
        with patch("operations.application.guard_patrol_use_cases.timezone.now", return_value=afternoon_now):
            with self.assertRaises((PermissionDenied, ValidationError)):
                StartGuardPatrolSessionUseCase.execute(self.guard, task.pk)

        self.assertEqual(task.phan_cong_ca_truc_id, morning_shift.pk)
