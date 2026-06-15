# SCMD Pro — Business Workflow Phase C v2 Security & Idempotency Decision

## Scope

This decision record refines Phase C business workflow integration after security/business audit.
It does not introduce broad new models. It only adds the minimum schema change required for
`operations.ShiftChangeRequest` to distinguish an approved request from a request already applied
to the roster.

## Shift-change authorization

`ShiftChangeRequest` approval and application must not rely on `IsAuthenticated` alone.
Authorization is enforced in the application layer through:

- `operations.application.shift_change_permission_policy.ShiftChangePermissionPolicy`
- `operations.application.shift_change_use_cases.ApproveShiftChangeRequestUseCase`
- `operations.application.shift_change_use_cases.ApplyShiftChangeRequestUseCase`

Rules:

- Employees may create only their own shift-change request.
- The requester may not approve their own request.
- `ban_giam_doc`, `nghiep_vu`, and technical superusers may approve/apply globally.
- `doi_truong` and `quan_ly_vung` may approve/apply only when every relevant source/target site is inside their managed scope.
- `ke_toan` alone is not an operational approver for shift-change workflows.
- Apply has the same authorization bar as approve and is enforced inside the use case, not only the API.

## Shift-change idempotency and metrics

`ShiftChangeRequest.TrangThai.APPLIED` is added as a terminal state.

Valid apply transition:

```text
APPROVED -> APPLIED
```

After a successful apply into `PhanCongCaTruc`, the request transitions to `APPLIED`.
A second apply is rejected because the use case only accepts `APPROVED` requests.

Swap-rate metrics now distinguish:

- submitted/requested shift-change records
- approved shift-change records
- applied shift-change records

Operational swap-rate uses `APPLIED` only, because this represents a real roster mutation.

## Payroll advance reconciliation ownership

`TamUngLuong` remains the source record for an advance request/payment.
`KhoanKhauTruNhanVien` remains the payroll deduction schedule.

To prevent double counting:

- direct `TamUngLuong` values are added to payroll only when there is no linked approved deduction;
- if `KhoanKhauTruNhanVien.tam_ung_id` exists, the linked `TamUngLuong` is recorded in the snapshot but excluded from direct advance summing;
- the approved deduction is the payroll amount source for that advance.

## Known Phase D hardening

Transition matrices are enforced via `transition_status()` and admin save handling. Direct production code should not mutate
`obj.trang_thai` followed by `obj.save()` outside workflow use cases. Phase D should add model-level or static-analysis protection
for direct status assignment in production modules.
