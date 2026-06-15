# -*- coding: utf-8 -*-
"""Shift management use cases.

Dedicated compatibility surface for deletion regression tests and service callers.
The actual scheduling mutation logic is centralized in ManageShiftAssignmentUseCase.
"""

from django.conf import settings

from operations.application.scheduling_use_cases import ManageShiftAssignmentUseCase


class DeleteShiftUseCase:
    """Delete a shift assignment through the scheduling SSOT and create AuditLog."""

    @staticmethod
    def execute(*, shift_id, actor_user, reason=None, tenant_id=None):
        return ManageShiftAssignmentUseCase.execute(
            action="DELETE",
            actor_user=actor_user,
            reason=reason,
            delete_old_id=shift_id,
            tenant_id=tenant_id or settings.SCMD_ORGANIZATION_ID,
        )
