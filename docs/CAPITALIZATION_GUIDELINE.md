<!-- Governance dependency referenced by DOCUMENTATION.md. -->

# SCMD Pro Capitalization Guideline

## Mục đích

Tài liệu này chuẩn hóa cách viết hoa và viết thường trên toàn bộ giao diện SCMD Pro để:

- giảm nhiễu thị giác,
- giảm tải nhận thức,
- giữ ngôn ngữ ERP nội bộ nhất quán,
- tránh việc mỗi màn hình dùng một kiểu font-case khác nhau.

Phạm vi áp dụng:

- `templates/`
- `static/`
- chuỗi hiển thị trong Python, JavaScript, HTML, CSS-generated content
- tài liệu mô tả component của team design/dev/QA

## Nguyên tắc mặc định

Đối với giao diện tiếng Việt, `Sentence case` là chuẩn mặc định toàn hệ thống.

Ví dụ:

- `Bảng điều khiển`
- `Quản trị nhân sự`
- `Tạo phiếu điều động`
- `Vui lòng nhập mật khẩu`

Không dùng `Title Case` như chuẩn mặc định cho UI tiếng Việt nội bộ.

## Quy tắc theo loại viết hoa

### 1. Sentence case

Sử dụng cho hầu hết thành phần UI.

Áp dụng cho:

- tiêu đề trang,
- menu điều hướng,
- tên tab,
- nút bấm,
- nhãn biểu mẫu,
- placeholder,
- helper text,
- toast,
- thông báo lỗi,
- thông báo thành công,
- tiêu đề card,
- tên cột bảng,
- badge trạng thái thông thường.

Ví dụ đúng:

- `Đăng nhập`
- `Quên mật khẩu`
- `Quản lý kho và vật tư`
- `Cảnh báo quyết toán`

Ví dụ sai:

- `ĐĂNG NHẬP`
- `Quản Lý Kho Và Vật Tư`
- `CẢNH BÁO QUYẾT TOÁN`

### 2. Title Case

Chỉ dùng hạn chế khi hiển thị:

- tên riêng tiếng Anh,
- tên tài liệu chính thức,
- tên module/public heading có tính danh xưng,
- thương hiệu hoặc nhãn sản phẩm đã được định danh riêng.

Ví dụ chấp nhận:

- `SCMD Pro Technical Console`
- `Weekly Operations Report`

Không dùng `Title Case` cho menu, button, form label tiếng Việt.

### 3. UPPERCASE

Chỉ dùng cho tín hiệu thị giác phụ, không dùng làm chuẩn nội dung chính.

Áp dụng cho:

- section label rất ngắn,
- eyebrow/kicker nhỏ phía trên heading,
- mã viết tắt chuẩn,
- token kỹ thuật ngắn.

Ví dụ chấp nhận:

- `HỆ THỐNG`
- `GPS`
- `OTP`
- `API`

Không áp dụng cho:

- menu chính,
- tên module,
- nút bấm,
- thông báo lỗi,
- tiêu đề form,
- chuỗi mô tả dài.

### 4. lowercase

Chỉ dùng khi có lý do kỹ thuật.

Áp dụng cho:

- email,
- username,
- slug,
- key kỹ thuật,
- mã nội bộ cần giữ nguyên định dạng.

Ví dụ:

- `admin@scmd.local`
- `attendance_sync_job`

## Quy tắc theo component

| Thành phần | Quy tắc bắt buộc | Ví dụ đúng |
|---|---|---|
| Tiêu đề trang | Sentence case | `Bảng điều khiển` |
| Menu sidebar | Sentence case | `Quản trị nhân sự` |
| Section divider | UPPERCASE ngắn | `HỆ THỐNG` |
| Button | Sentence case | `Xác nhận in` |
| Form label | Sentence case | `Mật khẩu` |
| Placeholder | Sentence case | `Nhập mã xác minh` |
| Error message | Sentence case | `Vui lòng nhập mật khẩu.` |
| Toast title | Sentence case | `Cảnh báo quyết toán` |
| Badge trạng thái | Sentence case mặc định | `Ổn định` |
| Bảng dữ liệu | Sentence case | `Mã nhân viên` |
| Footer ngắn | Sentence case hoặc UPPERCASE ngắn nếu là nhãn thương hiệu | `© SCMD` |

## Ngoại lệ được phép

Các trường hợp sau có thể giữ nguyên và không ép về `Sentence case`:

- tên thương hiệu: `SCMD`, `SCMD Pro`,
- từ viết tắt chuẩn: `GPS`, `API`, `OTP`, `IT`, `ID`,
- mã nhân viên, mã hợp đồng, mã ca trực,
- tên pháp nhân nếu tài liệu yêu cầu đúng định dạng pháp lý,
- mẫu biểu in ấn có tính hành chính/pháp lý cần trình bày theo chuẩn riêng.

Nếu dùng ngoại lệ, phải có lý do rõ ràng về thương hiệu, pháp lý hoặc nghiệp vụ.

## Những lỗi cần tránh

- dùng `text-transform: uppercase` trên toàn bộ `.btn`, `.nav-link`, `label`, `th` mà không có lý do.
- hard-code chuỗi in hoa toàn bộ trong JavaScript hoặc CSS-generated content.
- trộn `Sentence case` và `UPPERCASE` cho các item cùng cấp trong một menu.
- dùng `Title Case` cho tiếng Việt nội bộ vì “trông sang hơn”.
- dùng `&` và `và` lẫn lộn cho cùng một pattern đặt tên.

## Nguyên tắc triển khai kỹ thuật

- Ưu tiên lưu chuỗi ở dạng đúng ngay từ source.
- Không phụ thuộc vào `text-transform` để “chữa cháy” nội dung sai case.
- Chỉ dùng `text-transform: uppercase` cho class chuyên biệt như:
  - `.section-label`
  - `.eyebrow`
  - `.status-code`
- Không áp dụng uppercase diện rộng cho:
  - `.btn`
  - `.nav-link`
  - `.form-label`
  - `.sidebar-item`

## Checklist review trước khi merge

- Chuỗi mới thuộc loại component nào?
- Component đó có dùng đúng quy tắc case bắt buộc không?
- Có đang viết hoa toàn bộ chỉ vì mục đích trang trí không?
- Chuỗi này có lặp kiểu khác ở màn hình cùng cấp không?
- Có đang dùng `text-transform` để che nội dung source bị sai không?
- Có ngoại lệ thương hiệu/pháp lý nào cần giữ nguyên không?

## Cách quét nhanh trong codebase

Quét các chỗ có nguy cơ lạm dụng uppercase:

```bash
rg -n "text-transform:\\s*uppercase" templates static
rg -n "content:\\s*\\\"[A-ZÀ-Ỵ0-9 &/-]{4,}\\\"" static
rg -n "\"[A-ZÀ-Ỵ0-9 &/-]{4,}\"|'[A-ZÀ-Ỵ0-9 &/-]{4,}'" templates static
```

## Quyết định chuẩn cho SCMD Pro

- Chuẩn mặc định toàn hệ thống: `Sentence case`
- `UPPERCASE` chỉ là tín hiệu phụ
- `Title Case` chỉ dùng có chủ đích
- không dùng `ALL CAPS` cho menu, button, form, toast, message thông thường
