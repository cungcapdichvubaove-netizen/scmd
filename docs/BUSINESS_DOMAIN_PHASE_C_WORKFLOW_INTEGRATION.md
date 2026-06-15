# Business Domain Phase C — Workflow Integration

## Scope

Phase C turns the Phase A+B business records from admin-only source records into guarded operational workflows without adding broad schema changes.

## Decisions

- `ShiftChangeRequest` is the SSOT for shift-change/swap/overtime/cancel-shift workflows. `BaoCaoDeXuat` remains available for generic field proposals, but swap-rate reports and mobile đổi-ca APIs no longer use it as the SSOT.
- `DonNghiPhep` is the SSOT for leave requests. Approved leave is surfaced to Operations as a schedule conflict requiring dispatch; it does not automatically delete or rewrite shifts.
- Payroll reconciliation uses Phase A+B source records (`TamUngLuong`, `KhoanKhauTruNhanVien`, `HoSoBaoHiem`, `DonNghiPhep`) and preserves legacy source metadata (`SoQuy` etc.) until a later migration retires those sources.
- Workflow state changes must pass `WorkflowTransitionPolicy`; terminal states cannot be reopened by `transition_status()`.

## Guardrails

- Do not apply shift changes into `PhanCongCaTruc` unless the request is `APPROVED`.
- Do not apply shift changes when the source/target payroll period is `LOCKED` or `PAID`.
- Do not apply shift changes when the original assignment already has attendance.
- Do not treat approved paid leave as unauthorized absence.
- Do not write reconciliation into `BangLuongThang` periods that are `LOCKED` or `PAID`.

## Deferred

- Full UI approval screens for every workflow are not part of Phase C.
- Automatic offboarding execution into employee status remains deferred until explicit HR policy is approved.
- Invoice/debt posting into accounting reports remains a future facade/integration phase.
