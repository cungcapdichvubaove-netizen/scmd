# ACCESS_SCOPE_AUTHORIZATION_CONTRACT.md — SCMD Pro Access Scope & Operational Authorization Contract

Version: 1.2.0  
Status: Authoritative implementation contract for Phase 1 hardening  
Updated: 2026-06-08  
Scope: SCMD Pro single-organization hardened layered monolith

---

## 0. Purpose and boundary

This contract defines the authorization model for SCMD Pro workflows involving staff visibility, site visibility, shift scheduling, staff dispatch, task assignment, patrol, incidents, inventory issue/return, payroll visibility, export, dashboards, and operational workspaces.

SCMD Pro currently runs as a **single-organization hardened system**. The database field name `tenant_id` is legacy naming for fixed organization scope. It must resolve to `settings.SCMD_ORGANIZATION_ID`. It must not be interpreted as true SaaS tenant, dynamic tenant, subdomain tenant, request tenant, or customer tenant. Do not accept `tenant_id` from request payload, query string, form, serializer, or client-side state.

SCMD Pro must never rely on role names or menu hiding alone. Every sensitive operation must enforce:

```text
Authenticated account
+ business role / job title
+ operational data scope
+ object-level permission
+ contextual denial message
+ audit trail
```

This is mandatory because SCMD Pro manages attendance, GPS/photo evidence, incident responsibility, payroll, inventory, and staff movement.

---

## 0.1 Locked implementation decisions for Phase 1

This contract is implementation-grade. The following module and model ownership decisions are locked for Phase 1. AI/coder agents must not choose alternate locations without an approved ADR update.

| Concern | Authoritative location | Notes |
|---|---|---|
| `PolicyResult` and standard denial payloads | `core/policy_result.py` | SSOT for policy return values and API error serialization. |
| Access scope resolver | `core/access_scope.py` | Combines direct scope, delegated scope, historical scope and override level. |
| Access delegation model | Planned `delegation/models.py::AccessDelegation` | Target module only; current release chưa có app `delegation`, không được claim là deployed. |
| Delegation use cases | `delegation/application/delegation_use_cases.py` | Create, approve, activate, revoke, expire, and query active delegation. |
| Staff-region assignment history | `users/models_assignment.py::NhanVienRegionAssignment` | Historical and multi-region staff-to-region assignment SSOT. |
| Staff visibility policy | `users/access_policies.py` | Staff list and staff action visibility. |
| Site visibility policy | `clients/access_policies.py` | Site/post visibility and scope resolution. |
| Shift assignment policy | `operations/access_policies.py` | Shift create/update/delete and schedule visibility. |
| Patrol/inspection policy | `inspection/access_policies.py` | Patrol, QR evidence, inspection violation scope. |
| Inventory scope policy | `inventory/access_policies.py` | Warehouse/equipment scope and issue/return actions. |
| Task assignment policy | `workflow/access_policies.py` | Task assignee visibility and object-scope checks. |
| Payroll adjustment model | `accounting/models.py::PayrollAdjustment` | Controlled retroactive adjustment; do not create parallel adjustment model. |
| Sensitive export policy | `reports/access_policies.py` + `docs/access_scope/SENSITIVE_DATA_EXPORT_CONTRACT.md` | Export permissions, audit, masking, private storage. |

If a developer believes a location must change, create or update `docs/access_scope/ACCESS_SCOPE_DECISION_RECORD.md` before coding.

---

## 1. RBAC is not enough

RBAC answers:

```text
What type of function can this user perform?
```

Object scope answers:

```text
Which data objects may this user see or act on?
```

Example:

```text
A site commander at Site A may have `giao_ca_truc`.
That permission does not allow scheduling guards at Site B.
```

Every sensitive workflow must check both:

```text
has_permission(user, action)
has_object_scope(user, object, action_time)
```

---

## 2. Authorization layers

### 2.1 Authentication

Authentication identifies the account:

```text
User -> NhanVien
```

Authentication does not determine business scope.

### 2.2 Business role / job title

Business role determines what kind of work the user may perform.

