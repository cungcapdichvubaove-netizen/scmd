# SCMD Pro Runtime Readiness Blockers Patch V2 — 2026-06-14

## Base

- Base source supplied by user: `scmd_pro_clean_source.zip`
- Patch type: cumulative modified/new files only, safe overlay patch.
- Architecture contract: single-organization hardened layered monolith; no microservices; no true multi-tenant SaaS; no CDN runtime.

## Scope

### P0.1 / P0.2 — Docker PostGIS/Redis env contract

- Synchronized `.env.example`, `docker-compose.prod.yml`, and `config/settings.py` around required variables:
  - `SQL_DATABASE`
  - `SQL_USER`
  - `SQL_PASSWORD`
  - `DATABASE_URL`
  - `REDIS_URL`
  - `SCMD_ORGANIZATION_ID`
- `docker-compose.prod.yml` now injects the same DB/Redis contract into `web`, `migrate`, `collectstatic`, `celery`, and `celery_beat`.
- `SCMD_DOCKER_COMPOSE=production` marks compose prod/demo mode.
- In compose prod/demo mode, Django now fail-closes with `ImproperlyConfigured` if:
  - `DATABASE_URL` is missing/blank;
  - `DATABASE_URL` is SQLite;
  - `DATABASE_URL` points to `localhost`, `127.0.0.1`, or `::1`;
  - resolved database engine is not `django.contrib.gis.db.backends.postgis`;
  - `REDIS_URL` is missing/blank;
  - `REDIS_URL` points to localhost.

### P1.1 — Dashboard N+1 benchmark cannot be hidden by cache

- Updated `accounting/tests_performance_benchmark.py`:
  - cold API path clears cache before SQL query counting;
  - warm cache path is measured separately and not used as N+1 proof;
  - direct `GetOperationsDashboardUseCase.execute(...)` query-count test bypasses API cache entirely.
- `profile_ops_dashboard` now validates PostGIS runtime when `SCMD_DOCKER_COMPOSE=production` is set.

### P1.2 — Logo asset optimization while preserving icon DNA

- Removed base64 PNG payloads from all `static/img/brand/*.svg` files.
- Preserved the canonical SCMD shield as standalone PNG/WebP icon assets:
  - `logo-symbol.png`
  - `logo-symbol.webp`
  - `logo-symbol-white.png`
  - `logo-symbol-black.png`
  - `logo-symbol-blue.png`
- Replaced heavy SVGs with lightweight compatibility wrappers that contain only:
  - the approved shield icon reference; and
  - `SCMD` or `SCMD Pro` text.
- Removed marketing/tagline copy from brand SVG wrappers and regenerated `report-header-logo.png` to show only icon + `SCMD Pro`.
- Runtime UI keeps the hybrid pattern: login/home/sidebar/admin use a separate icon file plus product text rendered by local CSS/font where practical.
- Report/PDF templates continue to use optimized PNG report assets:
  - `report-header-logo.png`
  - `report-watermark-symbol.png`
- Runtime favicon links use existing ICO/PNG fallbacks; no runtime dependency on `favicon.svg`.
- Added brand asset contract tests for base64 scan, size budgets, tagline-free SVGs, and PNG metadata scan.

### P1.3 — Evidence image compression policy

- Chosen policy: **B — no automatic compression/overwrite for evidence originals**.
- `operations/signals.py` no longer schedules evidence image compression for incident or attendance photos.
- `operations/tasks.py` keeps Pillow compression as an explicit opt-in utility only.
- The opt-in utility now writes a sidecar display derivative and does **not** mutate the original `ImageField` file bytes or field path.
- Compression behavior for the derivative:
  - max long edge defaults to `1600` px, configurable via `SCMD_IMAGE_MAX_DIMENSION`;
  - quality defaults to `80`, configurable via `SCMD_IMAGE_COMPRESSION_QUALITY`;
  - `optimize=True`;
  - EXIF stripped from the derivative by re-saving without metadata.
- Added test proving the derivative is smaller/resized while the original evidence bytes remain unchanged.

## Modified files

