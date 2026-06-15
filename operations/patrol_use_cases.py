# -*- coding: utf-8 -*-
"""Compatibility shim for operations guard patrol use cases.

Canonical business logic lives in ``operations.application.guard_patrol_use_cases``.
This module exists only for old internal imports that referenced
``operations.patrol_use_cases`` before the application-layer module was created.
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
