<<<<<<< HEAD
## [Unreleased] - 2026-06-12

### Documentation
- Added the consolidated `docs/BUSINESS_WORKFLOW_A_TO_F_SYSTEM_CONTRACT.md` to capture Phase A→F business workflow source-of-truth decisions.
- Updated `README.md`, `DOCUMENTATION.md`, and `WHITEPAPER.md` so HĐLĐ, nghỉ phép, đổi ca, payroll reconciliation, thanh toán khách hàng/công nợ, and thu hồi tài sản/offboarding inventory are reflected in the authoritative system documentation.
- Extended business-domain decision records with Phase F asset recovery ownership and inventory/payroll/offboarding boundaries.
- Documented Phase F v2 void hardening: posted asset recovery cannot be voided while active damage/loss reports or effective payroll-deduction records remain.

## [3.5.5] - 2026-06-07

### Regression hardening
- Aligned Alive Check tests with the single-organization scope contract by reusing signal-created `NhanVien` profiles and creating `MucTieu` through `HopDong` instead of bypassing the contract graph.
- Hardened inventory posted/voided document handling so stale in-memory `PhieuNhap`/`PhieuXuat` objects cannot bypass hard-delete guards or block valid void flows after application use cases update database state.
- Corrected backup/restore tests and response headers without mutating `SCMD_ORGANIZATION_ID`, preserving the organization guard SSOT during test execution.
- Updated operations dashboard view fixtures to use an explicit operations group instead of widening dashboard permissions for ordinary users.
- Isolated employee-code and permission-signal tests so automatic profile creation no longer shifts expected employee-code sequence or creates duplicate profiles.

## [3.5.4] - 2026-06-07

### Security / architecture
- Reconfirmed that `static/`, `staticfiles/`, and Django `templates/` contain no Python source files and strengthened release checks to fail fast if misplaced `.py` files return.
- Reconfirmed that active `*/application/*.py` modules contain no wildcard imports, including `from .models import *`, and added explicit regression coverage for model imports.
- Reconfirmed `core.managers.TenantAwareManager` as the only organization-scope manager SSOT; `clients`, `operations`, and `accounting` remain consumers only.
- Extended `scripts/release_contract_check.py` so these three contracts are enforced before `manage.py check/test` in release verification.

## 3.5.3 - 2026-06-07 - Dashboard/admin language hardening

- Removed legacy cyber/war-room naming from owned JS/CSS asset surfaces and normalized old admin theme comments/tokens to SCMD navy/blue language.
- Applied the SCMD Pro capitalization guideline to dashboard templates by removing broad uppercase transforms from dashboard UI text and normalizing visible dashboard titles.
- Localized `/admin/` Technical Console copy according to `ADMIN_LOCALIZATION_AUDIT.md`, keeping technical identifiers/status codes such as `SUCCESS`, `Worker`, `Celery`, `task_id`, Django and Jazzmin unchanged where they are runtime terms.
- Added regression coverage for asset naming, dashboard capitalization and admin localization contracts.

# CHANGELOG.md - SCMD Pro

Semantic Versioning: <https://semver.org/>

## [3.5.2] - 2026-06-07

### Architecture
- Reconfirmed `core.managers.TenantAwareManager` as the single SSOT for organization-scoped managers and added regression checks to prevent duplicate manager definitions from returning in domain apps.
- Added regression coverage that fails if any `*/application/*.py` file reintroduces wildcard imports.

### Access control
- Extended `main.dashboard_router.DashboardRouter` from post-login routing into the centralized dashboard access policy.
- Added `dashboard_access_required()` and applied it to executive, operations, accounting, CRM, inventory, inspection, HR, reports, schedule, presentation, and mobile dashboard entrypoints.

### Tests
- Added architecture contract tests for manager SSOT and application-layer import hygiene.
- Added DashboardRouter access tests for matching workspaces, canonical route aliases, unmapped users, and superuser access.

## [3.5.1] - 2026-06-07

### Security
- Confirmed the owned `static/`, `staticfiles/`, and `templates/` surfaces contain no Python source files.
- Hardened production startup so `SECRET_KEY`, export password, and field encryption key fail fast when missing or when set to known development/default placeholders.
- Hardened bootstrap credentials so production refuses default admin username/email and placeholder admin/seed passwords.

### UI runtime
- Confirmed owned production templates/assets no longer reference `cdn.tailwindcss.com`; public/auth shells use the local Tailwind pipeline.