| Role / job function | Examples |
|---|---|
| Guard | check-in, check-out, patrol, incident report |
| Site Commander | site roster, manpower, shift scheduling within site |
| Area Manager | multi-region operations in assigned area |
| Operations Department | cross-site dispatch, incident coordination |
| HR | staff records, recruitment, transfer process |
| Payroll | payroll, attendance reconciliation, lock period |
| Inventory | issue/return equipment, stock reconciliation |
| Executive | oversight, approval, reports |
| Technical Admin | technical console; business actions still audited |

### 2.3 Operational scope

Operational scope determines visible/actionable data.

| Scope level | Meaning |
|---|---|
| SELF | own data only |
| SITE | one or more assigned sites |
| REGION | sites in assigned region/area |
| OPERATIONS | operational sites according to department scope |
| HR | staff records according to HR policy |
| PAYROLL | attendance/payroll according to payroll policy |
| INVENTORY | stock/equipment according to warehouse policy |
| EXECUTIVE | global oversight according to executive policy |
| TECHNICAL | technical console; not blanket business override |

### 2.4 Action permission

Action permission determines the operation:

```text
view, create, update, delete, approve, reject, lock, unlock, export, dispatch, delegate
```

Each action must be evaluated against the target object.

---

## 3. PolicyResult and error code registry

Policy functions must return contextual results for user-facing workflows. Do not return only `True`/`False` for sensitive workflows.

Required structure:

```python
@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    code: str
    message: str
    details: dict[str, Any] | None = None
    delegation_id: int | None = None
    scope_level: str | None = None
```

### 3.1 Standard error code registry

Use stable error codes so web/mobile clients can map denial cases to UI behavior.

| Code | Meaning | Typical UI action |
|---|---|---|
| `ERR_SCOPE_STAFF_OUT_OF_SCOPE` | Target staff is outside user's visible/assignable staff scope | Show staff/site explanation and escalation path |
| `ERR_SCOPE_SITE_OUT_OF_SCOPE` | Target site/post is outside user's scope | Show managed site list or contact Area Manager |
| `ERR_SCOPE_SHIFT_OUT_OF_SCOPE` | Shift belongs to site/staff outside user's scope | Show shift site and required scope |
| `ERR_SCOPE_DELEGATION_REQUIRED` | User lacks direct scope but may request delegation | Offer request-delegation flow |
| `ERR_SCOPE_DELEGATION_EXPIRED` | Delegation exists but is expired | Offer renewal/request new delegation |
| `ERR_SCOPE_DELEGATION_OUT_OF_SCOPE` | Delegation scope does not cover target object | Show delegated scope and target mismatch |
| `ERR_SCOPE_HISTORICAL_OUT_OF_SCOPE` | User did not have scope at event time | Show event date and assignment period |
| `ERR_OVERRIDE_HIGHER_SCOPE_LOCK` | Lower scope attempts to edit higher-scope decision | Offer change-request workflow |
| `ERR_PAYROLL_LOCKED` | Payroll-locked data cannot be edited directly | Offer adjustment/reopen workflow |
| `ERR_EXPORT_PERMISSION_REQUIRED` | Sensitive export requires explicit permission | Show required permission or approval path |
| `ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE` | Object is missing or hidden by scope | Avoid leaking existence details to low-privilege users |



### 3.2 Standard API denial payload

All API and HTMX endpoints that deny object-scope access must return a stable error payload. Web templates may render this payload into messages; mobile apps must use `error_code`, not parse localized `message`.

```json
{
  "success": false,
  "error_code": "ERR_SCOPE_STAFF_OUT_OF_SCOPE",
  "message": "Nhân viên Nguyễn Văn A hiện không thuộc phạm vi quản lý của bạn cho ngày 2026-06-10.",
  "details": {
    "target_staff": "Nguyễn Văn A",
    "target_site": "Mục tiêu B",
    "required_scope": "SITE:Mục tiêu B",
    "current_scope": "SITE:Mục tiêu A",
    "escalation_path": "Liên hệ Quản lý vùng hoặc Phòng nghiệp vụ"
  },
  "request_id": "..."
}
```

Privacy rules:

- For low-privilege users, return `ERR_OBJECT_NOT_FOUND_OR_NOT_VISIBLE` when revealing object existence would leak staff, payroll, GPS, photo, incident or site data.
- `details` must be masked by role. Do not include CCCD, bank account, exact GPS coordinates, private phone/address, salary amount or photo URLs unless the user has explicit permission.
- Mobile apps must branch on `error_code`; `message` is user-facing text and may be localized.
- Web UI must show a next step: request delegation, contact Area Manager, create change request, or open adjustment workflow.

