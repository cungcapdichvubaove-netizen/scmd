# -*- coding: utf-8 -*-
"""Operational job tests for guard patrol materialization and MISSED persistence."""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.utils import timezone

from main.models import AuditLog
from operations.application.guard_patrol_use_cases import (
    MarkMissedGuardPatrolTasksUseCase,
    MaterializeGuardPatrolTasksUseCase,
    _is_shift_checked_in,
)
from operations.models import NhiemVuTuanTraCa
from operations.tests.test_guard_patrol_domain import GuardPatrolDomainFixture


class GuardPatrolOperationalJobsTest(GuardPatrolDomainFixture):
    def test_materialize_command_creates_tasks_and_audits_system_actor(self):
        self._create_schedule(frequency=2, require_gps=False)
        stdout = StringIO()

        call_command(
            "materialize_guard_patrol_tasks",
            target_date=timezone.localdate().isoformat(),
            stdout=stdout,
        )

        tasks = list(NhiemVuTuanTraCa.objects.order_by("thu_tu_luot"))
        self.assertEqual(len(tasks), 2)
        create_audit = AuditLog.objects.filter(model_name="NhiemVuTuanTraCa").earliest("timestamp")
        self.assertEqual(create_audit.changes["actor_type"], "system")
        self.assertEqual(create_audit.changes["reason"], "SYSTEM_MATERIALIZATION_JOB")
        self.assertEqual(create_audit.changes["phan_cong_ca_truc_id"], self.shift.pk)
        summary_audit = AuditLog.objects.get(model_name="GuardPatrolMaterializationJob")
        self.assertEqual(summary_audit.changes["created_task_count"], 2)
        self.assertIn("created_tasks=2", stdout.getvalue())

    def test_mark_missed_use_case_persists_state_and_audits_job(self):
        self._create_schedule(frequency=1, require_gps=False)
        MaterializeGuardPatrolTasksUseCase.execute_for_date(
            target_date=timezone.localdate(),
            system_actor_label="system.materialize_guard_patrol_tasks",
        )
        task = NhiemVuTuanTraCa.objects.get()
        task.grace_deadline = timezone.now() - timedelta(minutes=5)
        task.save(update_fields=["grace_deadline", "updated_at"])

        summary = MarkMissedGuardPatrolTasksUseCase.execute(
            target_date=timezone.localdate(),
            now=timezone.now(),
            system_actor_label="system.mark_missed_guard_patrol_tasks",
        )

        task.refresh_from_db()
        self.assertEqual(task.trang_thai, NhiemVuTuanTraCa.TrangThai.MISSED)
        self.assertTrue(task.ly_do_huy_bo)
        self.assertEqual(summary["updated_task_count"], 1)
        update_audit = AuditLog.objects.filter(
            model_name="NhiemVuTuanTraCa",
            action=AuditLog.Action.UPDATE,
        ).latest("timestamp")
        self.assertEqual(update_audit.changes["reason"], "SYSTEM_MARK_MISSED_JOB")
        self.assertEqual(update_audit.changes["trang_thai"]["new"], NhiemVuTuanTraCa.TrangThai.MISSED)
        summary_audit = AuditLog.objects.get(model_name="GuardPatrolMarkMissedJob")
        self.assertEqual(summary_audit.changes["updated_task_count"], 1)

    def test_is_shift_checked_in_returns_false_when_attendance_missing(self):
        self.assertFalse(_is_shift_checked_in(self.shift))

    def test_is_shift_checked_in_does_not_swallow_unexpected_errors(self):
        class ExplodingShift:
            @property
            def chamcong(self):
                raise RuntimeError("unexpected relation error")

        with self.assertRaises(RuntimeError):
            _is_shift_checked_in(ExplodingShift())