### Tests
- Added regression coverage for static/template Python exposure, Tailwind CDN reintroduction, and production credential placeholder guards.

## Legacy wording note

Các mục lịch sử trước chuẩn thương hiệu 3.5.0 có thể còn nhắc `SCMD ERP`, `command-center`, hoặc wording cũ khác trong bối cảnh release trước đây. Các dòng này được giữ nguyên để bảo toàn lịch sử thay đổi, không phải current contract. Source of truth hiện hành cho product naming, architecture, scope và UI governance là `README.md`, `WHITEPAPER.md`, `DOCUMENTATION.md`, `UI_SYSTEM_REFACTOR_SPEC.md`, và `cursorrules.md`. Mọi surface user-facing hiện tại phải dùng `SCMD Pro`.

=======
# CHANGELOG.md - SCMD Erp

Semantic Versioning: <https://semver.org/>

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
## [3.3.3] - 2026-06-03

### UI
- Rebuilt `main/templates/main/homepage.html` as a SCMD ERP public landing surface in Vietnamese with the navy/blue brand system and without any cyber or war-room language.
<<<<<<< HEAD
- Rebuilt `main/templates/main/login.html` against the local Tailwind pipeline using `{% tailwind_css %}` and `brand_system.css`, removing the runtime `Tailwind CDN` dependency from the login surface.
=======
- Rebuilt `main/templates/main/login.html` against the local Tailwind pipeline using `{% tailwind_css %}` and `brand_system.css`, removing the runtime `cdn.tailwindcss.com` dependency from the login surface.
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

### Tests
- Added focused application-layer attendance coverage for `CheckInUseCase`, `CheckOutUseCase`, and `CalculateWorkHoursUseCase`, including duplicate check-in, missing check-in, async checkout processing, and negative-duration guard cases.
- Added focused payroll audit coverage for `AuditPayrollUseCase`, including the no-previous-period path and anomaly detection for >20% take-home variance.

### Documentation
- Updated architecture/reference specs to record the `3.3.3` public-surface cleanup and use-case coverage milestone.

## [3.3.2] - 2026-06-03

### Architecture
- Consolidated organization-scope query enforcement into one shared `core.managers.TenantAwareManager` SSOT and removed duplicate manager definitions from `clients`, `operations`, and `accounting` model modules.
- Replaced wildcard-only application facades in `operations/application`, `accounting/application`, and `users/application` with real application-layer implementations.
- Converted the old root `*_use_cases.py` modules into explicit compatibility wrappers so legacy imports no longer rely on wildcard exports.

### Quality
- Rewired moved application modules to valid package imports after the facade removal, including direct imports from `core.domain.geo` and canonical `operations.models`.
- Cleaned a focused set of runtime/admin/application files with mojibake-prone strings so operator-facing and developer-facing text is more stable under the SCMD ERP UTF-8 contract.

### Documentation
- Updated architecture/reference documents to record the `3.3.2` cleanup milestone for manager SSOT, application-layer implementation, and runtime encoding cleanup.

## [3.3.1] - 2026-06-03

### Security
- Removed the misplaced Python source file `static/js/attendance_use_cases.py` from the WhiteNoise-served static tree so application-layer code is no longer publishable as a static asset.
- Removed the misplaced Python source file `users/templates/users/employee_use_cases.py` from the template tree so application code no longer resides in a template-loader path.
- Removed the stale collected artifact `staticfiles/js/attendance_use_cases.py` to eliminate residual public exposure after the source cleanup.

### Quality
- Hardened `scripts/verify.ps1` to fail fast if any `.py` file is placed under a `static/` or `templates/` path, preventing this class of exposure from re-entering the repository.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the public-asset boundary and WhiteNoise exposure rule.

## [3.1.46] - 2026-06-02

### Deployment
- Removed production auto-migration behavior from `scripts/entrypoint.sh`; the script now only waits for the database and then executes the provided process command.
- Updated `docker-compose.prod.yml` so the long-running `web` service starts Daphne directly instead of booting through a migration-running shell script.
- Added a dedicated one-shot `migrate` service to the production compose file so schema changes can be executed explicitly before starting web, worker, and beat replicas.
- Removed the obsolete top-level `version` key from `docker-compose.prod.yml` to align compose hygiene with the documented architecture contract.

### Documentation
- Updated `README.md`, `WHITEPAPER.md`, and `DOCUMENTATION.md` to formalize the production deployment sequence: build image, start infra, run migration job once, then start app replicas.