Denied examples:

```text
ERR_SCOPE_STAFF_OUT_OF_SCOPE:
Nhân viên Nguyễn Văn A hiện thuộc Mục tiêu B. Bạn là Chỉ huy Mục tiêu A nên không thể thay đổi ca trực này. Vui lòng liên hệ Quản lý vùng hoặc Phòng nghiệp vụ.
```

```text
ERR_SCOPE_DELEGATION_OUT_OF_SCOPE:
Bạn đang được ủy quyền quản lý Mục tiêu A đến 13/06/2026. Thao tác này thuộc Mục tiêu B nên không được phép.
```

---

## 4. Scope sources

A user's effective scope may come from multiple sources.

| Source | Meaning | Audit requirement |
|---|---|---|
| Direct role scope | user directly manages site/region/department | standard audit |
| Temporary delegation | user acts on behalf of another user for limited time | audit includes delegator and delegation id |
| Historical assignment | user had valid scope when data was generated | view reason includes event date |
| Executive/global scope | approved global operational visibility | export/audit required for sensitive data |

Effective scope must be resolved centrally, not by ad hoc view queries.


---

## 4A. Admin Authorization Contract

Django Admin/Jazzmin is a technical console, not a bypass around business authorization. Admin views that expose staff, site, shift, attendance, GPS/photo evidence, incident, payroll, inventory, export or company data must enforce object-scope policies.

Required ModelAdmin patterns:

```python
def get_queryset(self, request):
    qs = super().get_queryset(request)
    return Policy.visible_queryset(request.user, qs)

def has_view_permission(self, request, obj=None):
    return Policy.can_view(request.user, obj).allowed if obj else Policy.can_view_module(request.user).allowed

def has_change_permission(self, request, obj=None):
    return Policy.can_change(request.user, obj).allowed if obj else Policy.can_change_module(request.user).allowed

def has_delete_permission(self, request, obj=None):
    return Policy.can_delete(request.user, obj).allowed if obj else False
```

Mandatory rules:

- `ModelAdmin.get_queryset()` must scope by user for user-facing business data.
- `has_view_permission`, `has_change_permission`, and `has_delete_permission` must check object scope when `obj` is provided.
- Admin actions must validate every selected object. Do not assume queryset filtering is enough.
- Inline admins must not show children outside the parent object's scope.
- ForeignKey widgets, autocomplete fields, raw ID fields, and search endpoints must use scoped querysets.
- Sensitive admin exports require explicit permission, reason, audit log, filters, row count and request metadata.
- Superuser/technical admin may access the console, but business-sensitive changes still require audit and must be traceable.
- Bulk post/void/lock/unlock/delete actions must be delegated to application use cases with transaction and audit.

Admin denial must use `PolicyResult` where possible and show a business message, not a generic 403.

---

## 5. Temporary Scope Delegation

### 5.1 Why not temporary role only

Temporary role assignment loses critical audit context:

```text
Who delegated?
Who received delegation?
Which scope was delegated?
Which permissions were delegated?
When does it start/end?
Who approved it?
Why was it created?
Was it revoked?
```

### 5.2 Required model

Target model location when implemented: `delegation/models.py::AccessDelegation`.

Required model:

```text
AccessDelegation
- delegator_user
- delegatee_user
- scope_type: SITE / REGION / DEPARTMENT / OPERATIONS
- scope_object_id
- permissions
- starts_at
- ends_at
- reason
- status: DRAFT / PENDING_APPROVAL / ACTIVE / EXPIRED / REVOKED / REJECTED
- approved_by
- approved_at
- revoked_by
- revoked_at
- revoke_reason
- tenant_id
- created_at
- updated_at
```

### 5.3 Database constraints and indexes

`AccessDelegation` must include DB-level constraints and indexes.

Required indexes:

```text
(delegatee_user, status, starts_at, ends_at)
(delegator_user, status, starts_at, ends_at)
(scope_type, scope_object_id, status)
(tenant_id, delegatee_user, status)
```

Required constraints:

