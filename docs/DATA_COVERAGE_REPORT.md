# SCMD Pro Digital Twin Data Coverage Report

## Coverage status

| Domain | Native DB coverage | Notes |
|---|---:|---|
| Company / branches | Partial | CompanyInfo native; branch metadata in master-data contract/export context |
| Departments / roles | Yes | PhongBan, ChucDanh, Group |
| HR 1200 staff | Yes | NhanVien/User/HocVan/BangCapChungChi |
| Customers 80 | Yes | KhachHangTiemNang |
| Contracts 160 | Yes | HopDong |
| Sites 100 | Yes | MucTieu + ViTriChot |
| Warehouses >=120 | Snapshot | No native warehouse model; JSONL linked to sites |
| Assets >=20,000 | Snapshot + inventory docs | Native VatTu/PhieuNhap/PhieuXuat; serial units JSONL |
| Cameras >=4,000 | Snapshot | No native camera model; JSONL linked to sites |
| Checkpoints >=5,000 | Yes | DiemTuanTra |
| Patrol routes >=500 | Yes | LoaiTuanTra |
| Patrol history >=50,000 | Yes | LuotTuanTra, limited GhiNhan evidence for performance control |
| Incidents >=150,000 | Yes | BaoCaoSuCo |
| AI alerts >=500,000 | Snapshot | No native AI alert model; JSONL linked to camera/site/incident |
| Finance 36 months | Yes + snapshot | BangLuongThang, ChiTietLuong, invoice JSONL |
| Realtime simulation | Yes | AuditLog realtime event stream simulator |

## Production-readiness interpretation

This patch creates a production-safe Digital Twin foundation without unreviewed schema expansion. It is suitable for demo, QA, UAT and load-test preparation. Full production-grade Camera/AI/Warehouse analytics requires native models and migrations in a later architecture phase.

## Final static backtest notes

The generator now seeds organization-level work-history records and site-level assignment histories through `LichSuCongTac`, assigns users to business-role groups through their `ChucDanh.nhom_quyen`, writes branch snapshots, uses deterministic random seeding, and avoids duplicate patrol-session growth by creating only missing patrol history for Digital Twin routes.

Native schema gaps remain intentionally represented as JSONL snapshots: physical warehouses, serialized asset units, cameras and AI alerts.


## Operational side-effect policy

`digital_twin_seed` suppresses production Celery/WebSocket/cache side effects by default so large synthetic incident and attendance batches do not flood Redis or generate noisy realtime alerts. Use `--allow-side-effects` only when the explicit test objective is to benchmark notification fan-out.