## [3.1.45] - 2026-06-02

### Security
- Removed the unsafe `BaoCaoSuCo.ma_su_co` placeholder default of `PENDING` that could trigger a duplicate-key failure on the second direct incident insert.
- Moved incident code generation back into `operations.models.BaoCaoSuCo.save()` so every creation path now enforces a unique `SC-YYYYMMDD-XXXXXX` code, including direct `objects.create()`, `form.save()`, serializer saves, SOS, seed, and simulation flows.
- Added a bounded retry on rare `ma_su_co` collisions so the model-level invariant remains resilient under concurrent inserts.

### Tests
- Added regression coverage to verify direct incident creates always generate distinct codes and that legacy `PENDING` placeholders are replaced before persistence.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the incident identity SSOT contract.

## [3.1.44] - 2026-06-02

### Payroll
- Rebuilt `accounting.application.payroll_use_cases.CalculatePayrollUseCase` against the current `ChiTietLuong` schema and removed writes to legacy/nonexistent fields.
- Switched payroll pricing to `MucTieu.get_don_gia_gio_thuc_te(thang, nam)` instead of direct `don_gia_gio` access.
- Added current-period mapping for allowances, advances, disciplinary fines, inventory deductions, and incident compensation into the active payroll snapshot fields.
- Standardized `AuditPayrollUseCase` under the `accounting.application` namespace and updated monthly payroll orchestration to use that SSOT.
- Hardened `PayrollService.tinh_luong_thang()` so anomaly-audit failure surfaces a warning instead of crashing the core payroll calculation flow.
- Added `ChiTietLuong.tong_phu_cap` as a compatibility alias for legacy templates and reports that still expect that surface.

### Tests
- Added focused payroll hotfix regression coverage in `accounting.tests_payroll_hotfix` for field mapping, deduction aggregation, and audit degradation behavior.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the payroll calculation SSOT contract.

## [3.1.43] - 2026-06-02

### Security
- Added `ShiftAccessPolicy` as the SSOT for resolving attendance shift access by tenant and authenticated employee.
- Hardened mobile attendance APIs so `checkin` and `checkout` now reject attempts to operate on another employee's shift with `403 SHIFT_ACCESS_DENIED`.
- Aligned HTML mobile attendance views with the same policy so web and API entrypoints no longer enforce different ownership rules.

### Tests
- Added regression coverage for unauthorized cross-employee attendance attempts in both API and HTML entrypoints.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the unified attendance access policy contract.

## [3.1.42] - 2026-06-02

### Admin UI
- Moved the signed-in account block to the bottom of the `/admin/` sidebar so it behaves as a footer utility area instead of an in-flow navigation card.
- Added a dedicated sidebar footer container and reworked the account card/menu spacing to suit a professional admin-shell footer pattern.
- Replaced the pseudo-element role treatment with a real role chip injected by JS so the account block can be styled and localized more cleanly.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the footer-account pattern for the admin sidebar.

## [3.1.41] - 2026-06-02

### Admin UI
- Refined the `/admin/` sidebar identity area with a stronger brand hierarchy, subtler glass surface, and a clearer operator-card treatment.
- Reframed the user card with a circular avatar treatment, pill-style role label, and a compact chevron control surface.
- Added a small console-context subtitle under the SCMD ERP brand block and cleaned the displayed role label to proper Vietnamese.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the admin sidebar identity-card refinement contract.

## [3.1.40] - 2026-06-02

### Admin UI
- Localized residual Jazzmin/Django admin chrome labels such as account-menu actions, search placeholders, dashboard labels, and footer wording into Vietnamese.
- Added a presentation-layer localization pass in the admin custom JS so the shell stays Vietnamese without forking the full Jazzmin base template.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the admin chrome localization hardening contract.

## [3.1.39] - 2026-06-02

### Admin UI
- Replaced residual English labels across the redesigned `/admin/` shell and system console with Vietnamese wording.
- Localized top-menu labels, system status text, KPI labels, runtime panel headings, quick-access labels, and action links.
- Replaced the sidebar enhancement script with a UTF-8 clean version so Vietnamese labels no longer degrade in the admin sidebar layer.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the Vietnamese-first wording contract for the admin console.

## [3.1.38] - 2026-06-02

### Admin UI
- Rebalanced the `/admin/` top-navbar flex layout so search shifts toward the account area instead of leaving a large dead gap on the right.
- Assigned the primary navbar list as the flexible region and kept the account controls visually adjacent to search.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the admin navbar flex-distribution contract.