```text
starts_at < ends_at
status in DRAFT/PENDING_APPROVAL/ACTIVE/EXPIRED/REVOKED/REJECTED
```

Overlap rule:

- Multiple delegations may overlap only when they delegate different scope objects or different permission sets.
- If two active delegations cover the same `delegatee_user`, `scope_type`, `scope_object_id`, and permission, the policy must use the narrower time window and highest explicit approval record.
- Runtime policy must reject expired delegations even if a scheduled cleanup task has not yet marked them `EXPIRED`.

Revocation/expiration:

- `REVOKED` delegations must stop immediately.
- `ends_at < now()` must behave as expired even if `status = ACTIVE`.
- Cleanup tasks may update status to `EXPIRED`, but access policy must not depend on cleanup timing.

### 5.4 Approval rule

Required first implementation:

```text
Site Commander may request delegation.
Area Manager or Operations Department approves.
Area Manager / Operations Department may create emergency delegation directly.
```

### 5.5 Audit rule

Every action performed through delegation must record:

```text
actor_user = delegatee
scope_source = DELEGATION
delegator_user = delegator
delegation_id = AccessDelegation.id
action
object_type
object_id
timestamp
reason/context
```

### 5.5 Expiry rule

Authorization must ignore expired delegations even if a cleanup task has not yet marked them `EXPIRED`.

### 5.6 Override level inherited from delegator

For override policy, a delegatee acts with the **effective scope level of the delegator**, but only inside the delegated scope, delegated permission set, and valid time window.

Example:

```text
Area Manager delegates Site A scheduling to Deputy B.
Deputy B may schedule at Site A with AREA override level for the delegated action.
Deputy B does not become Area Manager globally.
Audit must record actor=B, delegator=Area Manager, effective_scope_level=AREA, delegation_id=... .
```

If the delegated action exceeds delegated scope or permission, deny with `ERR_SCOPE_DELEGATION_OUT_OF_SCOPE`.

---

## 6. Historical Data Scope

SCMD Pro must distinguish current scope from event-time scope.

Example:

```text
Guard X worked at Site A from 2026-06-01 to 2026-06-27.
Guard X moved to Site B on 2026-06-28.
```

Site A commander can still reconcile Site A records from 2026-06-01 to 2026-06-27, but cannot view Site B records after 2026-06-28.

Required model:

```text
NhanVienRegionAssignment
Authoritative model location: `users/models_assignment.py::NhanVienRegionAssignment`.

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

Historical checks must use event date/time:

```python
can_view_attendance(user, attendance):
    site = attendance.shift.site
    event_time = attendance.shift.start_at
    return user_had_scope_on_site(user, site, at_time=event_time)
