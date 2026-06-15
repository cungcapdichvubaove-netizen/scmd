# -*- coding: utf-8 -*-
"""
Runtime guard context for sensitive data mutations.

This module intentionally has no Django ORM dependency. It is used by model-level
integrity guards to distinguish audited application-layer mutations from
accidental direct writes.
"""

from contextlib import contextmanager
from contextvars import ContextVar

_attendance_mutation_reason = ContextVar("attendance_mutation_reason", default=None)


@contextmanager
def allow_attendance_mutation(reason: str):
    """
    Temporarily allow sensitive ChamCong field updates.

    The caller is still responsible for creating the corresponding AuditLog or
    ChamCongAdjustment record in the same application-layer transaction.
    """
    token = _attendance_mutation_reason.set(reason or "AUDITED_ATTENDANCE_MUTATION")
    try:
        yield
    finally:
        _attendance_mutation_reason.reset(token)


def is_attendance_mutation_allowed() -> bool:
    return bool(_attendance_mutation_reason.get())


def current_attendance_mutation_reason():
    return _attendance_mutation_reason.get()