## [3.1.37] - 2026-06-02

### Admin UI
- Fixed the custom `/admin/` index layout to occupy the full available content width inside Jazzmin's Bootstrap row wrapper.
- Removed the unintended empty right-side whitespace by wrapping the console root in an explicit `col-12` grid column.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the full-width grid contract for custom admin index templates.

## [3.1.36] - 2026-06-02

### Admin UI
- Made admin top-navbar labels responsive with `clamp()`-based typography and adaptive horizontal padding.
- Enforced single-line navigation labels with nowrap and ellipsis so long items no longer wrap into two lines at common desktop widths.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the admin navbar responsive-typography contract.

## [3.1.35] - 2026-06-02

### Admin UI
- Redesigned the `/admin/` system console index around a compact header instead of a large hero with duplicated shortcuts.
- Replaced the flat KPI strip with tiered technical cards for database, workers, Celery schedule, and access surface.
- Added first-fold runtime panels for `Task Results & Audit` and `Truy cập nhanh` so operators reach technical actions faster.
- Preserved the grouped admin taxonomy below the fold while improving the scan order of the top section.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the compact system-console layout contract.

## [3.1.34] - 2026-06-02

### Admin UI
- Added lightweight runtime badges to the admin sidebar for enabled schedules and task-result alerts.
- Upgraded the sidebar user panel into a quick-action surface with profile, password change, and logout links.
- Kept the new sidebar signals read-only and shell-scoped so they improve operator speed without changing business behavior.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the admin sidebar runtime-signal contract.

## [3.1.33] - 2026-06-02

### Admin UI
- Cleaned admin sidebar labels by stripping numeric ordering prefixes and preserving full labels as hover titles.
- Added operator-readable sidebar section grouping for dashboard, operations, HR/finance, system, and administration areas.
- Softened the sidebar active state from a heavy full-blue fill to a restrained accent-left treatment with lower visual noise.
- Refined sidebar typography and icon contrast to match the proposed SCMD after-state more closely.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the admin sidebar information-architecture cleanup.

## [3.1.32] - 2026-06-02

### Admin UI
- Refined the `/admin/` sidebar shell so the logo area now uses the SCMD ERP navy surface instead of a bright disconnected header block.
- Increased logo legibility by removing the forced circular logo treatment and sizing the mark for a cleaner technical-console presence.
- Reworked the sidebar user panel spacing, avatar framing, and operator label hierarchy so the signed-in admin block feels intentional and easier to scan.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the admin sidebar shell contract.

## [3.1.31] - 2026-06-02

### Admin Console
- Repositioned `/admin/` as a technical administration console with a custom index view focused on database status, worker heartbeat, Celery scheduling, audit activity, and privileged access counts.
- Grouped admin applications by technical stewardship domains instead of relying only on raw business app presentation.
- Added critical-model warning badges for permission-sensitive, payroll-sensitive, GPS-sensitive, and config-sensitive entities on the admin index.
- Registered `WorkerHeartbeat` in admin and exposed it as a first-class technical monitoring surface.
- Reworked Jazzmin top navigation and branding so `/admin/` no longer reads like a business dashboard.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the `/admin/` technical-console contract.

## [3.1.30] - 2026-06-02

### Architecture
- Added `main.dashboard_router.DashboardRouter` as the SSOT for post-login dashboard routing.
- Moved `central_hub()` off ad-hoc inline `Group` checks and onto the shared router service.
- Stopped treating `is_staff` alone as an executive dashboard signal; only `is_superuser` now hard-routes to `admin:index`.
- Normalized dashboard route mapping against actual runtime route names, including `clients:dashboard_crm`.

### Quality
- Added targeted tests for superuser, executive, inventory, and fallback dashboard routing behavior.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the dashboard-routing SSOT contract.

## [3.1.29] - 2026-06-02

### Operations
- Added `config/bootstrap_credentials.py` as the SSOT for bootstrap usernames, emails, and passwords.
- Unified `create_superuser_auto.py`, `seed_data`, `create_scmd_structure`, `Deploy-Desktop`, and `Reset-Desktop` around the same canonical bootstrap credential contract.
- Removed the competing post-reset credential banner for seeded demo users so both deploy and reset now point operators to one consistent login set.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the unified bootstrap credential contract.

## [3.1.28] - 2026-06-02

