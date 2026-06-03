# SCMD ERP

**SCMD ERP** là hệ thống ERP vận hành chuyên biệt cho doanh nghiệp kinh doanh dịch vụ bảo vệ. Hệ thống không được định vị như một dashboard trình diễn, một “command center” kiểu cyber, hoặc một ERP tổng quát. Giá trị cốt lõi là tạo ra **operational truth**: dữ liệu vận hành đáng tin cậy để ra quyết định hằng ngày và làm căn cứ cho chấm công, lương, sự cố, kho và kiểm soát rủi ro.

> **SCMDPRO** là định hướng sản phẩm/chương trình phát triển. **SCMD ERP** là tên hệ thống phần mềm nội bộ được chuẩn hóa trong code, UI và tài liệu.

---

## 1. Hệ thống giải quyết vấn đề gì

SCMD ERP trả lời các câu hỏi vận hành quan trọng của một công ty bảo vệ:

- Hôm nay ai đang trực, trực ở mục tiêu nào, chốt nào, ca nào?
- Check-in/check-out có hợp lệ về thời gian, vị trí GPS, ảnh và phân công không?
- Mục tiêu nào thiếu quân số, có ca chưa được nhận, có nhân viên chưa check-in?
- Sự cố nào đang mở, mức độ nghiêm trọng ra sao, ai đang xử lý?
- Dữ liệu vận hành nào ảnh hưởng đến lương, khấu trừ, tạm ứng, đồng phục và đền bù?
- Kho còn đủ vật tư/đồng phục cho các mục tiêu không?
- Quản lý có thể kiểm tra, đối soát và khóa dữ liệu kỳ lương một cách minh bạch không?

---

## 2. Phạm vi chức năng chính

| Nhóm nghiệp vụ | Chức năng chính |
|---|---|
| CRM & hợp đồng | Lead, khách hàng, hợp đồng, mục tiêu bảo vệ, vị trí chốt |
| Vận hành hiện trường | Phân công ca, chấm công GPS/ảnh, kiểm tra quân số, alive check |
| Sự cố & rủi ro | Báo cáo sự cố, phân loại mức độ, theo dõi xử lý, biên bản |
| Nhân sự | Hồ sơ nhân viên, chức danh, phòng ban, trạng thái làm việc |
| Lương | Tính lương từ giờ thực tế, đơn giá mục tiêu, phụ cấp, khấu trừ, vi phạm |
| Kho | Vật tư, đồng phục, nhập/xuất, cấp phát theo mục tiêu/nhân viên |
| Thanh tra | Lịch tuần tra, kiểm tra hiện trường, biên bản vi phạm |
| Workflow | Đề xuất, phê duyệt, công việc nội bộ |
| Dashboard | Bảng điều hành vận hành cho lãnh đạo và điều phối |

---

## 3. Kiến trúc chính thức

SCMD ERP là **layered monolith**. Đây là quyết định kiến trúc chính thức từ dòng 3.x.

Hệ thống **không** được mô tả là microservices và **không** được ép vào clean architecture cứng nhắc. Mục tiêu hiện tại là giữ monolith rõ ràng, dễ kiểm soát, dễ deploy, dễ đối soát nghiệp vụ.

```text
Interface Layer       Django views, DRF endpoints, templates, WebSocket consumers
Application Layer     Use case classes, business orchestration, transaction boundary
Domain Helpers        Pure Python rules: geofence, payroll formulas, validators
Infrastructure Layer  Django ORM, Celery, Redis, Channels, storage, SMTP, integrations
```

Tài liệu chi tiết:

- [`WHITEPAPER.md`](WHITEPAPER.md): contract chiến lược và kiến trúc
- [`DOCUMENTATION.md`](DOCUMENTATION.md): technical reference
- [`UI_SYSTEM_REFACTOR_SPEC.md`](UI_SYSTEM_REFACTOR_SPEC.md): refactor UI/brand/system surface

---

## 4. Runtime stack

| Thành phần | Công nghệ |
|---|---|
| Backend | Python, Django 5.x |
| API | Django REST Framework, SimpleJWT, drf-spectacular |
| Database production | PostgreSQL + PostGIS |
| Database development | SQLite, chỉ dùng cho local/dev |
| Async jobs | Celery + Redis |
| Realtime | Django Channels + Daphne |
| Admin UI | Django Admin + Jazzmin |
| Frontend | Django templates + Tailwind CSS local build |
| Deploy | Docker Compose |

