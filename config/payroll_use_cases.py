# -*- coding: utf-8 -*-
"""
Deprecated compatibility shim.

Payroll use cases now live under accounting.application.payroll_use_cases.
"""

from accounting.application.payroll_use_cases import AuditPayrollUseCase

__all__ = ["AuditPayrollUseCase"]
