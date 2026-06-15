# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
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
=======
Compatibility exports for legacy imports.

SSOT note:
- `main.models.AuditLog` is the single authoritative audit model.
- `main.models.WorkerHeartbeat` is the single authoritative worker monitor model.
"""

from main.models import AuditLog, WorkerHeartbeat

__all__ = ["AuditLog", "WorkerHeartbeat"]
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
