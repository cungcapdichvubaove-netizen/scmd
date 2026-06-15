# -*- coding: utf-8 -*-
"""Legacy fallback lock tests for operations-owned guard patrol."""

from django.core.exceptions import ValidationError

from operations.application.guard_patrol_use_cases import ListGuardPatrolTasksUseCase, StartGuardPatrolSessionUseCase
from operations.models import NhiemVuTuanTraCa
from operations.tests.test_guard_patrol_domain import GuardPatrolDomainFixture


class GuardPatrolLegacyFallbackLockTest(GuardPatrolDomainFixture):
    def test_active_schedule_completed_task_does_not_show_legacy_fallback(self):
        self._create_schedule(frequency=1, require_gps=False)
        context = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user)
        task = context["nhiem_vu_tuan_tra"][0]
        task.trang_thai = NhiemVuTuanTraCa.TrangThai.COMPLETED_VALID
        task.save(update_fields=["trang_thai", "updated_at"])

        context = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user)

        self.assertTrue(context["uses_operations_schedule"])
        self.assertFalse(context["legacy_fallback_allowed"])
        self.assertEqual(context["lo_trinhs"], [])
        self.assertEqual(context["nhiem_vu_tuan_tra"][0].trang_thai, NhiemVuTuanTraCa.TrangThai.COMPLETED_VALID)

    def test_active_schedule_missed_task_does_not_show_legacy_fallback(self):
        self._create_schedule(frequency=1, require_gps=False)
        context = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user)
        task = context["nhiem_vu_tuan_tra"][0]
        task.trang_thai = NhiemVuTuanTraCa.TrangThai.MISSED
        task.save(update_fields=["trang_thai", "updated_at"])

        context = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user)

        self.assertTrue(context["uses_operations_schedule"])
        self.assertFalse(context["legacy_fallback_allowed"])
        self.assertEqual(context["lo_trinhs"], [])
        self.assertEqual(context["nhiem_vu_tuan_tra"][0].trang_thai, NhiemVuTuanTraCa.TrangThai.MISSED)

    def test_no_active_schedule_allows_legacy_fallback_for_transition(self):
        context = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user)

        self.assertFalse(context["uses_operations_schedule"])
        self.assertTrue(context["legacy_fallback_allowed"])
        self.assertIn(self.route, context["lo_trinhs"])

    def test_start_legacy_route_is_blocked_when_active_schedule_exists(self):
        self._create_schedule(frequency=1, require_gps=False)
        context = ListGuardPatrolTasksUseCase.execute(self.guard, actor=self.guard_user)
        task = context["nhiem_vu_tuan_tra"][0]
        task.trang_thai = NhiemVuTuanTraCa.TrangThai.COMPLETED_VALID
        task.save(update_fields=["trang_thai", "updated_at"])

        with self.assertRaises(ValidationError):
            StartGuardPatrolSessionUseCase.execute(self.guard, self.route.pk)