### Operations
- Added admin-account synchronization to `Reset-Desktop.ps1` and `reset-desktop.sh` so factory reset now recreates the canonical administrative login before handing the stack back to operators.
- Added explicit post-reset credential output for both the admin account and the seeded executive demo account.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the guaranteed post-reset credential contract.

## [3.1.27] - 2026-06-02

### Operations
- Hardened `Reset-Desktop.ps1` and `Deploy-Desktop.ps1` to use explicit UTF-8 console, temporary stream decoding, and log-file writes so Docker and Django command output no longer degrades into mojibake on Windows PowerShell.
- Replaced implicit `Get-Content` and log-write encoding behavior with explicit UTF-8 handling across the desktop operator scripts.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the UTF-8 console and log-stream contract for desktop operations.

## [3.1.26] - 2026-06-02

### Operations
- Hardened `Reset-Desktop.ps1` health checks so PowerShell no longer crashes on HTTP probe exceptions that do not expose a `.Response` property.
- Switched reset-time `migrate`, `check`, and `seed_data` invocations onto the captured Docker process wrapper for more consistent exit handling and operator output.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the reset health-check and one-off command execution contract.

## [3.1.25] - 2026-06-02

### Operations
- Replaced the mojibake-ridden `seed_data` management command with a UTF-8 clean version so reset-time logs and seeded operational labels render correctly in Vietnamese.
- Replaced the mojibake-ridden `create_scmd_structure` management command with a UTF-8 clean version so internal bootstrap structures and operator messages no longer degrade into double-encoded text.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the UTF-8 requirement for deploy/reset management command surfaces and seeded reference labels.

## [3.1.24] - 2026-06-02

### Product Surface
- Restored the last remaining ASCII fallback label in the authenticated application shell from `Truc tuyen` to `Trực tuyến`.
- Locked the user-facing Vietnamese copy contract so shell, dashboard, login, admin navigation, and print surfaces stay in proper UTF-8 with full diacritics.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the UTF-8 Vietnamese interface rule for product-facing templates and admin labels.

## [3.1.23] - 2026-06-02

### Operations
- Promoted `Faker==37.6.0` from development-only usage to the runtime dependency set because `seed_data` is callable from the desktop reset workflow inside app containers.
- Closed the gap where reset could succeed through migrate/check but fail on the optional sample-data step due to a missing runtime package.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the seed-data runtime dependency rule.

## [3.1.22] - 2026-06-02

### Operations
- Removed automatic `manage.py migrate` execution from `docker-entrypoint.sh`.
- Reworked desktop deploy/reset flows to run `migrate`, `check`, admin sync, and optional seed steps through one-off Django containers before starting `web`, `celery_worker`, and `celery_beat`.
- Eliminated the migration race condition that caused duplicate-schema failures on clean database resets.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the single-runner migration contract for desktop operations.

## [3.1.21] - 2026-06-02

### Operations
- Removed the `node:20-slim` Tailwind build stage from `Dockerfile` and made the runtime image consume the committed stylesheet at `theme/static/css/dist/styles.css`.
- Added an explicit Docker build assertion for the committed Tailwind artifact so desktop builds fail fast with a clear message if the CSS bundle is missing.
- Hardened `Deploy-Desktop.ps1` and `deploy-desktop.sh` to validate the Tailwind artifact before running compose build or restart flows.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the offline-friendly Docker asset contract for desktop deploys.

## [3.1.20] - 2026-06-02

### Product Surface
- Added `UI_SYSTEM_REFACTOR_SPEC.md` to map the SCMD ERP UI/system redesign to the real Django repository structure instead of a non-existent React frontend tree.
<<<<<<< HEAD
- Reframed the login surface toward an operations workspace and removed the strongest legacy cyber-console branding from the user-facing auth copy.
- Cleaned the personnel print template branding to use SCMD Pro language instead of legacy enterprise-security naming.
=======
- Reframed the login surface toward an ERP operations workspace and removed the strongest `Security Command System` style branding from the user-facing auth copy.
- Cleaned the personnel print template branding to use `SCMD ERP` language instead of legacy enterprise-security naming.
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
- Declared the frontend asset pipeline package as `scmd-erp-ui-build` and aligned Tailwind color extension names with the SCMD ERP brand/state palette.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the Django-surface mapping rule for future UI and brand refactors.

## [3.1.19] - 2026-06-02

