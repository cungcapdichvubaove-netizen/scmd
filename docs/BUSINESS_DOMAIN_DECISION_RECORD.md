# Business Domain Decision Record — Phase A+B

## Status

Accepted for Phase A+B patch.

## Context

SCMD Pro now models several business records that have their own lifecycle, source document, status, dates, approver, evidence file, audit log, and dashboard warning. The goal is to avoid overloading primary records such as `NhanVien`, `HopDong`, `PhanCongCaTruc`, or payroll lines with lifecycle fields that belong to separate legal or operational records.

## Decision 1 — Contract receivables ownership

For Phase A+B, contract-finance records are intentionally owned by the `clients` app:

- `clients.PhuLucHopDongDichVu`
- `clients.BienBanNghiemThu`
- `clients.HoaDon`
- `clients.CongNo`

Rationale:

- The source lifecycle starts from customer contract delivery, acceptance, invoicing, and receivable follow-up.
- `clients` already owns customer contracts and service-acceptance context.
- Moving these records into `accounting` now would require wider reporting and migration decisions that are out of Phase A+B scope.

Boundary:

- `clients.HoaDon` and `clients.CongNo` are the Phase A+B source records for customer receivables.
- `accounting will consume reconciled receivable data` from these records in a later reporting/export phase.
- Until that integration phase is designed, do not introduce duplicate accounting.HoaDon or accounting.CongNo models.

## Decision 2 — Legacy fields are not SSOT for business records

Legacy compatibility fields remain readable, but they are not the source of truth for records with independent lifecycle:

- `NhanVien.loai_hop_dong` is not SSOT for active labor contracts; use `HopDongLaoDong`.
- Insurance status must come from `HoSoBaoHiem`, not a loose employee field.
- Leave, offboarding, payroll advance/deduction, shift-change, acceptance, invoice, and receivable workflows must use their dedicated records, not generic proposal/report records.

## Decision 3 — Mandatory insurance dashboard rule

The HR dashboard mandatory-insurance warning is explicitly scoped to active BHXH:

- `HoSoBaoHiem.loai_bao_hiem = BHXH`
- `HoSoBaoHiem.trang_thai = ACTIVE`
- effective date is active on the dashboard date

An active `BAO_HIEM_KHAC`, `BHYT`, or `BHTN` record alone must not satisfy the mandatory BHXH warning for official staff.

## Decision 4 — Phase E customer payment and receivable settlement

Phase E keeps the customer payment, invoice allocation, and receivable settlement source records in the `clients` app:

- `clients.ThanhToanKhachHang`
- `clients.PhanBoThanhToanHoaDon`
- `clients.HoaDon`
- `clients.CongNo`

Rationale:

- Customer receivable collection starts from the contract/customer lifecycle already owned by `clients`.
- `CongNo.so_tien_da_thu` is no longer a manually edited source field. It is a derived/synchronized value from `PhanBoThanhToanHoaDon` through Phase E use cases.
- `accounting` will consume receivable reports/exports in a later phase, but must not introduce duplicate `accounting.HoaDon`, `accounting.CongNo`, or `accounting.ThanhToanKhachHang` without a migration/facade decision.

Boundary:

- `ThanhToanKhachHang` is the source record for money received from customers.
- `PhanBoThanhToanHoaDon` is the source record for allocating that money to invoices/receivables.
- `RecalculateReceivableStatusUseCase` is responsible for synchronizing invoice/receivable statuses from allocations.
- Canceling an already allocated payment is blocked in Phase E. A later recovery path must use explicit reversal/adjustment records, not silent deletion.

## Phase E v2 — Customer payment authorization and reversal boundary

`clients` continues to own the contract receivable lifecycle in Phase E v2.
However, payment mutation is now explicitly a finance-controlled workflow:
`CustomerPaymentPermissionPolicy` allows only superusers, `ban_giam_doc`, and
`ke_toan` to receive, allocate, cancel, or recalculate customer payments.

`PhanBoThanhToanHoaDon` records are append-only in admin for Phase E v2. Direct
admin delete is disabled. If a settlement needs correction, a future recovery
phase must introduce an explicit reversal/adjustment record instead of deleting
source allocations.

## Phase E v3 — Append-only customer payment evidence and debt-first allocation

Financial settlement records are treated as source evidence once they affect a
receivable. Phase E v3 therefore makes allocated `ThanhToanKhachHang` records and
created `PhanBoThanhToanHoaDon` records append-only for source fields. If an
operator made a mistake, the correct path is a future reversal/adjustment record,
not silent edit/delete of the original financial record.

Phase E v3 also rejects invoice-only allocation. Every allocation must target a
specific `CongNo`; the linked `HoaDon` is derived/validated from that debt. This
prevents a split-brain state where an invoice appears paid but the receivable
record remains open.

Report semantics are clarified but compatibility aliases remain. New report keys
are `total_open_receivable`, `total_collected_allocation`, and
`total_remaining_open_receivable`; legacy aliases are retained for current
widgets/templates.

Phase E4/E5 may add `PARTIALLY_ALLOCATED`/`FULLY_ALLOCATED` statuses and explicit
payment/allocation reversal records.


## Decision 5 — Phase F asset recovery and offboarding inventory ownership

Phase F keeps employee asset recovery in the `inventory` app:

- `inventory.PhieuThuHoi`
- `inventory.ChiTietPhieuThuHoi`
- `inventory.BienBanMatHongVatTu`
- `inventory.InventoryLedgerEntry` recovery references

Rationale:

- The source lifecycle starts from stock issue/return and warehouse accountability.
- Offboarding needs the result of inventory recovery, but `OffboardingChecklist` booleans are not the asset-recovery SSOT.
- Payroll may consume damage/loss deductions through `accounting.KhoanKhauTruNhanVien`, but Phase F must not write directly to `ChiTietLuong`.

Boundary:

- Do not model returned assets through fake `PhieuNhap` records.
- Do not hard-delete `PhieuThuHoi` once posted/voided.
- Good returns affect stock through ledger `IN`; void creates reversal ledger `OUT`.
- Lost/damaged/missing items create `BienBanMatHongVatTu` and, after approval, a payroll deduction source record.
- Serialized asset custody and formal reversal/correction records remain later phases.