```text
.env.example
docker-compose.prod.yml
DOCUMENTATION.md
FULL_SOURCE_FILELIST.txt
README.md
RELEASE_CHECKLIST.md
accounting/tests_performance_benchmark.py
config/jazzmin_conf.py
config/settings.py
operations/signals.py
operations/tasks.py
templates/base.html
templates/base_public.html
templates/partials/_sidebar.html
users/templates/users/ly_lich_pdf.html
templates/admin/users/nhanvien/print_profile.html
templates/admin/users/nhanvien/print_profile_bulk.html
static/img/brand/favicon.svg
static/img/brand/loading-symbol.svg
static/img/brand/logo-scmd-horizontal-black.svg
static/img/brand/logo-scmd-horizontal-white.svg
static/img/brand/logo-scmd-horizontal.svg
static/img/brand/logo-scmd-pro-horizontal-black.svg
static/img/brand/logo-scmd-pro-horizontal-white.svg
static/img/brand/logo-scmd-pro-horizontal.svg
static/img/brand/logo-scmd-pro-stacked-white.svg
static/img/brand/logo-scmd-pro-stacked.svg
static/img/brand/logo-symbol-black.svg
static/img/brand/logo-symbol-blue.svg
static/img/brand/logo-symbol-white.svg
static/img/brand/logo-symbol.svg
static/img/brand/README-SVG-FILES.txt
static/img/brand/report-header-logo.svg
static/img/brand/report-watermark-symbol.svg
reports/templates/reports/print/incident_pdf.html
operations/management/commands/profile_ops_dashboard.py
main/templates/main/homepage.html
main/templates/main/login.html
accounting/templates/accounting/admin/bang_luong_trinh_ky.html
```

## Added files

```text
static/img/brand/logo-symbol.png
static/img/brand/logo-symbol.webp
static/img/brand/logo-symbol-white.png
static/img/brand/logo-symbol-black.png
static/img/brand/logo-symbol-blue.png
static/img/brand/report-watermark-symbol.png
static/img/brand/report-header-logo.png
operations/tests/test_image_compression_task.py
main/tests/test_brand_asset_contract.py
core/tests/test_docker_env_contract.py
```

## Migrations

- No model/schema migration added.

## Local verification run in this environment

```text
python -m py_compile config/settings.py config/jazzmin_conf.py operations/tasks.py operations/signals.py operations/management/commands/profile_ops_dashboard.py accounting/tests_performance_benchmark.py core/tests/test_docker_env_contract.py main/tests/test_brand_asset_contract.py operations/tests/test_image_compression_task.py
PASS

python YAML parse + required docker-compose app env keys check
PASS

grep -RIl "data:image/png;base64" static/img/brand/*.svg
PASS — no offenders

brand SVG size budget check
PASS

brand tagline scan for static/img/brand/*.svg
PASS — no offenders

PNG metadata/string scan for report assets
PASS — no offenders

manual PNG inspection: static/img/brand/report-header-logo.png
PASS — icon + SCMD Pro only

python scripts/release_contract_check.py --root . --audit-zip
PASS
```

## Docker/PostGIS/Redis verification status

Not claimed in this patch. The current patch creation environment does not provide Docker (`docker: command not found`), so the required real Docker/PostGIS/Redis verification must be run by the receiver.

Required commands after applying patch:

```powershell
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml build web
docker compose -f docker-compose.prod.yml down --remove-orphans
docker compose -f docker-compose.prod.yml up -d db redis
docker compose -f docker-compose.prod.yml ps

docker compose -f docker-compose.prod.yml run --rm web python manage.py shell -c "from django.db import connection; print(connection.vendor); print(connection.settings_dict['ENGINE'])"

docker compose -f docker-compose.prod.yml run --rm migrate

docker compose -f docker-compose.prod.yml up -d web celery celery_beat

docker compose -f docker-compose.prod.yml exec web python manage.py check
docker compose -f docker-compose.prod.yml exec web python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.prod.yml exec web python manage.py test operations.tests.test_operations_dashboard_hotfix_contract
docker compose -f docker-compose.prod.yml exec web python manage.py test operations.test_dashboard_use_cases
docker compose -f docker-compose.prod.yml exec web python manage.py test accounting.tests_performance_benchmark
docker compose -f docker-compose.prod.yml exec web python manage.py test core.tests.test_docker_env_contract main.tests.test_brand_asset_contract operations.tests.test_image_compression_task
docker compose -f docker-compose.prod.yml exec web python manage.py profile_ops_dashboard --username admin --date 2026-06-14 --max-queries 50 --max-ms 800
```

Expected DB engine check:

```text
postgresql
django.contrib.gis.db.backends.postgis
```

## Backward compatibility / risk notes

- Local development remains allowed to use SQLite only when not running compose prod/demo mode.
- Docker prod/demo mode is stricter: missing/localhost/SQLite DB or Redis config will now fail early instead of falling back.
- Existing template references to legacy SVG logo paths keep working because the SVG paths are preserved as lightweight wrappers.
- Report/PDF now use PNG assets for deterministic rendering; no business logic or permission logic changed.
- Evidence originals are no longer overwritten by automatic tasks or signals. The compression helper is opt-in and creates a sidecar display derivative, leaving the original bytes and field path unchanged.

## Not claimed

- Runtime PASS is not claimed.
- Demo-ready is not claimed.
- Performance-ready is not claimed.
- Docker/PostGIS/Redis verification is not claimed until the full command list above passes in a real Docker environment.
