# GLOSSARY.md — SCMD Pro Domain Vocabulary

Version: 1.0.0  
Status: Shared vocabulary for developers, reviewers and AI coding agents  
Updated: 2026-06-08

---

## Purpose

This glossary standardizes SCMD Pro domain language. Use these terms in code comments, UI copy, documentation, tests and AI-assisted implementation notes.

SCMD Pro is a professional security-service operations platform. It is not a cyber dashboard, war-room UI, generic ERP, microservices project, or true SaaS multi-tenant system.

---

## Core business terms

| Term | Vietnamese UI term | Meaning | Typical model/module |
|---|---|---|---|
| Lead | Khách hàng tiềm năng | Potential customer before conversion | `clients.KhachHangTiemNang` |
| Customer | Khách hàng | Organization buying security service | `clients.KhachHang` if present / clients module |
| Contract | Hợp đồng | Commercial/security service agreement | `clients.HopDong` |
| Site | Mục tiêu bảo vệ | Protected customer location/site | `clients.MucTieu` |
| Guard post | Chốt bảo vệ / Vị trí chốt | Specific post inside a site | `operations.ViTriChot` |
| Shift | Ca trực | Work shift at site/post/date/time | `operations.PhanCongCaTruc` |
| Attendance | Chấm công | Check-in/check-out with time/GPS/photo | `operations.ChamCong` |
| Patrol | Tuần tra | Patrol route/session/checkpoint activity | `inspection.LoaiTuanTra`, `LuotTuanTra`, `GhiNhanTuanTra` |
| Checkpoint | Điểm tuần tra | QR/NFC/GPS checkpoint in patrol route | `inspection.DiemTuanTra` |
| Incident | Sự cố | Field incident, damage, violation, event | `operations.BaoCaoSuCo` |
| Alive check | Kiểm tra quân số / Alive Check | Manpower/guard presence check | `operations.KiemTraQuanSo` |
| Manpower | Quân số | Required/actual number of guards | operations/dashboard |
| Payroll period | Kỳ lương | Payroll month/period | `accounting.BangLuongThang` |
| Payroll detail | Chi tiết lương | Employee salary line/snapshot | `accounting.ChiTietLuong` |
| Payroll adjustment | Điều chỉnh lương | Retroactive adjustment after lock/paid status | `accounting.PayrollAdjustment` concept |
| Inventory item | Vật tư / quân tư trang | Uniform, equipment, tools | `inventory.VatTu` |
| Issue note | Phiếu xuất | Stock/equipment issue document | `inventory.PhieuXuat` |
| Receipt note | Phiếu nhập | Stock receipt document | `inventory.PhieuNhap` |
| Ledger entry | Bút toán kho / biến động tồn | Immutable stock movement | `inventory.InventoryLedgerEntry` |
| Reconciliation | Đối soát | Process to verify operation/payroll/stock data | cross-module |
| Audit trail | Lưu vết kiểm toán | Record of sensitive action | `main.AuditLog` |

---

## Access-scope terms

| Term | Meaning | Notes |
|---|---|---|
| RBAC | Functional permission: what action type user can perform | Not enough by itself |
| Object scope | Which staff/site/shift/object user can see or act on | Mandatory for sensitive workflows |
| Scope level | SELF, SITE, REGION, OPERATIONS, HR, PAYROLL, INVENTORY, EXECUTIVE | Used by policy and override rules |
| Direct scope | Scope granted by job assignment/role | Standard audit |
| Temporary delegation | Time-limited delegated scope from one user to another | Must include delegator/delegatee/time/permission/audit |
| Historical scope | Scope evaluated at event time, not current state only | Required for attendance/payroll/incidents |
| Multi-region assignment | One guard may belong to more than one site/regional staffing pool | Use `NhanVienRegionAssignment` concept |
| Override policy | Rule preventing lower scope from silently changing higher-scope decisions | Use change request where needed |
| PolicyResult | Standard allow/deny result with code, message and details | Required for contextual deny UX |

---

## Time and date terms

| Term | Meaning | Rule |
|---|---|---|
| `shift.start_at` | Shift start timestamp | Source for canonical work date |
| `shift.end_at` | Shift end timestamp | May be next day for night shifts |
| `work_date` | Business date of shift | Local date of `shift.start_at` unless explicit split exists |
| Event time | Time the data was generated | Used for historical-scope checks |
| Effective date | Date a transfer/scope/delegation begins | Must be explicit |

---

## Brand terms

| Term | Correct usage |
|---|---|
| SCMD | Company/parent brand, legal/copyright/vendor/about context |
| SCMD Pro | User-facing product name |
| ERP | Capability group only; not product name |
| War Room / Cyber / Tactical | Do not use in internal business UI |
| Bảng điều hành vận hành | Preferred Vietnamese operations dashboard wording |

---

## Naming guidance

Prefer Vietnamese business terms in UI labels and reports. Code may use existing model names but should not introduce cyber/war-room naming.

Examples:

```text
Correct: Mục tiêu bảo vệ, Chốt bảo vệ, Ca trực, Tuần tra, Sự cố, Quân số, Đối soát
Avoid: War Room, Tactical, Cyber, Sentinel, Security Command System
```
