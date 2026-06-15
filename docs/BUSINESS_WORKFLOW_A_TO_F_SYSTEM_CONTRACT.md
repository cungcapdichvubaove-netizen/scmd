# Business Workflow A→F System Contract — SCMD Pro

Status: **Accepted implementation contract after Phase F**  
Applies to: SCMD Pro business-domain workflow patches A→F  
Audience: developers, reviewers, QA, operators, release owners

This document consolidates the business-domain changes introduced from Phase A to Phase F. It is the bridge between individual patch manifests and the system-level product/architecture documents (`README.md`, `WHITEPAPER.md`, `DOCUMENTATION.md`).

## 1. Non-negotiable principle

SCMD Pro must not overload a primary record with fields that actually belong to a separate legal, financial, HR, scheduling, inventory, or contract workflow.

If a workflow has its own lifecycle, source document, evidence file, approval, status, dates, money/quantity effect, audit trail, and dashboard warning, it must be modeled as a dedicated source record rather than as a loose field or generic proposal.

Generic `workflow.Proposal` / `BaoCaoDeXuat` records may remain for ad-hoc internal proposals. They are **not** the SSOT for shift change, leave, labor contract, customer payment settlement, payroll deduction, asset recovery, or offboarding inventory.

## 2. Phase A — Labor contract as HR source record

### Source records

- `users.HopDongLaoDong`
- `users.PhuLucHopDongLaoDong`

### Contract

`NhanVien.loai_hop_dong` is legacy/compatibility only. It must not be used as the SSOT for an active labor contract.

Labor contract state, effective dates, expiry, file evidence, approval context, status, notes, and contract appendix history belong to `HopDongLaoDong` / `PhuLucHopDongLaoDong`.

### Dashboard obligations

HR dashboard must flag at least:

- contracts expiring within 30 days;
- expired contracts while the employee remains active;
- official employees without active labor contract records.

## 3. Phase B — Dedicated business records for HR, operations, payroll and contract finance

### Source records

Users/HR:

- `users.DonNghiPhep`
- `users.QuyetDinhNghiViec`
- `users.OffboardingChecklist`
- `users.HoSoBaoHiem`

Operations:

- `operations.ShiftChangeRequest`

Accounting/payroll source records:

- `accounting.TamUngLuong`
- `accounting.KhoanKhauTruNhanVien`

Clients/contract finance:

- `clients.PhuLucHopDongDichVu`
- `clients.BienBanNghiemThu`
- `clients.HoaDon`
- `clients.CongNo`

### Contract

- Mandatory social insurance dashboard checks use active `HoSoBaoHiem` records scoped specifically to BHXH. `BAO_HIEM_KHAC`, `BHYT`, or `BHTN` alone do not satisfy the mandatory BHXH warning.
- `clients` owns contract receivable lifecycle in the current architecture. `accounting` consumes receivable reports/exports in a later integration phase and must not create duplicate `accounting.HoaDon`, `accounting.CongNo`, or `accounting.ThanhToanKhachHang` without a migration/facade decision.

## 4. Phase C — Workflow integration and transition policy

### State transition policy

The following records must not have free-form state mutation:

- `HopDongLaoDong`
- `DonNghiPhep`
- `QuyetDinhNghiViec`
- `HoSoBaoHiem`
- `ShiftChangeRequest`
- `TamUngLuong`
- `KhoanKhauTruNhanVien`
- `PhuLucHopDongDichVu`
- `BienBanNghiemThu`
- `HoaDon`
- `CongNo`

Direct transitions such as `APPROVED -> DRAFT`, `ACTIVE -> DRAFT`, and `PAID -> DRAFT` are invalid unless an explicit recovery path is designed and audited.

### Shift change workflow

`operations.ShiftChangeRequest` is the SSOT for shift swap/overtime/cancel-shift workflows. `BaoCaoDeXuat` is not the SSOT for shift change.

Core lifecycle:

```text
DRAFT -> PENDING_APPROVAL -> APPROVED -> APPLIED
PENDING_APPROVAL -> REJECTED / CANCELLED
APPROVED -> CANCELLED
APPLIED -> terminal
```

Approval and apply must pass business authorization in the application layer, not only DRF/admin permissions.

Apply must check payroll lock, attendance already recorded, duplicate shift risk, replacement employee status, object scope, and audit logging.

Swap-rate reports count actual applied changes through `APPLIED`, not merely approved-but-not-applied requests.

### Leave/payroll integration

`DonNghiPhep APPROVED` is surfaced to scheduling/payroll snapshots. It must not automatically delete shifts. It must prevent approved paid leave from being treated as unauthorized absence and must distinguish unpaid leave in payroll snapshots.

## 5. Phase D — Scoped reporting, payroll hardening and static guards

### Swap-rate scope

`GetSwapRateReportUseCase` must receive `user`, `allowed_targets_qs`, or explicit `system_context=True`. API/report calls must not silently query all targets when a developer forgets to pass actor scope.

### Payroll pipeline

Official pipeline:

```text
CalculatePayrollUseCase
  -> PayrollSourceReconciliationUseCase
  -> review
  -> LOCKED / PAID
```

`CalculatePayrollUseCase` must not silently overwrite existing Phase C reconciliation snapshots. If recalculation occurs after reconciliation, the snapshot must be preserved and marked `NEEDS_RECONCILIATION`, or reconciliation must run again by explicit option.

Locked/paid payroll periods must not be mutated by calculation/reconciliation.

### Leave proration

