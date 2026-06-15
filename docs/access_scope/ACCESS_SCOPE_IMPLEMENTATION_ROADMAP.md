# ACCESS_SCOPE_IMPLEMENTATION_ROADMAP.md — SCMD Pro Operational Authorization Roadmap

Version: 1.2.0  
Status: Phase 1 hardening roadmap  
Updated: 2026-06-08

---

## Non-negotiable implementation order

Phase 1 Access Scope hardening must be implemented in this order. AI/coder agents must not skip ahead or create temporary substitutes when a prerequisite phase is missing.

| Order | Required foundation | Why it must come first |
|---:|---|---|
| 1 | `core/policy_result.py` | All policies and UI/API denials need one stable result shape and error code registry. |
| 2 | `core/access_scope.py` | Every visibility/action policy must resolve direct, delegated, historical and override scope through one resolver. |
| 3 | Direct visibility policies | `visible_sites()` and `visible_staff()` must exist before screens, admin lists or exports are scoped. |
| 4 | Admin queryset scope | `/admin/` must not remain a bypass while user-facing screens are hardened. |
| 5 | Action policies | POST/actions must enforce object-level permission after list visibility is scoped. |
| 6 | Temporary delegation | Delegation is an additional scope source; it must plug into the resolver, not bypass it. |
| 7 | Historical staff-region assignment | Attendance/payroll/incident history must use event time and assignment history, not only current scope. |
| 8 | Sensitive export/private media | Exports and evidence downloads must enforce the same scope and audit model. |
| 9 | Migration/backfill | Data migration must occur only after model ownership, policy behavior and verification SQL are locked. |
| 10 | Release gate | Full test matrix, smoke tests and release validators must pass before shipping. |

Forbidden sequencing:

```text
Do not implement delegation before PolicyResult and ScopeResolver.
Do not harden only UI while admin remains unscoped.
Do not add a separate site-assignment model before the region-scope backfill assumptions are documented and approved.
Do not expose sensitive export/private media before scope-aware audit exists.
```


## Objective

Implement operational authorization without changing SCMD Pro away from the current single-organization hardened layered monolith.

Priority domains:

```text
staff visibility
site visibility
shift scheduling
dispatch / transfer
task assignment
incident handling
patrol evidence
inventory issue/return
payroll visibility/export
```

---

## Phase A — Foundation: PolicyResult + Scope Resolver

Deliverables:

```text
core/policy_result.py
core/access_scope.py
core/tests/test_policy_result.py
core/tests/test_access_scope.py
```

Required components:

```text
PolicyResult
ScopeLevel
ScopeType
ScopeSource
AccessDeniedReason / error code registry
```

Acceptance:

```text
PolicyResult supports allow/deny with code, message, details.
ScopeLevel has ordered hierarchy.
Unit tests cover allow/deny and hierarchy comparison.
Policy denial codes match ACCESS_SCOPE_AUTHORIZATION_CONTRACT.md registry.
```

---

## Phase B — Direct Visibility Policies

Deliverables:

```text
clients/access_policies.py
users/access_policies.py
operations/access_policies.py
```

Required policies:

```text
SiteVisibilityPolicy.visible_sites(user, at_time=None)
StaffVisibilityPolicy.visible_staff(user, at_time=None)
StaffVisibilityPolicy.visible_staff_for_scheduling(user, site, at_date=None)
ShiftVisibilityPolicy.visible_shifts(user, date_range=None)
```

Target screens:

```text
weekly schedule dashboard
shift edit form
staff list
site list
mobile shift list
```

Acceptance:

```text
Site Commander A sees only Site A staff.
Area Manager sees only sites in managed area.
Guard sees only own shifts.
All querysets are filtered at database level.
```

---

## Phase C — Scheduling and Dispatch Action Policies

Deliverables:

```text
operations/access_policies.py
operations/application/dispatch_use_cases.py
operations/tests/test_shift_scope_policy.py
operations/tests/test_dispatch_policy.py
```