Runtime version cụ thể phải được xác nhận từ `requirements.txt`, lock file hoặc Docker image đang dùng. Không copy version thủ công vào tài liệu nếu chưa đối chiếu với dependency source of truth.

---

## 5. Hai giao diện chính

| Giao diện | URL | Vai trò |
|---|---|---|
| Operations Cockpit | `/dashboard/` | Bảng điều hành nghiệp vụ: ca trực, quân số, check-in, sự cố, kho, lương |
| Technical Console | `/admin/` | Quản trị kỹ thuật: dữ liệu nền, cấu hình, audit, system health |

Quy tắc sản phẩm:

- `/dashboard/` là nơi người dùng nghiệp vụ theo dõi vận hành hằng ngày.
- `/admin/` là console kỹ thuật, không phải business dashboard.
- Technical admin có quyền thao tác mạnh, nhưng mọi thao tác sửa dữ liệu nghiệp vụ nhạy cảm phải được audit theo policy trong `WHITEPAPER.md`.

---

## 6. Core modules

```text
main/         Core app, audit log, worker heartbeat, company config
users/        Nhân sự, nhân viên, chức danh, phòng ban
clients/      Lead, khách hàng, hợp đồng, mục tiêu bảo vệ, vị trí chốt
operations/   Phân công ca, chấm công, sự cố, kiểm tra quân số, alive check
accounting/   Lương, phụ cấp, khấu trừ, tạm ứng, sổ quỹ
inventory/    Vật tư, đồng phục, nhập/xuất/cấp phát
inspection/   Thanh tra, tuần tra, biên bản vi phạm
workflow/     Đề xuất, phê duyệt, công việc nội bộ
notifications/ Thông báo, push, realtime alerts
dashboard/    Operations cockpit, KPI aggregation
mobile/       Mobile/API surface cho nhân viên hiện trường
```

---

## 7. Local bootstrap

Credential local/dev phải được tạo bằng bootstrap script hoặc environment variables. Không được xem credential mẫu là credential production.

```text
username: admin
email:    admin@scmd.local
password: local/dev only — phải override trong production
```

Production deployment bắt buộc override:

- `SECRET_KEY`
- database credentials
- Redis credentials nếu có
- admin password
- encryption keys
- export password
- email/SMS/push credentials
- Cloudinary/storage credentials nếu dùng

---

## 8. Docker workflow

Development:

```bash
docker compose up --build
```

Production:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Quy tắc production:

- Không để long-running web/worker container tự chạy migration ngầm nếu chưa có migration plan.
- Migration production phải có backup, rollback note và kiểm tra post-deploy.
- Dữ liệu chấm công/lương/sự cố phải được đối soát sau các migration liên quan.

---

## 9. Validation commands

Các lệnh kiểm tra tối thiểu trước khi merge/release:

```bash
python manage.py check
python manage.py test
python manage.py showmigrations --plan
find static/ -name "*.py"
find . -path "*/templates/*" -name "*.py"
grep -R "cdn.tailwindcss.com" -n .
grep -R "from .* import \*" -n */application/*.py
```

Các lệnh grep có thể trả về vendor/minified artifacts. Khi đánh giá phải phân loại rõ: file do team sở hữu là lỗi cần xử lý; vendor artifact chỉ xử lý nếu được serve hoặc ảnh hưởng runtime.

---

## 10. Development rules

- Không dùng `cdn.tailwindcss.com` trong template production.
- Không đặt file Python trong `static/` hoặc `templates/`.
- Không dùng wildcard import trong application layer.
- Không tạo duplicate manager, duplicate model, duplicate use case SSOT.
- Không đưa lại ngôn ngữ `Security Command System`, `Sentinel`, `War Room`, `Tactical` vào UI người dùng.
- Mọi flow chấm công, lương, sự cố, export dữ liệu nhạy cảm phải có audit trail.
- Nếu code lệch tài liệu, phải tạo issue để sửa code hoặc cập nhật contract có lý do và changelog.

---

## 11. Tình trạng hiện tại

Bộ tài liệu này là contract mục tiêu cho SCMDPRO/SCMD ERP dòng 3.x. Một số debt đã được xác nhận trong code hiện tại và cần xử lý theo `WHITEPAPER.md`:

- file `.py` nằm sai trong `static/` hoặc `templates/`,
- wildcard facade trong application layer,
- duplicate `TenantAwareManager`,
- Tailwind CDN trong template,
- dấu vết brand cũ kiểu cyber/war-room,
- mojibake/encoding trong file nội bộ,
- tenant/organization boundary chưa nhất quán.