Leave overlap with payroll period is prorated to the days inside the target period. Snapshot keys must distinguish:

- `leave_total_days`
- `leave_days_in_this_period`

Half-day/decimal absence support remains a later payroll schema refinement unless explicitly implemented end-to-end.

### Static guard

Production code must not set `.trang_thai = ...` directly for controlled business records outside sanctioned places. The regression suite must scan for direct status mutation and only whitelist transition-status methods, guarded admin save paths, sanctioned application use cases, tests, and migrations.

## 6. Phase E — Customer payment and receivable settlement

### Source records

- `clients.ThanhToanKhachHang`
- `clients.PhanBoThanhToanHoaDon`
- `clients.HoaDon`
- `clients.CongNo`

### Official pipeline

```text
ReceiveCustomerPaymentUseCase
  -> AllocateCustomerPaymentUseCase
  -> RecalculateReceivableStatusUseCase
  -> receivable review/report
```

### Contract

`CongNo.so_tien_da_thu` is a synchronized/derived value from allocation records. It is not a manually editable source field after Phase E.

Every payment/allocation mutation must pass `CustomerPaymentPermissionPolicy` in the application layer.

Allocated financial source records are append-only for source fields:

- allocated `ThanhToanKhachHang` cannot silently change voucher code, amount, customer, contract, payment date, payment method, transaction code, or evidence file;
- created `PhanBoThanhToanHoaDon` cannot silently change payment, invoice, receivable, or allocation amount.

Invoice-only allocation is rejected. Every allocation must target a concrete `CongNo`; invoice status is recalculated from debt allocations to avoid split-brain states where an invoice appears paid but receivable remains open.

Report keys must make semantics explicit:

- `total_open_receivable`
- `total_collected_allocation`
- `total_remaining_open_receivable`

Legacy aliases may remain for template compatibility but should not be used in new UI.

## 7. Phase F — Asset recovery and offboarding inventory

### Source records

- `inventory.PhieuThuHoi`
- `inventory.ChiTietPhieuThuHoi`
- `inventory.BienBanMatHongVatTu`
- `inventory.InventoryLedgerEntry` with recovery document references

### Official pipeline

```text
PhieuXuat / ChiTietPhieuXuat
  -> PhieuThuHoi / ChiTietPhieuThuHoi
  -> InventoryLedgerEntry
  -> optional BienBanMatHongVatTu
  -> optional KhoanKhauTruNhanVien PENDING_APPROVAL
  -> payroll reconciliation later
```

### Contract

`OffboardingChecklist` boolean fields remain for compatibility, but they are not the SSOT for asset recovery.

Good returned items create inventory ledger `IN` entries. Voiding a posted recovery creates reversal `OUT` entries. Lost/damaged/missing items do not increase stock; they create `BienBanMatHongVatTu` and may create a payroll deduction source record through an approval use case.

Phase F must not write directly to `ChiTietLuong` and must not use fake `PhieuNhap` records to represent recovery.

Phase F v2 hardens void behavior: a posted recovery cannot be voided while active damage/loss reports or non-cancelled payroll-deduction records exist. Void guards must execute before inventory reversal ledger creation so blocked void attempts never mutate stock.

Offboarding completion must be blocked while the employee still has outstanding issued assets or unresolved damage/loss reports.

## 8. Audit, permission and append-only rules

Business workflows with legal, financial, payroll, shift, inventory, or customer-contract impact must follow these rules:

1. Mutations go through application use cases where possible.
2. Status changes use transition policy or `transition_status()`, not direct assignment.
3. Sensitive approvals and applications use object-level permission policy, not only `IsAuthenticated`.
4. Source financial/inventory evidence becomes append-only once it affects downstream records.
5. Correction requires explicit reversal/adjustment records, not silent edit/delete.
6. Locked/paid payroll periods are not mutated by downstream corrections.
7. All meaningful source-to-effect changes write `main.AuditLog` or the established audit mechanism.

## 9. Current non-goals and forward roadmap

Not completed by Phase F:

- customer payment/allocation reversal records;
- serialized asset custody for each individual item;
- decimal/half-day payroll absence end-to-end;
- `ThanhToanKhachHang` statuses split into `PARTIALLY_ALLOCATED` / `FULLY_ALLOCATED`;
- `ThanhToanKhachHangReversal` / `PhanBoThanhToanHoaDonReversal`;
- `PhieuThuHoiReversal` / damage-report correction records;
- `ThanhToanKhachHang` export/facade into `accounting` reports;
- `PhieuThuHoi` deeper warehouse dashboard queues;
- Phase G `PhuongAnBaoVe` / security service plan lifecycle.

## 10. Minimum release checks for A→F workflows

Run in Docker or the target development environment:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test users.tests_labor_contract_phase_a users.tests_business_domain_phase_b
python manage.py test users.tests_business_workflow_phase_c users.tests_business_workflow_phase_d
python manage.py test clients.tests_phase_e_customer_payment
python manage.py test inventory.tests_phase_f_asset_recovery
python manage.py test operations accounting users clients inventory
```

Static checks that should remain in CI/review:

```bash
grep -R "BaoCaoDeXuat" -n operations/application operations/api_views.py
grep -R "\.trang_thai\s*=" -n users operations accounting clients inventory
find static/ -name "*.py"
find . -path "*/templates/*" -name "*.py"
```

Grep results require classification. Tests, migrations, vendor artifacts, and sanctioned transition methods are not automatically bugs; production workflow code that directly mutates status or bypasses source records is a release blocker.
