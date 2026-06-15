# -*- coding: utf-8 -*-
"""Workflow transition guard for SCMD business records.

Phase C deliberately keeps this policy lightweight and model-local: each
business record exposes ``ALLOWED_STATUS_TRANSITIONS`` and calls this helper from
``transition_status()``. Direct database/admin state mutations remain visible to
existing code, but approved workflow paths now have a hard transition matrix and
an audit trail.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class WorkflowTransitionPolicy:
    """Validate finite-state transitions for business-domain records."""

    @staticmethod
    def validate_transition(model_name: str, old_status: str, new_status: str, allowed_transitions: dict) -> None:
        if old_status == new_status:
            return
        allowed = set(allowed_transitions.get(old_status, set()))
        if new_status not in allowed:
            raise ValidationError(
                _("Chuyển trạng thái không hợp lệ cho %(model)s: %(old)s → %(new)s.")
                % {"model": model_name, "old": old_status, "new": new_status}
            )
