# DOMAIN_DECISION_RECORD.md — Guard Patrol vs Inspection Patrol

Status: Phase 2 + v3 production hardening cumulative patch
Base: `43.zip` + `scmdpro_43_guard_patrol_domain_correction_patch_v3`
Date: 2026-06-14

## Decision

SCMD Pro separates two different business domains:

1. **Guard Patrol / Tuần tra bảo vệ tại mục tiêu**
   - Owner: `operations` / Phòng nghiệp vụ / Phòng vận hành.
   - Canonical namespace: `operations`.
   - Canonical mobile routes:
     - `/operations/mobile/tuan-tra/`
     - `/operations/mobile/tuan-tra/bat-dau/<id>/`
     - `/operations/mobile/tuan-tra/thuc-hien/<id>/`
     - `/operations/mobile/tuan-tra/ghi-nhan/`
     - `/operations/mobile/tuan-tra/hoan-thanh/<id>/`
   - Canonical application layer: `operations/application/guard_patrol_use_cases.py`.
   - Canonical schedule/task entities:
     - `operations.LichTuanTraVanHanh`
     - `operations.NhiemVuTuanTraCa`
   - Patrol execution evidence is traceable from legacy transition tables back to:
     - `PhanCongCaTruc`
     - `LichTuanTraVanHanh`
     - `NhiemVuTuanTraCa`
   - Canonical permissions:
     - `thuc_hien_tuan_tra_bao_ve`
     - `quan_ly_tuyen_tuan_tra_van_hanh`
     - `quan_ly_lich_tuan_tra_van_hanh`
     - `xem_doi_soat_tuan_tra_van_hanh`
     - `xu_ly_canh_bao_tuan_tra_van_hanh`

2. **Inspection Patrol / Thanh tra kiểm tra mục tiêu**
   - Owner: `inspection` / Phòng thanh tra & giám sát.
   - Canonical namespace: `inspection`.
   - Scope: kế hoạch kiểm tra mục tiêu, checklist/hạng mục, biên bản, vi phạm, kiến nghị khắc phục, báo cáo ban giám đốc.
   - Inspection may read operations patrol compliance by policy, but does not own or mutate daily guard patrol schedules by default.

## Why

Tuần tra bảo vệ hằng ngày là dữ liệu vận hành gắn với ca trực, mục tiêu, chốt bảo vệ, QR/GPS/ảnh, sự cố, đối soát và payroll. Thanh tra/giám sát là luồng độc lập để kiểm tra chất lượng dịch vụ, quân số, tác phong, đồng phục, công cụ, sổ sách và kiến nghị khắc phục.

If guard patrol uses `inspection` as the canonical route/use-case owner, reporting, permissions and accountability become incorrect. Therefore all runtime orchestration is owned by `operations`.

## Transition plan

This cumulative patch intentionally does **not** migrate legacy QR/route/evidence tables out of `inspection` yet. Current transition tables still live under `inspection`:

- `LoaiTuanTra`
- `DiemTuanTra`
- `LuotTuanTra`
- `GhiNhanTuanTra`

Reason: app-label/table migration is high-risk for existing data, mobile bookmarks, admin history, audit trails and previous regression patches. Phase 2 adds operations-owned schedule/task entities and links legacy execution records back to operations shift/task truth.

Legacy compatibility is preserved for one transition release:

- `inspection/application/patrol_use_cases.py` is a wrapper only.
- Existing `/inspection/mobile/...` routes remain compatibility redirect/wrapper paths.
- User-facing mobile dashboard/templates use `operations` routes as canonical.
- Legacy fallback can only be used when a current shift has no active operations schedule configured.

## Fallback lock

Legacy route fallback is locked when a current shift has any active `LichTuanTraVanHanh` matching its site/post/shift. This remains true even if all tasks are already:

- `COMPLETED_VALID`
- `COMPLETED_WITH_WARNINGS`
- `MISSED`
- `CANCELLED_WITH_REASON`

The mobile list shows those final states and does not open “Bắt đầu legacy”. This prevents creating patrol sessions outside the official operations schedule.

## Dashboard read boundary

Dashboard/compliance read paths do not materialize business records. `GuardPatrolComplianceUseCase` only reads existing `NhiemVuTuanTraCa` rows.

Task materialization is restricted to explicit command boundaries:

- `MaterializeGuardPatrolTasksUseCase`
- authenticated guard mobile list for the guard’s current shift only, idempotent and actor-bound
- future management command/Celery job if added later

## Multi-shift boundary

Guard patrol shift selection uses timezone-aware active windows instead of selecting the first assignment by date:

- supports multiple shifts in one day;
- supports night shifts crossing midnight by checking today and yesterday;
- prioritizes checked-in and not checked-out shift when overlap exists;
- blocks starting a task outside the current shift window.

## Completion validity

`LuotTuanTra.trang_thai = HOAN_THANH` is not used alone for compliance. The authoritative quality state is:

- `trang_thai_doi_soat = IN_PROGRESS`
- `COMPLETED_VALID`
- `COMPLETED_WITH_WARNINGS`
- `MISSED`
- `CANCELLED_WITH_REASON`

`NhiemVuTuanTraCa.trang_thai` mirrors task-level compliance for dashboards and reports.

## Phase 4 cleanup candidate

After Docker runtime tests and migration rehearsal pass, a later controlled release may rename/split legacy `inspection` persistence tables into true operations-owned tables. That cleanup must include backfill, rollback plan, audit verification and report migration.
