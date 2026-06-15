# -*- coding: utf-8 -*-
"""Backward-compatible shim for violation use cases.

The single source of truth lives in ``inspection.application.violation_use_cases``.
Keep this module import-only so legacy imports cannot diverge from runtime behavior.
"""

from inspection.application.violation_use_cases import CreateViolationUseCase

__all__ = ["CreateViolationUseCase"]
