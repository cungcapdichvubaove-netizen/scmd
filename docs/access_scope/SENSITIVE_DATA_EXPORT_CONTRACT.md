# SENSITIVE_DATA_EXPORT_CONTRACT.md — SCMD Pro Sensitive Data Export & Private Media Contract

Version: 1.0.0  
Status: Authoritative implementation contract  
Updated: 2026-06-08  
Scope: payroll, GPS, photo evidence, personnel data, incident evidence, sensitive exports

---

## 1. Sensitive data classes

| Class | Examples |
|---|---|
| Personnel PII | CCCD, address, phone, bank account, profile photo |
| Payroll | salary, allowance, deduction, bank transfer, payroll export |
| GPS | check-in/out coordinates, patrol coordinates, geofence evidence |
| Photo evidence | attendance photo, patrol photo, incident photo |
| Incident evidence | damage, responsibility, compensation, security event details |
| Inventory deduction | uniform/equipment loss, employee deduction trace |

---

## 2. Media storage and access

Rules:

- Sensitive photos/evidence must not be served as public static files.
- Do not place uploaded evidence in `static/` or committed source ZIP.
- Prefer private media storage or protected media views.
- If using cloud storage, use signed URLs with expiry.
- If local storage is used, route downloads through permission-checked Django views.
- Export files must not be saved under public static paths.

---

## 3. Export permission and reason

Sensitive export requires:

```text
explicit permission
object scope check
reason / purpose
filters used
row count
actor user
request id
IP/user agent if available
created timestamp
expiry or storage policy
```

Examples of sensitive exports:

```text
Payroll Excel/PDF
Attendance GPS/photo report
Employee profile PDF/bulk export
Incident PDF with evidence
Inventory deduction report
Patrol evidence export
```

---

## 4. Standard export audit record

Minimum audit payload:

```json
{
  "actor_user_id": 123,
  "action": "EXPORT_PAYROLL",
  "object_type": "BangLuongThang",
  "object_id": 456,
  "filters": {"month": "2026-06", "site": "A"},
  "row_count": 150,
  "reason": "Monthly payroll reconciliation",
  "file_reference": "private://exports/...",
  "request_id": "...",
  "ip": "...",
  "user_agent": "..."
}
```

Do not log raw CCCD, bank account, exact GPS coordinates or photo URLs in audit payload. Use masked or internal references.

---

## 5. Masking rules

Default masking:

| Field | Default display |
|---|---|
| CCCD | `********1234` |
| Bank account | `******7890` |
| Phone | `******123` unless HR/operations permission permits full |
| Address | province/district only unless HR permission permits full |
| GPS | approximate or hidden unless operations/evidence permission permits exact |
| Salary | hidden unless payroll permission permits full |

---

## 6. File lifecycle

Sensitive export file lifecycle:

```text
CREATED -> AVAILABLE -> EXPIRED -> DELETED/ARCHIVED
```

Rules:

- Default export link expiry: 24 hours unless a stricter environment policy is configured.
- Download of existing export must re-check permission.
- Re-download must be audited.
- Revocation must immediately block access.
- Expired export files should be deleted or moved to private archive according to retention policy.

---

## 7. Watermark and metadata

High-risk PDF/Excel reports should include:

```text
SCMD Pro report name
company info
exported_by
exported_at
filter summary
confidential label
page number / document id
```

For payroll and GPS/photo evidence, include watermark or footer metadata where practical.

---

## 8. Required tests

| ID | Scenario | Expected |
|---|---|---|
| EXPORT-SEC-001 | User without export permission requests payroll export | Denied with `ERR_EXPORT_PERMISSION_REQUIRED` |
| EXPORT-SEC-002 | Authorized export without reason | Denied |
| EXPORT-SEC-003 | Authorized export with reason | File created in private storage and audit written |
| EXPORT-SEC-004 | Re-download after permission revoked | Denied |
| EXPORT-SEC-005 | Low-privilege report payload | PII masked |
| EXPORT-SEC-006 | Source ZIP package | No uploaded media/export files included |
