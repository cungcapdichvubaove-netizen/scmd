# ACCESS_SCOPE_TEST_MATRIX.md — Regression Matrix

Version: 1.1.0  
Status: Phase-gated regression matrix  
Updated: 2026-06-08

---

## Staff and site visibility

| ID | Phase | Scenario | Expected |
|---|---|---|---|
| AS-STAFF-001 | Phase B | Site Commander A views staff list | Only staff in Site A scope |
| AS-STAFF-002 | Phase B | Site Commander A searches staff from Site B | No result / 403 for object detail |
| AS-STAFF-003 | Phase B | Area Manager for Area 1 views staff | Staff from Area 1 sites only |
| AS-STAFF-004 | Phase B | Operations user views staff | Staff from allowed operations scope |
| AS-STAFF-005 | Phase B | Guard views staff | Only own profile if allowed |

## Shift scheduling

| ID | Phase | Scenario | Expected |
|---|---|---|---|
| AS-SHIFT-001 | Phase C | Site Commander A assigns Site A staff to Site A post | Allowed |
| AS-SHIFT-002 | Phase C | Site Commander A assigns Site B staff | Denied with contextual message |
| AS-SHIFT-003 | Phase F | Site Commander A edits Area Manager locked shift | Denied or change request required |
| AS-SHIFT-004 | Phase C | Area Manager edits Site A shift in area | Allowed |
| AS-SHIFT-005 | Phase C | Any user edits payroll-locked shift | Denied; adjustment/reopen workflow required |
| AS-SHIFT-006 | Phase C/E | Overnight shift starts at Site A before transfer and ends after midnight | Scope uses start_at/work_date; Site A commander can reconcile |

## Delegation

| ID | Phase | Scenario | Expected |
|---|---|---|---|
| AS-DELEG-001 | Phase D | Active delegate schedules within delegated site | Allowed; audit includes delegation id |
| AS-DELEG-002 | Phase D | Delegate schedules outside delegated site | Denied |
| AS-DELEG-003 | Phase D | Expired delegation used | Denied with `ERR_SCOPE_DELEGATION_EXPIRED` |
| AS-DELEG-004 | Phase D | Delegator tries to delegate broader scope than owned | Denied |
| AS-DELEG-005 | Phase D | Emergency delegation created by Area Manager | Allowed; audit records creator/approver |
| AS-DELEG-006 | Phase D/F | Delegate edits object inside delegation after Area Manager delegated scope | Override comparison uses delegator's scope level inside boundary |

## Historical scope

| ID | Phase | Scenario | Expected |
|---|---|---|---|
| AS-HIST-001 | Phase E | Site A commander views attendance while guard belonged to Site A | Allowed |
| AS-HIST-002 | Phase E | Site A commander views attendance after guard moved to Site B | Denied |
| AS-HIST-003 | Phase E | Payroll reconciliation uses shift start/work_date | Correct site scope by event date |
| AS-HIST-004 | Phase E | Incident history follows incident site/date | Correct historical visibility |
| AS-HIST-005 | Phase E | Guard has active assignments to Site A and Site B | User sees allowed shifts/tasks for both assigned sites; check-in still requires PhanCongCaTruc |

## Inventory and payroll

| ID | Phase | Scenario | Expected |
|---|---|---|---|
| AS-INV-001 | Phase B/C | Inventory user issues equipment to staff in allowed scope | Allowed |
| AS-INV-002 | Phase B | Inventory user views payroll | Denied |
| AS-PAY-001 | Phase B | Payroll user views payroll records | Allowed by payroll scope |
| AS-PAY-002 | Phase C | Payroll user dispatches staff | Denied |
| AS-PAY-003 | Phase C/H | Payroll export | Permission + audit required |
| AS-PAY-004 | Phase H | Retroactive change after payroll lock | Creates PayrollAdjustment; locked ChiTietLuong unchanged |

## Access denied UX and error codes