### Runtime
- Restored `phonenumbers>=8.13.0` to `requirements.txt` so migration import paths for `django-phonenumber-field` can bootstrap correctly.
- Tightened deploy validation logic around migration-time imports, not only app-registry and URL-resolution imports.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the adapter-companion dependency rule for runtime and migration bootstrap.

## [3.1.18] - 2026-06-02

### Runtime
- Restored `qrcode==8.2` and `reportlab==4.4.2` to `requirements.txt` so the inspection module can satisfy its direct runtime imports during Django bootstrap and PDF export flows.
- Extended the deploy dependency contract beyond `INSTALLED_APPS` entries to also cover direct third-party imports executed from active URL and view modules.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the direct-runtime-import dependency rule for deploy artifacts.

## [3.1.17] - 2026-06-02

### Runtime
- Restored `django-cors-headers==4.9.0`, `cloudinary>=1.36.0`, and `django-cloudinary-storage>=0.3.0` to `requirements.txt` so the Django app registry can satisfy the current `INSTALLED_APPS` closure.
- Extended the deploy repair beyond the first failing import to cover the full missing runtime package set required by bootstrap.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the installed-apps dependency-closure rule for deploy artifacts.

## [3.1.16] - 2026-06-02

### Runtime
- Restored `django-celery-beat==2.8.1` and `django-celery-results==2.6.0` to `requirements.txt` so rebuilt desktop deploy images satisfy the Django app registry contract in `config.settings`.
- Fixed the deploy failure mode where `manage.py migrate` crashed before running because `config.apps_overrides` imported missing Celery Django integration packages.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the rule that every app referenced by `INSTALLED_APPS` must be backed by an explicit runtime dependency.

## [3.1.15] - 2026-06-02

### Design System
- Introduced `static/common/css/brand_system.css` as the shared SCMD ERP color token source for shell, public screens, dashboard, and admin.
- Reworked internal shell, sidebar, public entry layout, and executive dashboard to remove module-colored accents and standardize on navy/blue brand colors plus explicit state colors only.
- Updated admin styling to import the shared brand token contract so the Jazzmin workspace follows the same palette and contrast system.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the canonical SCMD ERP brand color and state-color rules.

## [3.1.14] - 2026-06-02

### Admin UI
- Reworked the Jazzmin admin shell into a calmer SCMD ERP workspace with a white utility navbar, structured navy sidebar, softer surfaces, clearer spacing, stronger typography hierarchy, and more consistent buttons, forms, tables, filters, and cards.
- Simplified the top navigation and reduced search clutter by limiting the admin search contract to `users.NhanVien` plus core operator routes.
- Corrected Jazzmin branding strings and static asset paths so the admin uses `common/css/custom_admin.css` and `js/scmd_jazzmin_scroll.js` without broken aliases.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the SCMD ERP admin workspace rules and navigation constraints.

## [3.1.13] - 2026-06-02

### Frontend
<<<<<<< HEAD
- Updated `templates/base.html` to load the project Tailwind build through `{% tailwind_css %}` instead of `Tailwind CDN`.
=======
- Updated `templates/base.html` to load the project Tailwind build through `{% tailwind_css %}` instead of `cdn.tailwindcss.com`.
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
- Added `defer` to the Alpine CDN script so shell initialization runs after the document body is available.
- Aligned `static/manifest.json` branding with SCMD ERP and restored missing manifest icons at `static/img/logo_192.png` and `static/img/logo_512.png`.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the authenticated-shell asset and manifest rules.

## [3.1.12] - 2026-06-02

### Developer Experience
- Updated `.vscode/settings.json` so VS Code and Pylance resolve Python imports against the workspace virtual environment instead of a system interpreter.
- Corrected the local workspace `venv` back to `Django 5.2.5` to match the runtime dependency contract in `requirements.txt`.
- Verified local imports for `dj_database_url`, `sentry_sdk`, and `decouple` from the workspace `venv`.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the workspace-interpreter and local dependency-alignment rule.

## [3.1.11] - 2026-06-02

### Operations
- Hardened `Deploy-Desktop.ps1` and `deploy-desktop.sh` so rebuild mode can fall back to local-image restart mode when Docker Hub metadata is unreachable but valid local SCMDERP images already exist.
- Preserved post-start correctness checks in fallback mode: `up`, migrations, admin sync, `manage.py check`, and HTTP health validation still run.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to record the offline-build fallback rule for desktop deploy flows.

## [3.1.10] - 2026-06-02