Required checks:

```text
can_assign_shift(user, staff, site, shift_date)
can_update_shift(user, shift)
can_delete_shift(user, shift)
can_transfer_staff(user, staff, from_site, to_site, effective_date)
```

Acceptance:

```text
Permission decorator alone is not enough.
Action policy validates target staff/site/shift.
Denied cases return contextual PolicyResult.
Night shifts use shift.start_at local date as canonical work_date.
Audit records scope level and delegation when applicable.
```

---

## Phase D — Temporary Delegation

Deliverables:

```text
delegation/models.py
delegation/application/delegation_use_cases.py
delegation/admin.py
delegation/tests/test_temporary_delegation.py
```

MVP workflows:

```text
view site staff
schedule shift
view/open incident at delegated site
manpower/alive-check management
```

Acceptance:

```text
Delegation grants scope only inside valid time window.
Expired delegation is ignored even before cleanup job runs.
Audit records delegation_id and delegator_user.
Delegatee inherits delegator override level only inside delegated scope/permission/time window.
User cannot delegate broader scope than they own.
Emergency delegation can be created by Area Manager / Operations Department.
```

---

## Phase E — Historical Scope

Deliverables:

```text
users/models_assignment.py
users/application/staff_assignment_use_cases.py
users/access_policies.py historical checks
```

Required model:

```text
NhanVienRegionAssignment
- nhan_vien
- muc_tieu
- role_at_site
- starts_at
- ends_at
- status
- assigned_by
- reason
- tenant_id
```

Acceptance:

```text
Manager of Site A can view records created while staff belonged to Site A.
Manager of Site A can view overnight shift that started while staff belonged to Site A even if it ended next day.
Manager of Site A cannot view records after staff moved to Site B.
Payroll uses shift/event start date, not current assignment only.
```

---

## Phase F — Override Policy

Deliverables:

```text
core/access_scope.py hierarchy helpers
operations/application/change_request_use_cases.py
operations/tests/test_override_policy.py
```

Acceptance:

```text
Lower scope cannot silently overwrite higher-scope locked decisions.
Site Commander must create request when changing Area Manager decision.
Payroll lock blocks operational edits unless adjustment/reopen workflow is used.
Delegated actor override comparison uses delegator scope level within delegation boundary.
```

---

## Phase G — Workspace Simplification

Deliverables:

```text
dashboard/application/workspace_resolver.py
dashboard/templates/dashboard/workspaces/*.html
```

Target workspaces:

```text
GuardWorkspace
SiteCommanderWorkspace
AreaManagerWorkspace
OperationsWorkspace
HRWorkspace
PayrollWorkspace
InventoryWorkspace
ExecutiveWorkspace
```

Acceptance:

```text
Users see only relevant dashboard cards and lists.
Workspace visibility matches backend policy.
No dashboard card depends on unscoped query.
```

---

## Phase H — Payroll Adjustment and Data Retention Hardening

Deliverables:

```text
accounting/models.py
accounting/application/payroll_adjustment_use_cases.py
main/application/archive_policy.py + documented archive job runbook
reports/tests/test_payroll_adjustment_export.py
```

Acceptance:

```text
LOCKED/PAID payroll records are not directly edited.
Retroactive changes create PayrollAdjustment records.
Audit and export explain before/after payroll impact.
Retention/archive policy is documented for audit, GPS/photo, patrol, incident, payroll and assignment history.
Archive strategy preserves historical scope and dispute traceability.
```

---

## Phase 1 Access Scope Done Criteria

Phase 1 access-scope hardening is complete only when:

```text
All test cases in ACCESS_SCOPE_TEST_MATRIX.md pass for implemented phases.
No user-facing view/API/admin action uses unscoped queryset for staff/site/shift/incident/patrol/inventory/payroll data.
PolicyResult + error code registry is used for sensitive deny workflows.
SiteVisibilityPolicy and StaffVisibilityPolicy are SSOT for visibility queries.
ShiftAssignmentPolicy and DispatchPolicy enforce object-level actions.
Temporary delegation model/use cases are deployed with audit context.
Historical scope is enforced for attendance, payroll reconciliation, incidents and overnight shifts.
Override policy prevents lower-scope silent overwrite of higher-scope decisions.
PayrollAdjustment exists before relaxing payroll lock rules.
Release checklist and smoke tests pass in Docker/PostGIS staging.
```

---

## Deployment rules

```text
Each phase requires migration plan if models change.
Each phase requires tests for allow and deny cases.
Do not remove legacy behavior without shim unless import scan is clean.
Do not implement delegation by shared passwords or temporary superuser status.
Do not broaden scope silently for convenience.
Do not ship a phase if its mapped TEST_MATRIX cases fail.
```


---

## Architecture decisions locked before coding

Phase 1 implementation must follow `docs/access_scope/ACCESS_SCOPE_DECISION_RECORD.md`. Do not create alternate model locations.

| Concern | Locked location |
|---|---|
| PolicyResult | `core/policy_result.py` |
| Scope resolver | `core/access_scope.py` |
| AccessDelegation | `delegation/models.py` |
| Delegation use cases | `delegation/application/delegation_use_cases.py` |
| NhanVienRegionAssignment | `users/models_assignment.py` |
| PayrollAdjustment | `accounting/models.py` |
| Admin authorization contract | `docs/access_scope/ADMIN_AUTHORIZATION_CONTRACT.md` |
| Migration/backfill plan | `docs/access_scope/ACCESS_SCOPE_MIGRATION_BACKFILL_PLAN.md` |
| Sensitive export/media privacy | `docs/access_scope/SENSITIVE_DATA_EXPORT_CONTRACT.md` |

---

## Phase I — Admin authorization hardening

Scope:

```text
ModelAdmin queryset scoping
Object-level view/change/delete permission
Admin bulk actions
Inline admins
ForeignKey/autocomplete scoped querysets
Sensitive admin exports
Superuser audit boundary
```

Deliverables:

```text
Admin policy mixins
Targeted admin tests
Sensitive export reason/audit checks
No unscoped admin list/change views for business data
```

---

## Phase J — Sensitive export and private media hardening

Scope:

```text
Payroll exports
GPS/photo evidence
Employee profile exports
Incident reports
Patrol evidence exports
Inventory deduction exports
```

Deliverables:

```text
Private media/download views or signed URLs
Export audit payload standardization
Reason-required export flows
PII masking rules
Expiry/re-download audit
```

---

## Phase 1 Done Criteria

Phase 1 Access Scope hardening is complete only when all of the following are true:

- `PolicyResult` and standard error payloads are implemented and used by sensitive access policies.
- `core/access_scope.py` resolves direct, delegated and historical scope.
- `AccessDelegation` must be implemented in `delegation/models.py` with indexes and constraints from the contract before this phase can be marked complete.
- `NhanVienRegionAssignment` is deployed in `users/models_assignment.py` and historical scope is enforced for attendance/payroll.
- No user-facing view/API/dashboard/admin list uses unscoped global querysets for staff/site/shift/incident/patrol/inventory/payroll data.
- Delegation expiry/revocation is enforced at runtime, independent of cleanup jobs.
- Override policy blocks lower-scope silent overwrite of higher-scope decisions.
- Sensitive exports require permission, reason, audit and private storage.
- Admin authorization contract tests pass.
- Full `ACCESS_SCOPE_TEST_MATRIX.md` phase gates pass.
- Pre-release smoke tests pass.


## Traceability requirement

Every implementation PR must update or satisfy `docs/access_scope/ACCESS_SCOPE_TRACEABILITY_MATRIX.md`: rule, files touched, tests, and release gate must be traceable before review.
