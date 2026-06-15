# ACCESS_SCOPE_MIGRATION_BACKFILL_PLAN.md — SCMD Pro Access Scope Migration & Backfill Plan

Version: 1.0.0  
Status: Required before Phase 1 data migration  
Updated: 2026-06-08  
Scope: `NhanVienRegionAssignment`, access delegation, historical scope backfill

---

## 1. Purpose

This plan defines how SCMD Pro migrates from current operational data to explicit historical access-scope data without losing payroll, attendance, incident, patrol or inventory traceability.

Do not run any production scope migration or access-delegation migration until this plan is reviewed against staging data. The current implementation remains region-scoped through `Region` and `NhanVienRegionAssignment`.

---

## 2. Target model ownership

| Model | Location | Purpose |
|---|---|---|
| `NhanVienRegionAssignment` | `users/models_assignment.py` | Staff-to-region assignment history, multi-region assignment, historical scope |
| `AccessDelegation` | Planned `delegation/models.py` | Temporary scope delegation target; current release chưa có model/app này |
| `PayrollAdjustment` | `accounting/models.py` | Retroactive payroll adjustment after locked/paid period |

---

## 3. Current source candidates for backfill

The implementation team must inspect the current schema and confirm exact field names before migration.

Potential data sources:

```text
operations.PhanCongCaTruc        shift/date/site evidence
clients.MucTieu                  site model
operations.ViTriChot             post -> site relation
users.NhanVien                   staff status/current legacy fields if any
users.LichSuCongTac              employment/work history if linked to site
operations.ChamCong              attendance -> shift/staff evidence
inventory issue/return documents equipment location context
```

Priority source for historical site membership:

```text
PhanCongCaTruc.ngay_truc + vi_tri_chot.muc_tieu + nhan_vien
```

because it reflects actual operational work.

---

## 4. Backfill rules for NhanVienRegionAssignment

### 4.1 From shifts

For each `nhan_vien` and `muc_tieu`, group contiguous shift dates into assignment windows.

Default rule:

```text
starts_at = first shift date at that site
ends_at   = day before next assignment window if continuous assignment changes are inferable
status    = ACTIVE if no later transfer detected, otherwise ENDED
source    = BACKFILL_FROM_SHIFT
```

### 4.2 Missing history

If a staff member has no shift/site history:

```text
create no assignment automatically
flag as DATA_ANOMALY_NO_SITE_HISTORY
```

Do not guess region assignment from department or job title.

### 4.3 Multi-site staff

If a staff member has shifts at multiple sites in overlapping periods:

```text
create multiple assignment rows
assignment_type = MULTI_SITE or RELIEF
```

Do not collapse into one `current_region`.

### 4.4 Overnight shifts

Overnight shift belongs to the local date of `shift.start_at` / `ngay_truc` for assignment grouping.

### 4.5 Data anomalies

Produce a migration report for:

```text
staff with no site history
staff with overlapping shifts at different sites on the same time window
site/post missing relation
shift without staff
attendance without shift
assignment window longer than configured anomaly threshold
```

---

## 5. SQL verification after backfill

Examples; adapt table names to actual migrations.

```sql
-- Staff without assignment but with shifts
SELECT pc.nhan_vien_id, COUNT(*)
FROM operations_phancongcatruc pc
LEFT JOIN users_nhanvienregionassignment a
  ON a.nhan_vien_id = pc.nhan_vien_id
GROUP BY pc.nhan_vien_id
HAVING COUNT(a.id) = 0;

-- Assignment tenant distribution
SELECT tenant_id, COUNT(*) FROM users_nhanvienregionassignment GROUP BY tenant_id;

-- Overlap check per staff/site
SELECT nhan_vien_id, muc_tieu_id, COUNT(*)
FROM users_nhanvienregionassignment
GROUP BY nhan_vien_id, muc_tieu_id
HAVING COUNT(*) > 1;
```

---

## 6. Rollback and forward-fix

Rollback strategy:

- Schema rollback is allowed only before dependent policies are deployed.
- If production data has been used by new policies, prefer forward-fix.

Forward-fix strategy:

- Keep original operational tables unchanged.
- Mark suspicious backfill rows with `source = BACKFILL_REVIEW_REQUIRED`.
- Provide admin review list for assignment anomalies.

---

## 7. Post-migration smoke tests

```text
Site Commander A sees historical attendance for staff while assigned to Site A.
Site Commander A does not see staff's later Site B shifts.
Area Manager sees all sites in assigned region.
Guard assigned to two sites sees both valid shift contexts.
Payroll source attendance resolves assignment by shift work_date.
```