### Operations
- Removed the obsolete top-level `version` key from `docker-compose.yml` so `docker compose` no longer emits warning noise during validation and runtime checks.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to record the compose-hygiene rule as part of the canonical local runtime contract.

## [3.1.8] - 2026-06-02

### Documentation
- Rewrote `README.md` to remove mojibake/encoding drift and align the project description with the actual SCMD ERP product position.
- Updated README content to reflect the layered monolith architecture, canonical bootstrap path, canonical local admin contract, Docker runtime flow, and executive dashboard principles.
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to record the README alignment rule as a documentation patch release.

## [3.1.6] - 2026-06-02

### Dashboard
- Repositioned `/dashboard/` from a command-center styled landing page into an internal SCMD ERP operations cockpit focused on staffing, shifts, attendance, incidents, warehouse alerts, and payroll review impact.
- Replaced shortcut-style module cards with operational KPI cards, work queues, target status summaries, and finance states that distinguish between real zero values and insufficient data.
- Standardized the dashboard and sidebar color system around navy/blue branding plus business-state colors only: green, blue, yellow, red, and gray.

### Runtime
- Expanded `dashboard.views.dashboard_main` to expose actionable operational aggregates such as active sites, unchecked shifts, late attendance, abnormal attendance, payroll review counts, quick alerts, and per-site dashboard status.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to formalize the dashboard positioning and the canonical status-color rules for SCMD ERP.

## [3.1.5] - 2026-06-02

### Runtime
- Restored the `users` URL contract for desktop HR dashboard, employee profile, mobile profile flows, salary detail, and PDF export endpoints so shared navigation no longer raises `NoReverseMatch`.
- Re-registered the HR alert history DRF endpoint under the `users` namespace with the expected `hralerthistory-list` route name to realign runtime behavior with existing tests and API consumers.

### Documentation
- Updated `WHITEPAPER.md` to record the canonical `users` navigation contract as a patch-level runtime stabilization.

## [3.1.4] - 2026-06-02

### Authentication
- Standardized the canonical local administrator account as `admin` / `ScmdAdmin2026!` with `admin@scmd.local`.
- Reworked `create_superuser_auto.py` to synchronize the canonical admin account idempotently instead of relying on the legacy `admin123` default.
- Updated desktop deploy flows to run admin synchronization after migrations so a fresh local database is always reachable without guessing credentials.
- Aligned demo superuser generation in `main/management/commands/create_scmd_structure.py` to the same canonical admin identity instead of creating `admin_scmd`.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to record the canonical local admin contract and distinguish it from demo employee passwords.

## [3.1.3] - 2026-06-02

### Runtime
- Added native WeasyPrint runtime libraries to `Dockerfile`, normalized `requirements.txt` for deterministic container builds, and removed the obsolete `version` key from `docker-compose.yml`.
- Repaired mobile and operations runtime drift by restoring missing API entry points, fixing broken imports, and making `main.context_processors` compatible with the current `main` model set.
- Removed DRF decimal validator warnings in `operations.api_serializers` by using `Decimal` bounds for latitude and longitude validation.

### Database
- Added merge migrations to restore a single forward migration graph for `accounting`, `clients`, `operations`, and `users`.
- Generated and applied new schema migrations for `main`, `users`, `accounting`, `clients`, and `operations` so model state now matches executable runtime state.
- Hardened tenant population migrations in `accounting` and `clients` so they accept both `UUID` and string forms of `SCMD_ORGANIZATION_ID`.

### Operations
- Validated `Deploy-Desktop.ps1` end-to-end after rebuild and restart flows, including `migrate`, `check`, and HTTP readiness on SCMDERP endpoints.
- Hardened `Check-Health.ps1` to evaluate Docker/Python checks by real process exit codes instead of PowerShell stream noise, and aligned probes to `/login/`, `/admin/login/`, and `/api/docs/`.

## [3.1.2] - 2026-06-02

