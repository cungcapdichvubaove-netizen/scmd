# Business Domain Phase C/D Roadmap

## Purpose

Phase A+B created source records and audit trails without mutating payroll, shift assignment, or accounting reports automatically. This was intentional to reduce regression risk. Phase C/D must add controlled application use cases and transition policy instead of letting admin saves directly mutate downstream ledgers or schedules.

## Phase C — Transition policy hardening

Add a shared transition matrix per lifecycle model. Each model should define allowed transitions and `transition_status()` must reject illegal jumps with `ValidationError` unless an explicit privileged recovery path exists.

Example policy shape:

```python
allowed_transitions = {
    DRAFT: [PENDING_APPROVAL, CANCELLED],
    PENDING_APPROVAL: [APPROVED, REJECTED, CANCELLED],
    APPROVED: [ACTIVE, TERMINATED],
    ACTIVE: [EXPIRED, TERMINATED],
    EXPIRED: [],
    TERMINATED: [],
}
```

Mandatory coverage:

- Prevent direct `DRAFT → ACTIVE` when approval/signature is required.
- Prevent reverting terminal states such as `EXPIRED → DRAFT`, `TERMINATED → DRAFT`, or `PAID → DRAFT`.
- Keep audit logging for every allowed transition.
- Add tests for allowed and denied paths for each Phase A+B model.

## Phase D — Controlled downstream integration use cases

Do not wire source records directly to downstream effects inside model `save()` or admin `save_model()`. Add explicit application/use-case services with idempotency, validation, audit log, and rollback strategy.

Planned integrations:

- `DonNghiPhep → payroll`: approved paid/unpaid leave should affect payroll attendance/allowance calculation through a payroll adjustment or attendance summary integration.
- `ShiftChangeRequest → PhanCongCaTruc`: approved shift changes or overtime requests should create or update shift assignments only through a scheduling use case that respects payroll lock policy.
- `TamUngLuong/KhoanKhauTruNhanVien → ChiTietLuong`: approved advances/deductions should be applied to payroll lines through a payroll calculation use case, not by direct model mutation.
- `HoaDon/CongNo → accounting reports`: contract receivable data should feed accounting reports after reconciliation rules are agreed; Phase A+B keeps `clients.HoaDon` and `clients.CongNo` as source records.

## Phase D acceptance gates

- Use-case tests prove idempotency: applying the same approved source record twice does not duplicate downstream entries.
- Payroll lock tests prove approved requests cannot alter locked payroll periods without an explicit adjustment/reopen flow.
- Audit tests show actor, source record, target record, and before/after values.
- Dashboard tests show pending unapplied approved records as action items.

## Phase D — Executed hardening scope

Phase D locks the remaining integration risks without adding broad schema:

- Swap-rate report authorization and scoped target queries. API callers must pass a user into `GetSwapRateReportUseCase`; scoped roles only see managed targets, and non-operational accounting/employee users receive 403. Phase D v2 further requires explicit `system_context=True` for trusted scheduled/internal full-tenant report runs, so a future API cannot accidentally omit user context and expose all targets.
- Payroll pipeline order: `CalculatePayrollUseCase → PayrollSourceReconciliationUseCase → review → LOCKED/PAID`. If payroll is calculated after a Phase C reconciliation snapshot already exists, calculation preserves the source snapshot and marks it `NEEDS_RECONCILIATION` instead of silently overwriting it.
- Leave proration: approved leave crossing a payroll boundary is counted only for overlapping days in the current period, with both `leave_total_days` and `leave_days_in_this_period` recorded.
- Static guard: Phase A+B/C workflow status mutation must go through transition methods/admin guards/sanctioned application use cases; Phase D v2 no longer whitelists the whole `/application/` tree. An application file with direct `.trang_thai =` is allowed only when it calls `transition_status()`/`WorkflowTransitionPolicy` or is explicitly listed as a legacy/sanctioned exception.

## Phase E/F/G — Explicitly not in Phase D

- Phase E: `ThanhToanKhachHang` / customer payment collection and settlement workflow.
- Phase F: `PhieuThuHoi` / asset recovery and offboarding-return workflow.
- Phase G: `PhuongAnBaoVe` / protection-plan source record linked to service contract, target, guard posts, patrol and SLA expectations.

## Phase E follow-up — decimal absence precision

Phase D records leave proration in snapshots using decimal values: `leave_total_days`, `leave_days_in_this_period`, `approved_unpaid_leave_days`, and `unpaid_leave_days`. The legacy `ChiTietLuong.so_ngay_nghi` field remains integer-scoped in this patch to avoid a schema migration and payroll regression. If SCMD Pro enables half-day leave, Phase E must add decimal leave/payroll absence handling end-to-end instead of relying on integer `so_ngay_nghi`. Acceptance wording: half-day leave must preserve decimal leave/payroll absence precision in calculation, reconciliation, review UI and reports.