| ID | Phase | Scenario | Expected |
|---|---|---|---|
| AS-UX-001 | Phase A/C | User attempts out-of-scope shift assignment | Message includes staff, site, escalation path and stable error code |
| AS-UX-002 | Phase D | Delegate attempts outside scope | Message includes delegated scope and expiry |
| AS-UX-003 | Phase F | Lower scope attempts override | Message explains higher-scope lock/request path |
| AS-UX-004 | Phase A | API receives deny PolicyResult | Response includes `error_code`, user-friendly message and details safe for role |

## Pre-release smoke test checklist

| ID | Phase | Scenario | Expected |
|---|---|---|---|
| SMOKE-001 | All | Login page renders | SCMD Pro branding, no Tailwind CDN runtime |
| SMOKE-002 | All | Admin `/admin/` renders | No crash; CompanyInfo admin loads |
| SMOKE-003 | All | Dashboard opens for authorized operator | KPI data scoped; no demo-only numbers |
| SMOKE-004 | All | Guard mobile shift list | Guard sees own shifts only |
| SMOKE-005 | All | Guard check-in/check-out happy path | Audit created; GPS/photo policy enforced |
| SMOKE-006 | All | Export sensitive report | Permission + audit enforced |
| SMOKE-007 | All | Worker heartbeat / task queue health | Worker heartbeat visible, no task queue fatal error |
| SMOKE-008 | All | Release validators | `scripts/release_contract_check.py --audit-zip` and root proxy both PASS |
| SMOKE-009 | All | Static/package hygiene | No `media/`, `staticfiles/`, `__pycache__/`, `*.pyc`, destructive dev scripts in release ZIP |


---

## Admin, import, API leak and concurrency tests

| ID | Phase | Scenario | Expected result |
|---|---|---|---|
| AS-ADMIN-001 | Phase I | Site Commander A opens admin list for staff/shift/site data | Only objects in Site A scope are visible |
| AS-ADMIN-002 | Phase I | Site Commander A opens admin change URL for Site B object | 403 or not found; no object data leaked |
| AS-ADMIN-003 | Phase I | Admin bulk action selection includes out-of-scope object | Action rejects out-of-scope object and logs denial |
| AS-ADMIN-004 | Phase I | ForeignKey dropdown/autocomplete for staff in admin | Only scoped staff are returned |
| AS-ADMIN-005 | Phase I | Superuser exports payroll | Export succeeds only with audit/reason metadata |
| AS-API-LEAK-001 | Phase B/C | Low-privilege user requests out-of-scope detail endpoint | `ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE`, no existence leak |
| AS-IMPORT-001 | Phase C/E | CSV import assigns staff to out-of-scope site | Row rejected with scoped error; no partial unauthorized assignment |
| AS-CONC-001 | Phase F | Site Commander and Area Manager edit same shift | Override/concurrency rule enforced; lower scope cannot silently overwrite |
| AS-DELEG-EXPIRED-001 | Phase D | Delegation ended but cleanup has not marked EXPIRED | Runtime policy denies access |
| AS-MEDIA-001 | Phase J | User requests attendance/patrol photo outside scope | Denied; no public media URL leaked |
| AS-EXPORT-001 | Phase J | Payroll/GPS/personnel export without reason | Denied |
| AS-EXPORT-002 | Phase J | Authorized export with reason | Private file, audit row, expiry metadata |

---

## Pre-release smoke test checklist

| ID | Phase | Smoke test | Expected result |
|---|---|---|---|
| SMOKE-LOGIN-001 | All | Login page | Renders SCMD Pro branding, no Tailwind CDN runtime |
| SMOKE-ADMIN-001 | All | `/admin/` index | Renders without crash; scoped admin modules visible |
| SMOKE-DASH-001 | All | Operations dashboard | Loads KPI from scoped data, no demo hardcode |
| SMOKE-GUARD-001 | All | Guard mobile shift list | Shows only guard's shifts |
| SMOKE-ATT-001 | All | Check-in/check-out happy path | Creates attendance and audit log |
| SMOKE-EXPORT-001 | All | Sensitive export | Requires permission/reason and creates audit |
| SMOKE-WORKER-001 | All | Worker heartbeat | Worker health visible or documented unavailable in local |
| SMOKE-RELEASE-001 | All | Release validators | `release_contract_check.py` and script validator pass |
