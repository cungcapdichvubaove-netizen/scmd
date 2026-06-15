# ACCESS_SCOPE_DECISION_RECORD.md — SCMD Pro Access Scope ADR

Version: 1.0.0  
Status: Authoritative decision log for Phase 1 hardening  
Updated: 2026-06-08  
Scope: Access Scope, Object-level Authorization, Delegation, Historical Scope

---

## Purpose

This document locks architecture decisions required before coding Phase 1 Access Scope Hardening. AI/coder agents must not choose alternate model locations, module names, response payloads, or admin enforcement strategies without updating this ADR and the implementation contract.

---

## ADR-001 — AccessDelegation module location

Decision: when delegation is implemented, it must use a dedicated Django app/module named `delegation`.

Authoritative files:

```text
delegation/models.py::AccessDelegation
delegation/application/delegation_use_cases.py
delegation/access_policies.py
delegation/admin.py
```

Current release note:

- `AccessDelegation` chưa được triển khai trong codebase hiện tại.
- Tài liệu này khóa hướng kiến trúc để tránh implement nửa vời ở app khác.

Rationale:

- Delegation is not a temporary role assignment.
- Delegation has its own lifecycle: request, approve, activate, revoke, expire.
- Audit must preserve delegator, delegatee, scope, permission set and validity window.

Forbidden:

- Do not implement delegation by sharing passwords.
- Do not implement delegation by temporary superuser status.
- Do not store delegation as unstructured JSON in user profile.
- Do not create parallel `AccessDelegation` models in `main`, `users`, or `operations`.

---

## ADR-002 — NhanVienRegionAssignment model location

Decision: keep the current region-scope implementation in `users/models_assignment.py` and do not introduce a separate site-assignment model in this release.

Authoritative model:

```text
users/models_assignment.py::NhanVienRegionAssignment
```

Rationale:

- Staff assignment is part of staff lifecycle and HR/operations handoff.
- It must support historical region scope through `Region`, `NhanVienRegionAssignment`, `CoHoiKinhDoanh.region`, and legacy `MucTieu.quan_ly_vung` fallback.
- It must not be reduced to `NhanVien.current_region`.

Forbidden:

- Do not use a single `current_region` field as SSOT.
- Do not infer historical staff-region assignment only from the latest shift.
- Do not create duplicate assignment tables in `operations` without approved ADR.

---

## ADR-003 — PayrollAdjustment model location

Decision: implement retroactive payroll adjustment in `accounting/models.py`.

Authoritative model:

```text
accounting/models.py::PayrollAdjustment
```

Rationale:

- Payroll adjustment belongs to the accounting/payroll subsystem.
- Locked/paid payroll detail must remain immutable.
- Retroactive corrections must create adjustment records rather than editing old `ChiTietLuong`.

Forbidden:

- Do not unlock a paid payroll period for normal retroactive correction.
- Do not edit `ChiTietLuong` directly after `LOCKED` or `PAID` except through a documented emergency correction with audit.
- Do not create ad hoc adjustment fields on unrelated models.

---

## ADR-004 — PolicyResult response format

Decision: all policy denial responses use `core/policy_result.py::PolicyResult` and the standard API payload.

Authoritative file:

```text
core/policy_result.py
```

Required response:

```json
{
  "success": false,
  "error_code": "ERR_SCOPE_STAFF_OUT_OF_SCOPE",
  "message": "User-facing business message",
  "details": {},
  "request_id": "..."
}
```

Client rule:

- Mobile app branches on `error_code`.
- Web UI renders `message` and shows next-step guidance.
- Low-privilege clients must not learn whether hidden objects exist.

---

## ADR-005 — Admin enforcement strategy

Decision: Django Admin/Jazzmin must enforce object scope. Admin is not a bypass.

Required enforcement points:

```text
ModelAdmin.get_queryset()
ModelAdmin.has_view_permission()
ModelAdmin.has_change_permission()
ModelAdmin.has_delete_permission()
Admin actions
Inline admins
ForeignKey/autocomplete/search querysets
Sensitive export actions
```

Superuser rule:

- Superuser is a technical emergency role.
- Sensitive business actions still require audit.
- Export, lock/unlock, post/void, delete, payroll correction and GPS/photo access must be traceable.

---

## ADR-006 — Historical scope event-time rule

Decision: historical access is evaluated at the event's canonical business date/time.

Canonical rules:

| Data type | Scope date/time |
|---|---|
| Shift | local date of `shift.start_at` (`work_date`) |
| Overnight shift | date of `start_at`, not `end_at` |
| Attendance | associated shift `work_date`; fallback to check-in local date only if shift missing |
| Incident | incident occurred_at/opened_at |
| Patrol evidence | patrol session start time or checkpoint timestamp according to policy |
| Payroll | work date of source attendance/shift |
| Inventory issue/return | posted_at/effective document date |

Rule: a Site Commander keeps access to records generated while the staff/site was under their scope, even after the staff is transferred.

---

## ADR-007 — Superuser / technical admin business-action policy

Decision: technical admin access does not remove business audit obligations.

Rules:

- Technical admin can access admin console for emergency correction.
- Sensitive business data changes must create audit records.
- Production use of technical admin for business operations requires reason and ticket/reference.
- Technical admin should not be used for routine scheduling, payroll, incident closure or inventory posting.

---

## ADR-008 — Sensitive export and private media policy

Decision: sensitive exports and evidence media must use private access paths.

Required contract:

```text
docs/access_scope/SENSITIVE_DATA_EXPORT_CONTRACT.md
```

Applies to:

```text
Payroll, GPS, attendance photo, patrol photo, incident evidence, employee profile, CCCD, bank account, personnel report, sensitive Excel/PDF exports.
```

---

## Change policy

Any change to these decisions must update:

```text
docs/access_scope/ACCESS_SCOPE_AUTHORIZATION_CONTRACT.md
docs/access_scope/ACCESS_SCOPE_IMPLEMENTATION_ROADMAP.md
docs/access_scope/ACCESS_SCOPE_TEST_MATRIX.md
DOCUMENTATION.md
WHITEPAPER.md
.cursorrules
```
