# VIBE_CODING_ACCESS_SCOPE_PLAYBOOK.md — AI/Coder Guide for Access Scope Work

Version: 1.1.0  
Status: Mandatory guide for AI-assisted implementation  
Updated: 2026-06-08

---

## 1. Product context

SCMD Pro is a professional security-service operations platform. It is not a cyber dashboard, not a war-room UI, not a microservices rewrite, and not a true multi-tenant SaaS.

Target architecture:

```text
single-organization hardened layered monolith
```

`tenant_id` is legacy naming for the configured organization scope. Do not implement dynamic SaaS tenant behavior.

---

## 2. Before coding, answer these questions

```text
Who is the user?
What business role do they have?
Which site/staff/shift/object are they allowed to see?
Which action are they allowed to perform?
At what time is the scope evaluated?
Is access direct, delegated, or historical?
For overnight shifts, what is the canonical work_date?
Does an override hierarchy apply?
What audit record is required?
What stable error code and user-facing denial message should be shown?
```

---

## 3. Forbidden patterns

Do not use global querysets in user-facing workflows:

```python
NhanVien.objects.all()
MucTieu.objects.all()
PhanCongCaTruc.objects.filter(...)
BaoCaoSuCo.objects.filter(...)
```

Do not rely only on:

```text
frontend hiding
role name
is_superuser
permission decorator without object-level check
current_region only
shared passwords
temporary superuser role
unchecked temporary role escalation
```

Do not edit LOCKED/PAID payroll records directly. Use adjustment/reversal workflow.

---

## 4. Required implementation pattern

Use this shape:

```python
sites = SiteVisibilityPolicy.visible_sites(request.user)
staff = StaffVisibilityPolicy.visible_staff_for_scheduling(request.user, site, shift_date)
result = ShiftAssignmentPolicy.can_assign_shift(request.user, staff_member, site, shift_date)
if not result.allowed:
    messages.error(request, result.message)
    return redirect(...)
```

For APIs:

```python
if not result.allowed:
    return Response(
        {
            "success": False,
            "error_code": result.code,
            "message": result.message,
            "details": result.details or {},
        },
        status=403,
    )
```

Use error codes from `ACCESS_SCOPE_AUTHORIZATION_CONTRACT.md`, for example `ERR_SCOPE_STAFF_OUT_OF_SCOPE`, `ERR_SCOPE_DELEGATION_EXPIRED`, `ERR_OVERRIDE_HIGHER_SCOPE_LOCK`, `ERR_PAYROLL_LOCKED`.

---

## 5. Temporary delegation rules

Never solve temporary replacement by sharing passwords or permanent role escalation.

Correct solution:

```text
AccessDelegation with limited scope, limited permissions, start/end time, reason, approval, audit.
```

When an action uses delegation, audit must include:

```text
actor_user
delegator_user
delegation_id
scope_type
scope_object_id
permission_used
effective_scope_level inherited from delegator
```

Delegatee inherits the delegator's override level only inside delegated scope/permission/time window.

---

## 6. Historical scope and night-shift rules

For attendance, payroll, incidents, patrol, and inventory history, evaluate access by the event/work date.

Never use only the employee's current site for historical records.

Night shifts:

```text
Canonical work_date = local date of shift.start_at.
Do not switch scope at midnight unless the business explicitly splits the shift into two records.
```

---

## 7. Multi-region assignment rules

Do not assume one employee has exactly one active site.

Use:

```text
NhanVienRegionAssignment for regional staffing pool / operational affiliation
PhanCongCaTruc for actual shift/date/post
```

---

## 8. Override rules

Scope hierarchy:

```text
EXECUTIVE / GLOBAL_OPERATION > OPERATIONS > REGION > SITE > SELF
```

Lower scope cannot silently overwrite higher-scope decisions. Use change request or explicit override permission.

Delegated actions compare against the delegator's effective scope level within delegation boundary.

---

## 9. Payroll adjustment rule

If payroll is `LOCKED` or `PAID`, do not directly edit `ChiTietLuong`.

Use or introduce:

```text
PayrollAdjustment
```

The adjustment must record source object, reason, before/after calculation snapshot, approver and audit trail.

---

## 10. Data retention rule

Do not add pruning/delete logic for audit, GPS/photo, attendance, payroll, patrol, incident, or assignment history without checking the retention table in `ACCESS_SCOPE_AUTHORIZATION_CONTRACT.md` and `WHITEPAPER.md`.

Archive must preserve traceability for disputes and historical scope checks.

---

## 11. Testing requirements for every PR

For any workflow touched by access scope, include:

```text
allow test
deny test
out-of-scope object test
delegation test if delegation applies
historical scope test if dates matter
night-shift test if shift crosses midnight
audit assertion if data changes
error code + message assertion for access denied UX
```

---

## 12. Review checklist

A change is not acceptable if:

```text
It adds an unscoped queryset.
It checks only role/permission but not target object.
It hides UI but leaves backend open.
It changes attendance/payroll/incident/inventory without audit.
It creates temporary access without expiry.
It returns generic 403 where business explanation is needed.
It ignores overnight-shift work_date.
It lets lower scope overwrite higher-scope decision silently.
```
