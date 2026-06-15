# Legacy Application Shims

Status: temporary compatibility wrappers during the `*/application/*` import migration.

Removal policy:
- Keep for exactly one release window after all internal imports have moved to `*/application/*`.
- Target removal: next release after the Phase 1 architecture hardening rollout.
- Do not add new imports to these files.

Active shims:
- `attendance_use_cases.py`
- `dashboard_use_cases.py`
- `employee_use_cases.py`
- `operations/attendance_use_cases.py`
- `operations/dashboard_use_cases.py`
- `operations/alive_check_use_cases.py`

Sunset checklist before deletion:
- `rg -n "from (attendance_use_cases|dashboard_use_cases|employee_use_cases|operations\\.attendance_use_cases|operations\\.dashboard_use_cases|operations\\.alive_check_use_cases) import|import (attendance_use_cases|dashboard_use_cases|employee_use_cases)$" .`
- Confirm no Django view, API view, task, admin action, signal, or test imports a shim directly.
- Delete the shim files in one patch release and re-run system checks and targeted tests.
