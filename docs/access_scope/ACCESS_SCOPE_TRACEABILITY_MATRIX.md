# ACCESS_SCOPE_TRACEABILITY_MATRIX.md — SCMD Pro Access Scope Traceability Matrix

Version: 1.0.0  
Status: Mandatory implementation traceability for Phase 1 Access Scope hardening  
Updated: 2026-06-08  
Scope: Map authorization contract rules to files, tests and release gates.

---

## Purpose

This matrix connects:

```text
Rule / contract requirement
-> files that must be implemented or reviewed
-> mandatory tests
-> release gate that blocks shipment
```

AI/coder agents must use this file before changing runtime code. A Phase 1 implementation PR is incomplete if it changes scope-sensitive behavior without mapping the change to this matrix.

---

## Traceability table

| Rule / requirement | Primary files to implement or review | Mandatory tests | Release gate |
|---|---|---|---|
| PolicyResult stable denial contract | `core/policy_result.py`, API/HTMX response helpers | `AS-UX-004` | Access-scope gate |
| Scope resolver combines direct, delegated, historical and override scope | `core/access_scope.py`, `delegation/application/delegation_use_cases.py`, `users/models_assignment.py` | `AS-STAFF-*`, `AS-DELEG-*`, `AS-HIST-*` | Access-scope gate |
| Staff visibility must be object-scoped | `users/access_policies.py`, `users/views.py`, `users/admin.py`, staff serializers/search endpoints | `AS-STAFF-001..005`, `AS-ADMIN-001`, `AS-API-LEAK-001` | Admin authorization gate + Access-scope gate |
| Site visibility must be object-scoped | `clients/access_policies.py`, `clients/views.py`, `clients/admin.py`, site dropdown/autocomplete | `AS-STAFF-002`, `AS-ADMIN-004` | Admin authorization gate |
| Shift scheduling must check staff + site + post scope | `operations/access_policies.py`, `operations/application/*scheduling*`, `operations/views.py`, `operations/admin.py` | `AS-SHIFT-001..006`, `AS-CONC-001` | Access-scope gate + Import/concurrency gate |
| Temporary delegation grants scoped, time-bounded access | `delegation/models.py`, `delegation/application/delegation_use_cases.py`, `core/access_scope.py`, `delegation/admin.py` | `AS-DELEG-001..006`, `AS-DELEG-EXPIRED-001` | Access-scope gate |
| Delegatee inherits delegator override level only inside boundary | `core/access_scope.py`, `delegation/application/delegation_use_cases.py`, override policy helpers | `AS-DELEG-006`, `AS-CONC-001` | Override/concurrency gate |
| Historical scope uses event time and night-shift work_date | `users/models_assignment.py`, `users/access_policies.py`, `operations/access_policies.py`, payroll/attendance reconciliation | `AS-HIST-001..005`, `AS-SHIFT-006` | Migration gate + Access-scope gate |
| NhanVienRegionAssignment backfill must be verified | `users/models_assignment.py`, migration files, `docs/access_scope/ACCESS_SCOPE_MIGRATION_BACKFILL_PLAN.md` | backfill SQL verification + `AS-HIST-*` | Migration gate |
| Payroll locked/paid data must use PayrollAdjustment | `accounting/models.py`, `accounting/application/*payroll*`, payroll admin/actions | `AS-PAY-004` | Data integrity gate |
| Admin list/change/delete must enforce object scope | `*/admin.py`, shared admin mixins if introduced | `AS-ADMIN-001`, `AS-ADMIN-002` | Admin authorization gate |
| Admin bulk actions must check every object | `*/admin.py`, import/export admin actions | `AS-ADMIN-003` | Admin authorization gate |
| Admin FK/autocomplete must be scoped | `*/admin.py`, autocomplete views/widgets | `AS-ADMIN-004` | Admin authorization gate |
| Superuser business actions still require audit | admin actions, export actions, sensitive mutation actions | `AS-ADMIN-005` | Admin authorization gate + Sensitive export gate |
| Sensitive export requires permission, reason and audit | `reports/access_policies.py`, `reports/views.py`, `accounting/*export*`, `users/views.py`, `inventory/views.py` | `AS-EXPORT-001`, `AS-EXPORT-002`, `SMOKE-EXPORT-001` | Sensitive export and private media gate |
| Sensitive media must not be public URL | protected media views/storage helpers, attendance/photo/report templates | `AS-MEDIA-001` | Sensitive export and private media gate |
| CSV/import must be scoped per row | import views, import resources, admin import/export resources | `AS-IMPORT-001` | Import/concurrency gate |
| API detail endpoints must not leak object existence | DRF viewsets, detail views, permission classes | `AS-API-LEAK-001` | API leak gate |
| Dashboard/workspace lists must use scoped data | `dashboard/application/*`, workspace resolver, dashboard views/templates | `SMOKE-DASH-001`, staff/site scope tests | Access-scope gate |
| Release package and validators must pass | `release_contract_check.py`, `scripts/release_contract_check.py`, packaging script | `SMOKE-RELEASE-001`, `SMOKE-009` | Release readiness gate |

---

## PR review checklist

For every access-scope PR, reviewers must confirm:

```text
- The PR references at least one row in this matrix.
- The implementation files match the authoritative ownership in ACCESS_SCOPE_DECISION_RECORD.md.
- The tests listed in the row are added or updated.
- Admin and import surfaces are considered when the model is exposed there.
- Sensitive export/media implications are considered if data includes payroll, GPS, photo, personnel, incident or inventory evidence.
- Release checklist gates are updated when a new class of sensitive workflow is introduced.
```

---

## Change control

Do not remove a row from this matrix to make implementation easier. If a rule no longer applies, update `ACCESS_SCOPE_DECISION_RECORD.md` first and record the reason.
