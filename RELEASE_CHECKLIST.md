# RELEASE_CHECKLIST.md

Version: `2026-06-14`  
Scope: SCMD Pro production demo release hygiene and smoke checklist

## 1. Pre-flight

- Xác nhận dùng đúng source tree sạch, không đóng gói từ workspace có `media/`, `staticfiles/`, `node_modules/`, `__pycache__/`, `.pyc`, `.log`.
- Xác nhận `.env` production không nằm trong patch/source ZIP.
- Xác nhận server demo có HTTPS thật nếu cần QR/camera/PWA.
- Xác nhận host/container có đủ GDAL/PROJ nếu chạy GeoDjango.

## 2. Mandatory commands

Chạy trên source tree đầy đủ hoặc container production-like:

```bash
python manage.py check
python manage.py showmigrations --plan
python manage.py test main
python manage.py test dashboard
python manage.py test operations
python manage.py test accounting
python manage.py test inventory
python scripts/release_contract_check.py --audit-zip
python scripts/clean_release_artifacts.py --dry-run
docker compose -f docker-compose.prod.yml config
```

Nếu đóng gói audit từ bản copy sạch:

```bash
set PYTHONDONTWRITEBYTECODE=1
python scripts/release_contract_check.py --root <clean_copy_path> --audit-zip
```

## 3. Static and source hygiene

```bash
find static/ -name "*.py"
find . -path "*/templates/*" -name "*.py"
grep -R "cdn.tailwindcss.com" -n .
grep -R "fonts.googleapis.com\|fonts.gstatic.com" -n .
find . -name "__pycache__" -o -name "*.pyc" -o -name "*.log"
```

Expected:

- Không có Python source trong `static/` hoặc `templates/`
- Không có Tailwind CDN runtime
- Không có external font CDN runtime
- Không có artifact local/runtime trong source package

## 4. Vendor sanity check

```bash
python scripts/sync_vendor_assets.py
```

Kiểm tra thủ công:

- `static/vendor/chartjs/chart.umd.min.js`
- `static/vendor/html5-qrcode/html5-qrcode.min.js`
- `static/vendor/alpine/alpine.min.js`
- `static/vendor/jquery/jquery-3.7.0.min.js`
- `static/vendor/select2/select2.min.js`
- `static/vendor/fontawesome/css/all.min.css`

Expected:

- file có kích thước hợp lý, không phải placeholder cực nhỏ
- CSS/webfonts FontAwesome đầy đủ
- không request CDN cho các thư viện này

## 5. Brand / wording gate

```bash
grep -R "War Room\|Sentinel\|Tactical\|Security Command System\|SCMD ERP\|ENTERPRISE SECURITY PLATFORM\|\bESP\b" -n templates static main dashboard users operations accounting clients inspection inventory mobile
```

Expected:

- Runtime path không còn wording legacy/cyber sai contract

## 6. Production deploy order

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm migrate
docker compose -f docker-compose.prod.yml run --rm collectstatic
docker compose -f docker-compose.prod.yml up -d web nginx celery celery_beat
```

Expected:

- web container không tự `collectstatic`
- static đã có sẵn trước khi web phục vụ traffic

## 7. Demo server smoke checklist

- `Env`
  - `SECRET_KEY`, `SCMD_ORGANIZATION_ID`, export/encryption secrets, Redis, mail vars đã set đúng
  - Docker prod/demo `.env` có đủ `SQL_DATABASE`, `SQL_USER`, `SQL_PASSWORD`, `DATABASE_URL`, `REDIS_URL`, `SCMD_ORGANIZATION_ID`
  - `DATABASE_URL` dùng host `db`, scheme `postgis://`; `REDIS_URL` dùng host `redis`; không dùng SQLite/localhost trong compose prod
- `Migrate`
  - migrate thành công, không có lỗi schema drift mới
- `Collectstatic`
  - chạy riêng thành công trước khi start web
- `Start web/worker`
  - web, nginx, celery, celery_beat healthy
- `Static smoke`
  - `curl -I http://localhost:8000/static/common/css/brand_system.css`
  - xác nhận `/static/` có cache headers
- `Login smoke`
  - `/login/` render và đăng nhập được
- `Dashboard smoke`
  - `/dashboard/` render, chart lên, không lỗi đỏ console
- `Admin smoke`
  - `/admin/` render, không gọi Google Fonts
- `QR smoke`
  - mobile patrol page mở camera trên HTTPS
- `Chart smoke`
  - chart dashboard render thật bằng local Chart.js

## 8. HTTP smoke

```bash
curl -I http://localhost:8000/login/
curl -I http://localhost:8000/dashboard/
curl -I http://localhost:8000/accounting/dashboard/
curl -I http://localhost:8000/inventory/
curl -I http://localhost:8000/admin/
curl -I http://localhost:8000/static/common/css/brand_system.css
curl -I http://localhost:8000/sw.js
```

Expected:

- HTML không cache cứng
- `/static/` có `Cache-Control` dài hạn
- `/sw.js` không cache cứng

## 9. Benchmark checklist

- Đo server time, query count, SQL time, render time ở:
  - `/dashboard/`
  - `/accounting/dashboard/`
  - `/inventory/`
  - `/users/dashboard/`
  - `/inspection/dashboard/`
- Xác nhận target demo:
  - dashboard nghiệp vụ ưu tiên dưới `800ms` server time khi dữ liệu demo hợp lý
  - query count ưu tiên dưới `50`, chấp nhận dưới `100` với dashboard tổng hợp
  - template render ưu tiên dưới `150ms`

## 10. Release gate

Chỉ claim `demo-ready` khi:

- `release_contract_check.py` PASS trên package/source cuối cùng
- package không chứa artifact cấm
- admin/runtime không gọi Google Fonts
- không còn vendor stub cho thư viện đang dùng
- icons/logo/font render đúng
- collectstatic/deploy flow tách bạch, deterministic
- smoke test browser/mobile hoàn tất
