# PATCH MANIFEST

## Patch

- Name: `scmdpro_production_demo_hardening_patch`
- Date: `2026-06-14`
- Product: `SCMD Pro`
- Scope: hardening bề mặt release/demo production cho static assets, vendor runtime, font/icon/logo, Docker/Nginx, PWA cache và performance instrumentation

## Mục tiêu patch

- Làm sạch release package để không mang artifact local/runtime lên server demo.
- Thay vendor JS/CSS placeholder bằng bản local official có pin version rõ ràng.
- Loại bỏ external font CDN trên admin/runtime path.
- Giảm trọng lượng brand SVG/logo để cải thiện first load và tránh layout shift.
- Tách `collectstatic` khỏi web container startup trong production-like flow.
- Tăng chất lượng cache header `/static/`, giữ `/media/` tiếp tục có auth gate.
- Version hóa service worker cache theo release để tránh stale assets sau deploy.
- Mở rộng performance instrumentation cho các bề mặt dashboard nghiệp vụ chính.

## Blocker đã xử lý

- `BLOCKER 1` Release package sạch:
  - mở rộng `scripts/clean_release_artifacts.py`
  - mở rộng `scripts/release_contract_check.py`
  - chặn `node_modules`, `staticfiles`, `media`, `__pycache__`, `.pyc`, `.log`, profile/tmp
- `BLOCKER 2` Vendor runtime local thật:
  - thêm `scripts/sync_vendor_assets.py`
  - sync vendor từ `node_modules` sang `static/vendor`
- `BLOCKER 3` External Google Fonts:
  - xóa font CDN khỏi `templates/admin/base.html`
- `BLOCKER 4` Brand assets quá nặng:
  - thay toàn bộ logo SVG base64/raster nặng bằng SVG vector nhẹ
- `BLOCKER 5` `collectstatic` chạy ngầm:
  - đổi default startup flag
  - thêm service `collectstatic` riêng trong `docker-compose.prod.yml`
- `BLOCKER 6` Nginx static cache:
  - thêm `try_files`, cache headers, `gzip_static`, `nosniff`, `no-store` cho HTML động
- `BLOCKER 7` Perf instrumentation:
  - mở rộng prefix đo hiệu năng cho accounting, inventory, users, clients, inspection, workflow
- `BLOCKER 8` PWA cache stale:
  - version hóa cache bằng `SCMD_PRO_CACHE_VERSION`
  - service worker render version từ settings/runtime

## File thay đổi

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
- `PATCH_MANIFEST.md`
- `PRODUCTION_DEMO_READINESS_REPORT.md`
- `RELEASE_CHECKLIST.md`
- `ROLLBACK_NOTES.md`

## Migration

- Không có migration mới.
- Không đổi model schema.
- Không đổi business logic payroll, attendance, incident, inventory, permission hay audit flow.

## Vendor versions

- `chart.js` `4.4.3`
- `jquery` `3.7.1`
- `select2` `4.1.0-rc.0`
- `alpinejs` `3.14.1`
- `html5-qrcode` `2.3.8`
- `@fortawesome/fontawesome-free` `6.5.2`
- `dexie` `4.0.8`
- `htmx.org` `1.9.12`
- `nprogress` `0.2.0`
- `bootstrap` `4.6.2`

## Static / font / icon / logo changes

- Admin không còn gọi `fonts.googleapis.com` hoặc `fonts.gstatic.com`.
- PWA core assets dùng font local `Be Vietnam Pro` và FontAwesome local.
- Xóa dependency audio scan placeholder; thay bằng Web Audio API + vibration cho QR patrol mobile.
- Đồng bộ CSS/webfonts FontAwesome local đầy đủ để tránh icon lỗi thành dấu chấm/ký tự rác.
- Thay logo SVG nặng bằng vector SVG nhỏ gọn, không còn embedded base64 PNG trong runtime brand assets.

## Docker / Nginx / deploy changes

- `docker-entrypoint.sh` mặc định không tự `collectstatic`.
- `docker-compose.prod.yml` có service `collectstatic` riêng.
- `web` service đặt `SCMD_COLLECTSTATIC_ON_START=0`.
- `/static/` được cache dài hạn và `immutable`.
- `/media/` tiếp tục private/auth-gated.
- `/` động trả `Cache-Control: no-store`.

## PWA cache changes

- `SCMD_PRO_CACHE_VERSION` đọc từ env hoặc `RELEASE_VERSION`.
- `/sw.js` trả về JS không cache cứng ở browser/proxy.
- Cache cũ được purge theo version mới sau activate.
- Không cache sai auth endpoints, dashboard POST/mutation hoặc `/media/`.

## Backward compatibility

- Không thêm dependency runtime mới ngoài vendor local đang phục vụ các template hiện có.
- Không thay route business.
- Không thay permission model.
- Không thay schema hoặc dữ liệu hiện hữu.
- Dev workflow vẫn có thể `collectstatic` thủ công; production-like flow deterministic hơn.

## Rollback note

- Rollback chỉ cần restore các file thay đổi nêu trên và build lại static/vendor.
- Không cần rollback dữ liệu vì patch không mutate schema hay bản ghi nghiệp vụ.

## Test summary

Đã chạy:

- `python scripts/sync_vendor_assets.py`
- `python scripts/clean_release_artifacts.py --dry-run`
- `docker compose -f docker-compose.prod.yml config`
- `Get-ChildItem static -Recurse -Filter *.py`
- `Get-ChildItem . -Recurse -Filter *.py | Where-Object { $_.FullName -match '\\templates\\' }`
- `rg -n "fonts.googleapis.com|fonts.gstatic.com|cdn.tailwindcss.com|War Room|Sentinel|Tactical|Security Command System|SCMD ERP|ENTERPRISE SECURITY PLATFORM|\\bESP\\b" templates static main users operations accounting clients inspection inventory dashboard mobile`

Cần/đã chạy lại trong audit sạch:

- `python scripts/release_contract_check.py --root <clean_copy> --audit-zip`

Không chạy được trong host hiện tại:

- `python manage.py check`
- `python manage.py showmigrations --plan`
- `python manage.py test ...`

Lý do: máy Windows hiện thiếu runtime GDAL/PROJ để khởi tạo GeoDjango từ `config/settings.py`.

## Known limitations

- Smoke test browser thực tế trên HTTPS/mobile camera chưa được chạy trong phiên này, nên QR camera/chart render mới được xác nhận ở mức static/runtime asset readiness.
- `docker compose build` và `collectstatic` trong container chưa chạy tại đây; mới xác nhận cấu hình bằng `docker compose ... config`.
- Benchmark request time/query count thực tế phụ thuộc dữ liệu demo server; patch này mới bảo đảm instrumentation và đường triển khai deterministic.
