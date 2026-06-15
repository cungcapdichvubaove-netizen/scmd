# Business Workflow Phase F — Asset Recovery & Offboarding Inventory

## Decision

SCMD Pro now treats employee asset return/offboarding inventory as its own source-record lifecycle:

`PhieuXuat/ChiTietPhieuXuat` → `PhieuThuHoi/ChiTietPhieuThuHoi` → `InventoryLedgerEntry` and optional `BienBanMatHongVatTu` → `KhoanKhauTruNhanVien`.

`OffboardingChecklist` boolean fields remain for backward compatibility, but they are not the SSOT for asset recovery. Asset completion is validated from posted recovery documents and resolved damage/loss reports.

## Scope boundaries

Phase F intentionally does **not** implement serialized asset tracking across the whole system, does **not** change the payroll engine, and does **not** write directly to `ChiTietLuong`.

Damage/loss money becomes a source deduction record in `accounting.KhoanKhauTruNhanVien` with status `PENDING_APPROVAL`. Payroll application remains in the payroll workflow.

## Ledger rules

- Good returned items create `InventoryLedgerEntry` with document type `RECOVERY`, direction `IN`.
- Voiding a posted recovery creates reversal ledger entries with direction `OUT`.
- Lost/damaged/missing items do not increase stock; they create `BienBanMatHongVatTu`.
- `PhieuThuHoi` cannot be hard-deleted after `POSTED` or `VOIDED`.

## Phase G/H follow-up

- Serialized asset lifecycle and per-item custody.
- Formal reversal/correction documents for damage reports.
- Deeper dashboard UI for warehouse/offboarding queues.


## Release checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test inventory.tests_phase_f_asset_recovery
python manage.py test users accounting inventory
python manage.py test operations accounting users clients inventory
```

## Known boundaries after Phase F

- No serialized asset tracking across every individual uniform/tool item yet.
- No formal `PhieuThuHoiReversal` or `BienBanMatHongVatTuCorrection` model yet.
- Damage/loss approval creates `KhoanKhauTruNhanVien PENDING_APPROVAL`; payroll application remains the payroll workflow responsibility.
- Offboarding checklist compatibility booleans remain but must not be treated as the source of truth for asset recovery.

## Phase F v2 void hardening

Phase F v2 intentionally chooses the conservative rule for posted recovery voids:

- A posted `PhieuThuHoi` cannot be voided while any related `BienBanMatHongVatTu` is still active (`DRAFT`, `PENDING_APPROVAL`, `APPROVED`, or `APPLIED`). Operators must cancel/resolve the damage report first.
- If a related damage report has already created `KhoanKhauTruNhanVien`, void is blocked unless every related deduction is in a terminal cancellation state (`CANCELLED` or `REJECTED`). If a deployment does not support cancellation/rejection on the deduction model, any linked deduction blocks void.
- Void guards run before any inventory reversal ledger is written; a blocked void must not mutate stock.
- Successful void audit logs must explicitly state that there are no active damage/loss reports or effective payroll-deduction records tied to the recovery document.

No payroll engine changes, serialized asset tracking, or offboarding boolean removal are included in Phase F v2.
