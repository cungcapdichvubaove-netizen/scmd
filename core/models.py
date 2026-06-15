# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: core/models.py
Description: Compatibility exports for legacy imports (Technical SSOTs).
             Aligning with WHITEPAPER.md Section 4 (F-010).

Authoritative SSOTs:
- Audit Log: main.models.AuditLog (Lưu vết kiểm toán)
- Worker Health: main.models.WorkerHeartbeat (Theo dõi sức khỏe hệ thống)
- Company Information: main.models.CompanyInfo (Thông tin công ty)
"""

from main.models import AuditLog, WorkerHeartbeat, CompanyInfo

__all__ = [
    "AuditLog",
    "WorkerHeartbeat",
    "CompanyInfo",
]
