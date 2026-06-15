# Rollback Notes

Patch: `scmdpro_production_demo_hardening_patch`  
Date: `2026-06-14`

## Scope

Patch này chỉ thay đổi:

- static/vendor runtime assets
- brand SVG/logo assets
- admin/public/runtime template assets
- service worker cache versioning
- production Docker/Nginx deploy config
- release hygiene scripts và tài liệu release

Không có:

- migration
- model schema change
- business logic payroll/attendance/inventory/inspection change
- permission model change

## Rollback strategy

Restore các file đã thay đổi về bản trước patch:

- `package.json`
- `package-lock.json`
- `config/settings.py`
- `main/pwa_views.py`
- `templates/sw.js`
- `templates/admin/base.html`
- `operations/templates/operations/mobile/tuan_tra.html`
- `inspection/templates/inspection/mobile/tuan_tra.html`
- `docker-entrypoint.sh`
- `docker-compose.prod.yml`
- `nginx/default.conf`
- `scripts/sync_vendor_assets.py`
- `scripts/clean_release_artifacts.py`
- `scripts/release_contract_check.py`
- `static/vendor/**`
- `static/img/brand/*.svg`

## Rollback commands

Sau khi restore source:

```bash
docker compose -f docker-compose.prod.yml config
python scripts/release_contract_check.py --audit-zip
```

Nếu rollback cả deploy state:

```bash
docker compose -f docker-compose.prod.yml run --rm collectstatic
docker compose -f docker-compose.prod.yml up -d web nginx celery celery_beat
```

## Operational impact of rollback

- Low for data integrity: không có thay đổi dữ liệu hay schema.
- Medium cho demo UX/performance: rollback có thể đưa trở lại:
  - vendor runtime placeholder
  - external font dependency
  - logo nặng
  - web startup chậm hơn nếu `collectstatic` lại chạy ngầm
  - cache/PWA behavior kém deterministic hơn

## Post-rollback validation

- `/login/` render bình thường
- `/dashboard/` render không lỗi JS/CSS
- `/admin/` render bình thường
- `/static/` phục vụ được asset chính
- mobile QR page vẫn mở được nếu giữ nguyên vendor runtime trước đó

## Data rollback

Không cần rollback dữ liệu.