### Operations
- Replaced legacy desktop health logic with SCMDERP runtime checks against `D:\SCMDERP\docker-compose.yml`, `pg_isready`, `redis-cli ping`, `python manage.py check`, and HTTP reachability on port `8000`.
- Rewrote `Deploy-Desktop.ps1` and `deploy-desktop.sh` to deploy only the layered-monolith stack `web`, `celery_worker`, `celery_beat`, `db`, `redis`, with mandatory `python manage.py migrate --noinput` and `python manage.py check`.
- Consolidated `Deploy-Desktop.bat` and `Reset-Desktop.bat` into thin wrappers so Windows desktop flows no longer maintain a second operational contract.
- Replaced legacy cleanup behavior in `Cleanup-Desktop.bat` so cleanup now validates and tears down the active SCMDERP compose project rather than stale `docker-compose.desktop.yml` and hard-coded volume names.
- Rewrote `reset-desktop.sh` to mirror the canonical SCMDERP reset contract and removed references to legacy `app/pdf/prisma` desktop services.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to record the wrapper consolidation and the requirement that health checks validate the actual Django stack on port `8000`.

## [3.1.1] - 2026-06-02

### Operations
- Hardened `D:\scmdpro\Deploy-Desktop.ps1` so full deploy mode also runs `python manage.py migrate --noinput` before system check and health validation.
- Rewrote `D:\scmdpro\deploy-desktop.sh` to mirror the PowerShell deploy contract with explicit fast/full modes and the canonical SCMDERP service map.
- Replaced legacy cleanup behavior in `D:\scmdpro\Cleanup-Desktop.bat` so cleanup now targets the active SCMDERP compose project instead of stale `docker-compose.desktop.yml` and hard-coded `scmdpro_*` volumes.
- Added compose validation before destructive reset flows in `D:\scmdpro\Reset-Desktop.ps1` and `D:\scmdpro\reset-desktop.sh`.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to record the desktop operations hardening as a patch release under the same layered-monolith architecture.

## [3.1.0] - 2026-06-02

### Operations
- Standardized desktop helper scripts to operate against the SCMDERP Docker stack instead of the legacy `scmdpro` Node/Prisma desktop contract.
- Defined the approved desktop wrapper set as `Deploy-Desktop`, `Reset-Desktop`, and `Check-Health` in PowerShell and shell variants.
- Locked desktop operations to `D:\SCMDERP\docker-compose.yml`, `manage.py migrate`, `manage.py check`, and the canonical service set: `web`, `celery_worker`, `celery_beat`, `db`, `redis`.

### Documentation
- Updated `WHITEPAPER.md` and `DOCUMENTATION.md` to state that external desktop scripts are operational wrappers only, not architectural truth sources.
- Added the rule that operator-facing scripts must align with the same monolith runtime contract before any broader platform ambitions.

## [3.0.0] - 2026-06-01

### Architecture
- Standardized the project as a `layered monolith` with explicit module boundaries instead of continuing to claim strict clean architecture enforcement that the runtime code did not satisfy.
- Consolidated audit SSOT around `main.models.AuditLog` and `main.models.WorkerHeartbeat`.
- Consolidated Alive Check SSOT around `operations.models.KiemTraQuanSo`.

### API Contracts
- Froze broken legacy mobile endpoints with `410 GONE` and `LEGACY_API_FROZEN`.
- Standardized mobile attendance contracts on `operations.api_views.CheckInAPI` and `operations.api_views.CheckOutAPI`.

### Runtime Stabilization
- Added compatibility shims for legacy `.application.*` imports to stop import-time crashes while code is normalized.
- Added `core.infrastructure.security` to restore a single encryption helper path for PII fields.
- Added bootstrap and verification scripts: `scripts/bootstrap.ps1` and `scripts/verify.ps1`.

### Why
- Reduce runtime drift between architecture documents and executable code.
- Freeze unsafe API surfaces instead of preserving misleading compatibility.
- Establish one bootstrap path and one SSOT per critical subsystem before any true multi-tenant or service-splitting work.

## [2.1.x]

Previous 2.1.x hardening entries are superseded by the 3.0.0 architecture normalization release.
Historical detail remains available in git history.
<<<<<<< HEAD
## scmdpro_43_guard_patrol_domain_correction_patch_v4

- Hardening Guard Patrol v3 trước production.
- Khóa legacy fallback khi ca đã có lịch tuần tra vận hành active.
- Bổ sung ảnh checkpoint mobile: input image/capture, FormData field `hinh_anh_xac_thuc`, view/use case/test happy path.
- Dashboard compliance không materialize `NhiemVuTuanTraCa` hoặc audit khi GET/read.
- Thêm `MaterializeGuardPatrolTasksUseCase` làm command boundary.
- Chọn ca hiện tại theo timezone-aware window, hỗ trợ nhiều ca/ngày và ca đêm qua ngày.
- Bổ sung tests: photo policy, multi-shift, dashboard no-side-effect.

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
