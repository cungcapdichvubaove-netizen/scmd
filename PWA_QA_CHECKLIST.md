# SCMD Pro PWA QA Checklist

Mục tiêu: xác nhận SCMD Pro PWA hoạt động ổn định trên public entry, desktop shell và mobile shell mà không làm sai contract dữ liệu vận hành.

## 1. Desktop install

- Mở `http://localhost:8000/login/` trên Chrome hoặc Edge.
- Xác nhận service worker đã đăng ký thành công tại `Application > Service Workers`.
- Xác nhận manifest hợp lệ tại `Application > Manifest`.
- Xác nhận panel cài đặt xuất hiện khi trình duyệt hỗ trợ `beforeinstallprompt`.
- Bấm `Cài ứng dụng`.
- Xác nhận ứng dụng mở ở chế độ `standalone` và tên app/manifest hiển thị **SCMD Pro**.
- Đăng nhập thành công và đi vào `hub`/dashboard SCMD Pro.

## 2. Desktop fallback

- Trên trình duyệt không phát `beforeinstallprompt`, mở `/login/`.
- Xác nhận panel hiển thị hướng dẫn cài đặt fallback thay vì nút cài đặt giả.
- Xác nhận ẩn panel không gây lỗi JS.

## 3. Android install

- Mở `/login/` trên Chrome Android.
- Xác nhận panel cài đặt xuất hiện hoặc fallback instruction xuất hiện đúng ngữ cảnh.
- Thêm vào màn hình chính.
- Mở ứng dụng từ icon.
- Xác nhận `display-mode: standalone`.
- Đăng nhập và vào `/operations/mobile/dashboard/` hoặc `hub` tùy vai trò.

## 4. iPhone install

- Mở `/login/` trong Safari iPhone.
- Xác nhận panel hiển thị hướng dẫn `Thêm vào Màn hình chính`.
- Thêm shortcut từ menu Share.
- Mở lại từ icon.
- Xác nhận status bar/theme hiển thị đúng và không vỡ layout mobile login.

## 5. Offline behavior

- Sau khi đã tải `/login/`, bật offline trong DevTools.
- Reload `/login/`: phải mở được từ cache.
- Mở `/password-reset/`: phải mở được từ cache nếu đã truy cập hoặc từ precache.
- Mở `/dashboard/` hoặc route nghiệp vụ chưa có mạng: không được trả dữ liệu cũ sai; phải rơi về trang `/offline/` hoặc lỗi mạng an toàn.

## 6. Static asset localization

- Xác nhận các shell sau không còn dùng CDN cho Font Awesome, jQuery, Select2:
  - `templates/base.html`
  - `templates/base_public.html`
  - `operations/templates/operations/mobile/base_mobile_revamped.html` cho Font Awesome
- Xác nhận asset local tồn tại:
  - `static/vendor/fontawesome-free/`
  - `static/vendor/jquery/`
  - `static/vendor/select2/`

## 7. Brand regression

- Login/public shell hiển thị tên **SCMD**.
- Tagline hiển thị đúng khi có không gian: **Nền tảng chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp**.
- Không còn `SCMD Pro`, `War Room`, `Sentinel`, `Tactical` trên public entry và mobile shell.
- Icon/app name/manifest nếu sửa phải thống nhất theo SCMD.

## 8. Regression safety

- Đăng nhập từ `/login/` vẫn hoạt động bình thường.
- `select2` ở authenticated shell vẫn hoạt động.
- Sidebar desktop vẫn collapse/expand được.
- Mobile sidebar vẫn mở/đóng được.
- User menu vẫn mở/đóng được.

## 9. Known residual risks

- `HTMX` trên mobile shell vẫn là dependency ngoài ở phase hiện tại.
- Font hệ thống đang được dùng để giảm phụ thuộc mạng; nếu muốn brand typography cố định hoàn toàn, cần localize bộ font chính thức ở phase tiếp theo.
