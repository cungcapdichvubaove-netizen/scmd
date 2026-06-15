<!-- Governance dependency referenced by DOCUMENTATION.md. -->

# Admin Localization Audit

Tài liệu này ghi nhận các chuỗi còn tiếng Anh trên `/admin/`, phân loại theo mức độ nên Việt hóa và chỉ rõ ngoại lệ kỹ thuật cần giữ nguyên để tránh hiểu sai hoặc gây lỗi.

## 1. Nên Việt hóa ngay

Các chuỗi này là UI thuần hiển thị cho người vận hành, không gắn với identifier kỹ thuật:

| Vị trí | Chuỗi cũ | Trạng thái |
|---|---|---|
| `config/urls.py` | `SCMD Technical Console` | Đã đổi thành `Quản trị kỹ thuật SCMD` |
| `config/jazzmin_conf.py` | `SCMD Technical Console` | Đã đổi thành `Quản trị kỹ thuật SCMD` |
| `templates/admin/base_site.html` | `SCMD Technical Console` | Đã đổi thành `Quản trị kỹ thuật SCMD` |
| `templates/admin/index.html` | `Technical Console` | Đã đổi thành `Bảng quản trị kỹ thuật` |
| `templates/admin/index.html` | `User`, `Action`, `Module`, `Status` | Đã đổi sang `Người dùng`, `Hành động`, `Phân hệ`, `Trạng thái` |
| `templates/admin/index.html` | `results`, `records` | Đã đổi sang `kết quả`, `bản ghi` |
| `templates/admin/index.html` | `Admin Taxonomy` | Đã đổi thành `Phân loại quản trị` |
| `templates/base.html` | `Technical Console` | Đã đổi thành `Bảng quản trị kỹ thuật` |
| `templates/partials/_sidebar.html` | `Technical Console` | Đã đổi thành `Bảng quản trị kỹ thuật` |
| `main/templatetags/admin_console.py` | `CORE MASTER DATA`, `ACCESS & SECURITY`, ... | Đã đổi sang nhãn tiếng Việt |
| `main/templatetags/admin_console.py` | `Critical`, `Permission-sensitive`, ... | Đã đổi sang nhãn tiếng Việt |
| `users/admin.py` | `Số lượng User` | Đã đổi thành `Số người dùng` |

## 2. Nên giữ tiếng Anh kỹ thuật có chủ đích

Các chuỗi này nên giữ lại toàn phần hoặc giữ một phần vì đây là thuật ngữ runtime, trạng thái hệ thống hoặc tên công nghệ:

| Chuỗi | Lý do |
|---|---|
| `Celery` | Tên công nghệ/scheduler cụ thể |
| `worker` | Thuật ngữ runtime quen thuộc trong vận hành kỹ thuật; có thể chú giải bằng ngữ cảnh tiếng Việt |
| `job` | Thuật ngữ tác vụ nền, nên giữ khi đi cùng runtime/debug |
| `heartbeat` | Thuật ngữ giám sát hạ tầng phổ biến, dịch sát dễ gây mơ hồ |
| `SUCCESS` | Mã trạng thái kỹ thuật cần khớp dữ liệu/log |
| `task_id` | Tên định danh kỹ thuật, không nên dịch |
| `Django`, `Jazzmin` | Tên framework/thư viện |

Nguyên tắc áp dụng:
- Có thể thêm vỏ ngữ cảnh tiếng Việt xung quanh, ví dụ `Tác vụ nền Celery`, `Worker chậm nhịp`.
- Không dịch các status code hoặc tên field kỹ thuật đang tham gia truy vấn/log/audit.

## 3. Tên riêng hoặc thư viện không nên đụng

| Chuỗi | Lý do |
|---|---|
| `SCMD`, `SCMD Pro` | Tên thương hiệu |
| `Font Awesome`, `Select2`, `AlpineJS` | Tên thư viện |
| `serviceWorker` | API trình duyệt |
| `PeriodicTask`, `TaskResult`, `WorkerHeartbeat` | Tên model/định danh kỹ thuật trong code |

## 4. Checklist rà tiếp cho `/admin/`

- Tên model và verbose name của app thứ ba có còn tiếng Anh không.
- Bộ lọc list view (`list_filter`) có còn label tiếng Anh do Django/Jazzmin render không.
- Các action label trong `ModelAdmin.actions` có còn trộn `User`, `Group`, `Status`, `Module` không.
- `help_text`, `short_description`, `verbose_name`, `verbose_name_plural` trong `admin.py` có còn tiếng Anh không.
- Các badge/runtime card có còn lẫn tiếng Anh thuần UI với thuật ngữ kỹ thuật không.
- Các empty state của admin list/detail có còn `No ... available` hoặc chuỗi fallback mặc định không.

## 5. Quy tắc triển khai

- Việt hóa ở nguồn render hoặc `verbose_name`, không vá bằng CSS.
- Không dịch identifier, status code và tên công nghệ.
- Với thuật ngữ kỹ thuật cần giữ, bọc trong câu tiếng Việt để người vận hành hiểu đúng ngữ cảnh.
- Mọi thay đổi ở `/admin/` phải ưu tiên an toàn cho permission, audit và dữ liệu vận hành.
