# PRODUCTION DEMO READINESS REPORT

Date: `2026-06-14`  
Product: `SCMD Pro`  
Scope: production demo hardening for release package, runtime assets, deploy surface and cache behavior

## 1. Release package status

Status: `Conditionally ready`

Đã xử lý:

- có script dọn artifact local/runtime trước khi đóng gói
- validator release đã kiểm tra:
  - merge conflict markers
  - `.py` trong `static/`
  - `.py` trong `templates/`
  - wildcard import trong `application/`
  - Tailwind CDN
  - external font CDN
  - vendor runtime stub
  - forbidden artifacts trong source ZIP

Điểm cần tuân thủ khi đóng gói:

- không đóng `node_modules/`
- không đóng `staticfiles/`
- không đóng `media/`
- không đóng `__pycache__/`, `.pyc`, `.log`, temp profile, secrets

## 2. Vendor JS/CSS status

Status: `Ready at source level`

Đã localize và pin version:

- Chart.js `4.4.3`
- jQuery `3.7.1`
- Select2 `4.1.0-rc.0`
- Alpine `3.14.1`
- html5-qrcode `2.3.8`
- FontAwesome `6.5.2`
- Dexie `4.0.8`
- htmx `1.9.12`
- NProgress `0.2.0`
- Bootstrap bundle `4.6.2`

Vendor files runtime trong `static/vendor` hiện có kích thước hợp lý, không còn dạng placeholder cực nhỏ.

## 3. Font / icon / logo status

Status: `Ready at source level`

Đã xử lý:

- bỏ Google Fonts khỏi admin runtime
- dùng font local trong PWA/runtime assets
- copy đủ FontAwesome CSS + webfonts local
- thay logo SVG nặng bằng SVG vector nhỏ gọn
- bỏ audio placeholder scan feedback, thay bằng Web Audio API

Kỳ vọng sau deploy:

- không request `fonts.googleapis.com`
- icon sidebar/header/card không thành dấu chấm
- logo sidebar/login/report không tải file vài trăm KB

## 4. Collectstatic / deploy status

Status: `Ready in config`

Đã xử lý:

- web container không còn mặc định `collectstatic` khi start
- có service `collectstatic` riêng trong `docker-compose.prod.yml`
- flow deploy rõ: build -> migrate -> collectstatic -> start web/worker -> smoke

## 5. Nginx static cache status

Status: `Ready in config`

Đã xử lý:

- `/static/` có `try_files $uri =404`
- cache dài hạn `public, max-age=2592000, immutable`
- `gzip_static on`
- `X-Content-Type-Options: nosniff`
- HTML/app traffic `/` trả `Cache-Control: no-store`
- `/media/` vẫn private/auth-gated

## 6. PWA cache status

Status: `Ready at source level`

Đã xử lý:

- cache version theo `SCMD_PRO_CACHE_VERSION`
- `/sw.js` không cache cứng
- activate phase xóa cache version cũ
- không cache auth-like endpoints và `/media/`

Rủi ro còn lại:

- cần smoke test update flow trên browser thật sau deploy để xác nhận không còn stale CSS/JS

## 7. Performance instrumentation status

Status: `Ready in config`

Phạm vi prefix hiện cover:

- `/admin/`
- `/dashboard/`
- `/operations/`
- `/accounting/`
- `/inventory/`
- `/users/`
- `/clients/`
- `/inspection/`
- `/workflow/`
- `/mobile/`

## 8. Benchmark status

Status: `Not executed in this environment`

Chưa đo được:

- server time dashboard thực tế
- query count thực tế
- render time thực tế
- browser FCP / layout shift / second-load cache hit

Nguyên nhân:

- host hiện thiếu GDAL/PROJ nên không chạy được Django checks/server smoke trực tiếp
- chưa chạy production-like container đầy đủ để benchmark bằng dữ liệu demo

## 9. Smoke test checklist

Sau deploy server demo thật, bắt buộc kiểm tra:

- `/login/`
- `/dashboard/`
- `/operations/`
- `/accounting/dashboard/`
- `/inventory/`
- `/users/dashboard/`
- `/inspection/dashboard/`
- `/admin/`
- trang mobile QR patrol trên HTTPS
- chart/dashboard có render thật
- console browser không có lỗi đỏ
- network không gọi Google Fonts hay Tailwind CDN

## 10. Remaining risks

- `python manage.py check` và test suite chưa chạy được trên host hiện tại do thiếu GDAL/PROJ runtime.
- QR scanner/camera mới được xác nhận ở mức asset/runtime source; chưa xác minh camera thật trên mobile HTTPS trong phiên này.
- Nếu release ZIP được tạo ngoài quy trình clean/audit đã cập nhật, vẫn có rủi ro người vận hành đóng nhầm artifact local.

## 11. Current conclusion

Kết luận hiện tại: `source/config demo-hardening đã sẵn sàng cho production-like deploy`, nhưng chỉ nên claim `demo-ready` sau khi:

1. `release_contract_check.py` PASS trên clean copy/package cuối cùng
2. production-like compose build/collectstatic chạy thành công
3. smoke test browser/mobile thực hiện xong trên server demo HTTPS
