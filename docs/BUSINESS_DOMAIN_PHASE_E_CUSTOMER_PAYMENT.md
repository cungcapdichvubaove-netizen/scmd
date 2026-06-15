# Business Workflow Phase E — Customer Payment & Receivable Settlement

## Scope

Phase E turns customer receivables from editable result fields into traceable workflow records.

Added source records:

- `clients.ThanhToanKhachHang`
- `clients.PhanBoThanhToanHoaDon`

Existing derived records:

- `clients.HoaDon`
- `clients.CongNo`

## Official pipeline

```text
ReceiveCustomerPaymentUseCase
  -> AllocateCustomerPaymentUseCase
  -> RecalculateReceivableStatusUseCase
  -> receivable review/report
```

`CongNo.so_tien_da_thu` is synchronized from allocation records and must not be treated as an admin-editable source of truth after Phase E.

## Status rules

Payment:

```text
DRAFT -> RECEIVED -> ALLOCATED
DRAFT -> CANCELLED
RECEIVED -> CANCELLED
ALLOCATED -> terminal in Phase E
```

Invoice:

```text
ISSUED -> PARTIALLY_PAID -> PAID
ISSUED/PARTIALLY_PAID -> OVERDUE
```

Receivable:

```text
OPEN -> PARTIAL -> PAID
OPEN/PARTIAL -> OVERDUE
OPEN/PARTIAL/OVERDUE -> WRITTEN_OFF
```

`PAID` is only valid when allocation is sufficient. Direct PAID transitions without enough allocation are rejected.

## Recovery boundary

Canceling an allocated payment is blocked in Phase E. A future recovery phase should introduce explicit reversal/adjustment records rather than deleting allocation or audit history.

## Not in Phase E

- No asset recovery record (`PhieuThuHoi`) — planned for Phase F.
- No guard service plan (`PhuongAnBaoVe`) — planned for Phase G.
- No accounting refactor. Accounting consumes client receivable report data in a future integration phase.

## Phase E v2 hardening

Phase E v2 keeps all Phase E source-record fixes and adds the minimum hardening
needed before broader rollout:

- Customer payment mutations must pass `CustomerPaymentPermissionPolicy` in the
  application layer, not only Django admin permissions.
- Only superusers, `ban_giam_doc`, and `ke_toan` may receive, allocate, cancel,
  or recalculate customer payment settlement records.
- CRM/sales may view receivable report context through `nhan_vien_kinh_doanh`,
  but cannot mutate payment/allocation source records.
- `PhanBoThanhToanHoaDon` must not be deleted directly in admin. Any reversal or
  recovery path must be modeled explicitly in a later phase so audit history is
  preserved.
- Allocation consistency is checked across tenant, contract, and customer to
  prevent cross-contract or cross-customer settlement mistakes.

## Phase E v3 hardening

Phase E v3 closes two finance-integrity blockers found after v2 review.

### Append-only financial source records

`ThanhToanKhachHang` becomes immutable for core source fields after it has any
allocation record. These fields cannot be edited directly after allocation:

- `ma_phieu`
- `so_tien`
- `khach_hang`
- `hop_dong`
- `ngay_thanh_toan`
- `hinh_thuc`
- `ma_giao_dich`
- `file_chung_tu`

`PhanBoThanhToanHoaDon` is append-only for source fields after creation:

- `thanh_toan`
- `hoa_don`
- `cong_no`
- `so_tien`

Admin exposes allocated payment/allocation source fields as readonly and blocks
save-time mutation. Correction must be handled by a later explicit reversal or
adjustment record, not by silently editing the original source record.

### Allocation target integrity

Phase E v3 uses the safer contract: every allocation must target a concrete
`CongNo`. Invoice-only allocation is rejected because it can mark `HoaDon` as
paid while the linked `CongNo` remains open. When `cong_no` is supplied,
`hoa_don` is derived from that debt if omitted.

### Report semantics

Dashboard totals now expose clearer names:

- `total_open_receivable`
- `total_collected_allocation`
- `total_remaining_open_receivable`

Legacy aliases remain for template compatibility:

- `total_receivable`
- `total_collected`
- `total_remaining`

### Phase E4/E5 follow-up

A later recovery phase should add one of:

- `ThanhToanKhachHangReversal`
- `PhanBoThanhToanHoaDonReversal`
- explicit adjustment/correction records

A later status refinement may split `ALLOCATED` into
`PARTIALLY_ALLOCATED` and `FULLY_ALLOCATED`. Phase E v3 keeps the existing
status enum to avoid an unnecessary migration while hardening integrity.
