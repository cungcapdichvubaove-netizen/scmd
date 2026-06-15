# SCMD Pro Incident Lifecycle Contract

This document is the authoritative contract for incident status semantics. It exists to remove ambiguity between historical Vietnamese labels in old migrations, UI copy, and the current business workflow.

## Authoritative model and policy

- Source model: `operations.models.BaoCaoSuCo`
- Transition policy: `operations.application.incident_transition_policy.IncidentTransitionPolicy`
- Stable identity: `BaoCaoSuCo.ma_su_co`

## Status mapping

| Stable code | Vietnamese display | Contract meaning | Terminal |
|---|---|---|---|
| `CHO_XU_LY` | Chờ xử lý | Incident is recorded and awaiting handling | No |
| `DANG_XU_LY` | Đang xử lý | Incident is actively being handled | No |
| `DA_XU_LY` | Đã xử lý (Không đền bù) | Operational handling completed without compensation; not the final closed state | No |
| `CHO_DEN_BU` | Chờ đền bù (Có thiệt hại) | Compensation/deduction/recovery is pending | No |
| `HOAN_TAT` | Hoàn tất xử lý | Final closed state after handling/reconciliation is complete | Yes |
| `HUY` | Đã hủy bỏ | Cancelled/voided incident record | Yes |

## Rules

1. Do not rename database values to English aliases such as `RESOLVED` or `CLOSED`.
2. `DA_XU_LY` is **not** terminal. It means handled without compensation and may still be reopened or moved to compensation if evidence changes.
3. Closed incident set is exactly `HOAN_TAT`, `HUY`.
4. Reopen target is `DANG_XU_LY`, with audit reason.
5. Incident compensation must be traceable through business source records and payroll/accounting reconciliation. Payroll must not consume free-text incident amounts directly.
6. Historical labels in migrations are audit history, not permission for new docs/UI to invent a different state machine.
