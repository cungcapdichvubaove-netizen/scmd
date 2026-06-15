# -*- coding: utf-8 -*-
"""Dashboard read path must not create guard patrol tasks or audit rows."""

from django.utils import timezone

from main.models import AuditLog
from operations.application.guard_patrol_use_cases import GuardPatrolComplianceUseCase
from operations.models import NhiemVuTuanTraCa
from operations.tests.test_guard_patrol_domain import GuardPatrolDomainFixture


class GuardPatrolDashboardNoSideEffectTest(GuardPatrolDomainFixture):
    def test_compliance_read_does_not_materialize_tasks_or_audit(self):
        self._create_schedule(frequency=2)
        before_tasks = NhiemVuTuanTraCa.objects.count()
        before_audits = AuditLog.objects.count()

        summary = GuardPatrolComplianceUseCase.execute(
            tenant_id=self.tenant_id,
            target_date=timezone.localdate(),
        )

        self.assertEqual(summary["stats"]["total"], 0)
        self.assertEqual(NhiemVuTuanTraCa.objects.count(), before_tasks)
        self.assertEqual(AuditLog.objects.count(), before_audits)