```

### 6.1 Night-shift event-time rule

Security operations frequently use overnight shifts, for example 18:00 to 06:00. For access-scope and reconciliation purposes, SCMD Pro must define a canonical business date.

Contract:

```text
The canonical `work_date` of a shift is the local date of `shift.start_at`, not `shift.end_at`.
```

Implications:

```text
A shift from 2026-06-27 18:00 to 2026-06-28 06:00 belongs to work_date 2026-06-27.
Historical scope checks for shift scheduling, attendance reconciliation, incident linkage, and payroll snapshot use shift.start_at/work_date.
```

Example:

```text
Guard X transfers from Site A to Site B at 2026-06-28 00:00.
A shift that started at Site A at 2026-06-27 18:00 remains Site A work_date 2026-06-27.
Site A commander may view/reconcile that shift and its attendance even though checkout occurred on 2026-06-28.
```

Exception rule:

```text
If a business explicitly splits overnight shifts into two payroll/work segments, the split must create two explicit shift/attendance segments. Do not infer split scope silently from clock midnight.
```

---

## 7. Multi-site Assignment

A guard may be assigned to more than one site.

Do not use a single `current_region` as the only source of truth.

Correct separation:

```text
NhanVienRegionAssignment = long-running operational assignment / regional staffing pool
PhanCongCaTruc = actual shift on a specific date/site/post
```

A guard may have active assignment rows for Site A and Site B. Actual check-in/check-out must still validate against `PhanCongCaTruc`.

---

## 8. Override Policy

Scope hierarchy:

```text
EXECUTIVE / GLOBAL_OPERATION > OPERATIONS > REGION > SITE > SELF
```

Rule:

```text
Lower scope must not silently overwrite higher-scope decisions.
```

Examples:

| Existing action | Later actor | Rule |
|---|---|---|
| Site Commander creates shift | Area Manager edits shift | allowed if within region |
| Area Manager creates shift | Site Commander edits shift | deny or require change request |
| Operations locks schedule | Area/Site edits schedule | deny unless override permission |
| Payroll locks period | Operations edits attendance | deny; use adjustment/reopen workflow |
| Delegatee acts within active delegation | Any later actor | compare against delegator's effective scope level |

Override decision metadata should include:

```text
actor_user
effective_scope_level
scope_source: DIRECT / DELEGATION / SYSTEM / EMERGENCY
scope_source_id: delegation_id or approval id if applicable
```

---

## 9. Payroll reconciliation adjustment

Locked or paid payroll periods must not be modified directly. Retroactive corrections after lock/paid must create adjustment records.

Required SSOT model:

```text
PayrollAdjustment
- payroll_period
- nhan_vien
- source_object_type: ATTENDANCE / INCIDENT / INVENTORY / MANUAL / SYSTEM
- source_object_id
- adjustment_type: ADDITION / DEDUCTION / REVERSAL / CORRECTION
- amount
- reason
- calculation_snapshot
- status: DRAFT / REVIEWED / APPROVED / POSTED / VOIDED
- applies_to_period
- created_by
- approved_by
- posted_at
- tenant_id
```

Rules:

```text
LOCKED/PAID ChiTietLuong is immutable.
Adjustment must reference the original source and explain before/after impact.
Adjustment must be included in next payroll run or controlled reversal workflow.
Every adjustment requires audit.
```

---

## 10. Required policy modules

Required layout:

```text
core/policy_result.py
core/access_scope.py
users/access_policies.py
clients/access_policies.py
operations/access_policies.py
inspection/access_policies.py
inventory/access_policies.py
workflow/access_policies.py
```

Required policy functions:

```text
SiteVisibilityPolicy.visible_sites(user, at_time=None)
StaffVisibilityPolicy.visible_staff(user, at_time=None)
StaffVisibilityPolicy.visible_staff_for_scheduling(user, site, at_date=None)
ShiftAssignmentPolicy.can_assign_shift(user, staff, site, shift_date)
DispatchPolicy.can_transfer_staff(user, staff, from_site, to_site, effective_date)
TaskAssignmentPolicy.can_assign_task(user, assignee, site=None)
IncidentVisibilityPolicy.visible_incidents(user)
InventoryAccessPolicy.can_issue_equipment(user, staff, site=None)
PayrollAccessPolicy.visible_payroll_records(user)
```

---

## 11. Enforcement points

Every sensitive workflow must enforce policy at three layers:

```text
UI visibility
Queryset scope
Action policy
```

UI hiding is never a security boundary. Permission decorators are not enough. Object-level policy is mandatory.

---

## 12. Workflow-specific contracts

### 12.1 Shift scheduling

Must validate:

```text
user has `giao_ca_truc`
user has scope on target site/post
staff is visible/assignable to user at shift work_date
night shifts use shift.start_at local date as work_date
shift period is not payroll locked
site/post belongs to user scope
higher-scope locks/overrides are respected
```

### 12.2 Dispatch / transfer

Must validate:

```text
user has dispatch permission
user has scope on source site
user has scope on destination site
staff is transferable at effective date
uniform/equipment obligations are handled
audit records source, destination, actor, reason
```

### 12.3 Task assignment

Must validate:

```text
user can assign work
assignee is in user scope
site/post/shift attached to task is in user scope
delegation is recorded if applicable
```

### 12.4 Incident handling

Must validate:

```text
user can see incident site
user can transition incident state
closed incident cannot be edited without reopen/audit
financial impact requires payroll/accounting permission
```

### 12.5 Inventory/equipment

Must validate:

```text
warehouse scope
site/staff relationship
issue/return approval
payroll deduction trace if lost/damaged
audit for stock-affecting actions
```

### 12.6 Payroll

Must validate:

```text
payroll visibility scope
lock/unlock permission
export permission and audit
attendance adjustment policy
historical site scope for reconciliation views
retroactive corrections create PayrollAdjustment, not direct locked-row edits
```

---

## 13. Required tests

Minimum regression matrix:

```text
Site Commander A cannot see Site B staff.
Site Commander A cannot assign Site B staff.
Area Manager can see Site A and B inside area, not Site C outside area.
Operations Department can dispatch across allowed sites.
Guard sees only own shifts/patrol/tasks.
Payroll user cannot dispatch staff.
Inventory user cannot view payroll.
Temporary delegate can act only within delegation window and scope.
Expired delegation no longer grants access.
Audit records delegator/delegatee when action uses delegation.
Historical Site A commander can view records from the period staff belonged to Site A.
Historical Site A commander can view overnight shift that started while staff belonged to Site A.
Historical Site A commander cannot view later Site B records.
Lower scope cannot overwrite higher-scope locked decisions.
Delegatee override level follows delegator within delegated scope only.
Access denied message contains business reason and stable error code.
```

---

## 14. Data retention and archive contract

Operational authorization generates high-volume records: audit logs, GPS/photo evidence, patrol scans, staff assignment history, task events, and dashboard aggregates. These records must be retained according to business value and legal/accounting needs.

Minimum retention policy:

| Data class | Hot retention | Archive / cold storage | Notes |
|---|---:|---:|---|
| Payroll, salary details, payroll adjustments | 60 months | retain permanently unless legal policy says otherwise | high dispute/legal value |
| Contracts, sites, pricing history | active + 60 months | retain permanently or legal archive | needed for reconciliation |
| Attendance and shift assignments | 24 months | archive after 24 months | keep indexed by employee/site/date |
| GPS/photo attendance evidence | 12 months | cold storage after 12 months | preserve references in DB |
| Incident records | 36 months | archive after 36 months | serious incidents may retain longer |
| Patrol checkpoint evidence | 12 months | cold storage after 12 months | keep summary metadata hot |
| AuditLog | 24 months hot | archive after 24 months | never silently delete sensitive audit |
| NhanVienRegionAssignment | active + 60 months | archive after 60 months | needed for historical scope |
| Notification/task event logs | 6-12 months | prune/archive by severity | operational noise |

Rules:

```text
Archive must preserve referential traceability for payroll, incident, inventory, and attendance disputes.
Do not hard-delete audit records for sensitive actions without approved retention policy.
Archived data must remain queryable by authorized users for investigation/export workflows.
Performance optimization must not break historical-scope checks.
```

---

## 15. Definition of Done

A workflow is Access-Scope compliant only when:

```text
Querysets are scoped by policy.
Actions are checked by object-level policy.
Deny messages are contextual and use registered error codes.
Audit logs include scope source and delegation where applicable.
Historical records use event-time scope, including overnight shift work_date rules.
Tests cover allowed and denied cases.
No workflow relies only on frontend hiding or generic RBAC.
```
### 6.4 Database constraints and indexes for `NhanVienRegionAssignment`

Required indexes:

```text
(nhan_vien, starts_at, ends_at)
(muc_tieu, starts_at, ends_at)
(tenant_id, nhan_vien, muc_tieu)
(status, starts_at, ends_at)
```

Required rules:

- Assignment active/current must be derived from assignment history, not a single `current_region` field.
- Multi-region assignment is allowed when business rules permit it. Do not add a global uniqueness constraint that prevents a guard from working at Site A and Site B in the same period.
- Overlap is valid only when shift windows do not conflict or when assignment type is `FLOATING`/`RELIEF`.
- Conflict detection must happen in scheduling/dispatch policies.
- Backfill from legacy data must be documented in `ACCESS_SCOPE_MIGRATION_BACKFILL_PLAN.md`.



---

## 18. Related authoritative contracts

- Admin authorization: `docs/access_scope/ADMIN_AUTHORIZATION_CONTRACT.md`
- Migration/backfill: `docs/access_scope/ACCESS_SCOPE_MIGRATION_BACKFILL_PLAN.md`
- Sensitive export/media privacy: `docs/access_scope/SENSITIVE_DATA_EXPORT_CONTRACT.md`
- Architecture decision record: `docs/access_scope/ACCESS_SCOPE_DECISION_RECORD.md`
- Release checklist: `RELEASE_CHECKLIST.md`
