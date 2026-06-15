# -*- coding: utf-8 -*-
"""Legacy compatibility wrapper for guard patrol use cases.

Guard Patrol is now owned by ``operations``. This module intentionally keeps the
old import path alive for one transition release because existing views/tests and
bookmarks may still import ``inspection.application.patrol_use_cases``.

Do not add new business logic here. Add canonical guard patrol logic in
``operations.application.guard_patrol_use_cases``.
"""

from operations.application.guard_patrol_use_cases import (  # noqa: F401
    CompleteGuardPatrolSessionUseCase,
    CompletePatrolSessionUseCase,
    GuardPatrolComplianceUseCase,
    ListGuardPatrolTasksUseCase,
    MarkMissedGuardPatrolTasksUseCase,
    MaterializeGuardPatrolTasksUseCase,
    RecordGuardPatrolCheckpointUseCase,
    RecordPatrolCheckpointUseCase,
    StartGuardPatrolSessionUseCase,
    StartPatrolSessionUseCase,
)
