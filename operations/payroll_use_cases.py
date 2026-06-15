# -*- coding: utf-8 -*-
"""
Proxy for Accounting Use Cases.
Reason: Business logic for Payroll has been moved to module `accounting` 
per Clean Architecture standards (v2.1.0).
"""

from accounting.application.payroll_use_cases import (
    CalculatePayrollUseCase, 
    AuditPayrollUseCase
)