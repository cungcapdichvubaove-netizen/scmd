# ADMIN_AUTHORIZATION_CONTRACT.md — SCMD Pro Django Admin Authorization Contract

Version: 1.0.0  
Status: Authoritative implementation contract  
Updated: 2026-06-08  
Scope: Django Admin/Jazzmin object-scope authorization

---

## 1. Purpose

SCMD Pro uses Django Admin/Jazzmin as a technical console. Admin must not bypass RBAC, object scope, audit governance, or sensitive export policy.

This contract applies to ModelAdmin classes, admin actions, inline admins, autocomplete fields, import/export actions, and emergency correction workflows.

---

## 2. Required ModelAdmin pattern

Every ModelAdmin for sensitive business data must enforce scope in `get_queryset()` and object-level permission methods.

Sensitive business data includes:

```text
NhanVien, MucTieu, ViTriChot, PhanCongCaTruc, ChamCong, BaoCaoSuCo,
KiemTraQuanSo, patrol/inspection models, inventory documents/ledger,
payroll records, export records, CompanyInfo, audit records.
```

Required pattern:

```python
def get_queryset(self, request):
    qs = super().get_queryset(request)
    return AccessPolicy.visible_queryset(request.user, qs)

def has_view_permission(self, request, obj=None):
    if obj is None:
        return AccessPolicy.can_view_module(request.user).allowed
    return AccessPolicy.can_view(request.user, obj).allowed

def has_change_permission(self, request, obj=None):
    if obj is None:
        return AccessPolicy.can_change_module(request.user).allowed
    return AccessPolicy.can_change(request.user, obj).allowed

def has_delete_permission(self, request, obj=None):
    if obj is None:
        return False
    return AccessPolicy.can_delete(request.user, obj).allowed
```

---

## 3. Admin actions

Admin actions must validate every selected object before execution.

Forbidden:

```python
for obj in queryset:
    obj.delete()
```

Required:

```python
for obj in queryset:
    result = AccessPolicy.can_perform_action(request.user, obj, action="void")
    if not result.allowed:
        raise PermissionDenied(result.message)
    UseCase.execute(actor=request.user, obj=obj, reason=reason)
```

Bulk actions that post/void/delete/lock/unlock/export sensitive data must:

- require explicit permission;
- require a reason when action changes data state;
- run in a transaction where appropriate;
- call application use cases, not inline model mutation;
- write audit logs with row count and selected object IDs where safe.

---

## 4. Inline admins

Inline admins must not leak child objects outside scope.

Rules:

- Inline queryset is scoped through the parent object's policy.
- If the parent is outside scope, the parent page must not be visible.
- Inline create/change/delete must check action policy.
- Inline ForeignKey dropdowns must be scoped.

---

## 5. ForeignKey, autocomplete and search fields

Admin widgets must not expose staff/site/object choices outside scope.

Required:

```python
def formfield_for_foreignkey(self, db_field, request, **kwargs):
    if db_field.name == "nhan_vien":
        kwargs["queryset"] = StaffVisibilityPolicy.visible_staff(request.user)
    return super().formfield_for_foreignkey(db_field, request, **kwargs)
```

Autocomplete endpoints must use scoped querysets. Raw ID fields must enforce object permission after submission.

---

## 6. Sensitive admin export

Sensitive export from admin requires:

```text
permission
reason
filters
row_count
actor_user
timestamp
IP/user agent/request_id where available
export file id/path
```

Sensitive export includes payroll, attendance, GPS, photo evidence, employee profile, CCCD, bank account, incident evidence and inventory deduction data.

Exports must follow `docs/access_scope/SENSITIVE_DATA_EXPORT_CONTRACT.md`.

---

## 7. Superuser policy

Superuser is not a business-process role.

Rules:

- Superuser may access technical console.
- Sensitive business changes still require audit.
- Routine operational work must use business roles and scopes.
- Production superuser correction requires reason/ticket reference.

---

## 8. Required tests

Minimum tests:

| ID | Scenario | Expected |
|---|---|---|
| ADMIN-SCOPE-001 | Site Commander A opens admin list | Only Site A data visible |
| ADMIN-SCOPE-002 | Site Commander A opens Site B object change URL | 403 or not found |
| ADMIN-SCOPE-003 | Admin bulk action includes object outside scope | Outside object rejected; no partial unauthorized mutation |
| ADMIN-SCOPE-004 | FK dropdown staff field | Only visible staff listed |
| ADMIN-SCOPE-005 | Autocomplete staff search | No out-of-scope staff returned |
| ADMIN-EXPORT-001 | Sensitive export by authorized user | Audit contains filters, reason, row count |
| ADMIN-SUPER-001 | Superuser payroll export | Audit still created |
