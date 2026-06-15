# SCMD Pro Digital Twin Dataset Architecture

Status: Phase 1 implementation for Django/PostgreSQL layered monolith.

## Source-of-truth finding

The attached SCMD Pro codebase is a Django/PostgreSQL/PostGIS monolith, not a Prisma schema project. No native `Camera`, `AiAlert`, `Warehouse`, or serialised `AssetUnit` Django models exist in the current schema. The generator therefore follows a no-schema-break strategy:

- Native Django models are populated where the schema exists: HR, customers, contracts, sites, posts, shifts, attendance, patrol, incidents, inventory documents, payroll.
- Missing subsystems are emitted as JSONL snapshots with foreign-key references to real native rows: cameras, AI alerts, warehouse inventory and serialised asset units.
- No hardcoded database primary keys are used. Deterministic natural keys use the `DT-*` namespace.

## Module map

```text
seed/
├── master-data/        # user-facing architecture placeholder
├── master_data/        # Python package for organization, departments, roles
├── hr/                 # employees, users, certificates, education
├── customers/          # customer accounts and opportunities
├── contracts/          # contracts and business terms
├── sites/              # protected sites and guard posts
├── inventory/          # native inventory + JSONL warehouse/asset snapshots
├── patrol/             # shifts, attendance, routes, checkpoints, patrol history
├── incidents/          # 36-month incident distribution
├── ai-alerts/          # user-facing architecture placeholder
├── ai_alerts/          # JSONL camera and AI alert generator
├── finance/            # payroll periods and payslip snapshots
├── realtime/           # realtime event simulator
└── orchestrator/       # profile, reset, runner and shared context
```

## Relationship map

```text
CompanyInfo
PhongBan ─┐
ChucDanh ─┼── NhanVien ─── LichSuCongTac ─── MucTieu
User ─────┘

KhachHangTiemNang ─── CoHoiKinhDoanh ─── HopDong ─── MucTieu ─── ViTriChot
                                                        │
                                                        ├── LoaiTuanTra ─── DiemTuanTra
                                                        │        └── LuotTuanTra ─── GhiNhanTuanTra
                                                        └── PhieuXuat / CongCuTaiMucTieu

CaLamViec ─── PhanCongCaTruc ─── ChamCong
        │             └── BaoCaoSuCo
        └── KiemTraQuanSo

LoaiVatTu ─── VatTu ─── ChiTietPhieuNhap ─── PhieuNhap
        │      └────── ChiTietPhieuXuat ─── PhieuXuat
        └────── CongCuTaiMucTieu

BangLuongThang ─── ChiTietLuong ─── NhanVien
CauHinhLuong ─── NhanVien
```

## Scale profiles

| Profile | Purpose | Notes |
|---|---|---|
| smoke | CI/local validation | Fast; validates FK and command path |
| small | QA/UAT demo | Useful for sales demo and integration testing |
| full | Enterprise benchmark | Encodes 1200 staff, 80 customers, 160 contracts, 100 sites, 20k asset snapshots, 4k cameras, 50k patrol sessions, 150k incidents, 500k AI alert snapshots |

Full scale requires `--allow-full-scale` to avoid accidental large writes.

## Idempotency

- Native rows use deterministic natural keys such as `DT-HD-000001`, `DT-SITE-000001`, `DT-PN-000001`.
- Commands use `get_or_create` / `update_or_create` where safe.
- Reset deletes only deterministic Digital Twin records and preserves append-only `AuditLog`.

## Security and privacy

- No real personal data is used.
- Email domain is `scmdpro.local`.
- CCCD values are synthetic 12-digit strings.
- Phone numbers are deterministic synthetic Vietnamese-format numbers.
- Exported JSONL files are generated under `var/digital_twin/` and are not static web assets.

## Native coverage limitation

The current schema has no native Camera/AiAlert/Warehouse/AssetUnit models. Adding those models should be a separate schema-design phase with migrations, admin, API and policy coverage. This generator deliberately avoids creating unreviewed production tables.


## Operational side-effect policy

`digital_twin_seed` suppresses production Celery/WebSocket/cache side effects by default so large synthetic incident and attendance batches do not flood Redis or generate noisy realtime alerts. Use `--allow-side-effects` only when the explicit test objective is to benchmark notification fan-out.
