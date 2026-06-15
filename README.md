# SCMD Pro

**SCMD Pro** là phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp. Hệ thống không được định vị như một dashboard trình diễn, một “command center” kiểu cyber, hoặc một ERP tổng quát. Giá trị cốt lõi là tạo ra **operational truth**: dữ liệu vận hành đáng tin cậy để ra quyết định hằng ngày và làm căn cứ cho chấm công, lương, sự cố, kho và kiểm soát rủi ro.

> **SCMD** là công ty/thương hiệu mẹ. **SCMD Pro** là tên user-facing của sản phẩm. `ERP` chỉ được dùng để mô tả các năng lực quản trị nội bộ của hệ thống, không phải tên thương hiệu chính.

---

## 1. Hệ thống giải quyết vấn đề gì

SCMD Pro trả lời các câu hỏi vận hành quan trọng của một công ty bảo vệ:

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
| Nhân sự | Hồ sơ nhân viên, chức danh, phòng ban, HĐLĐ, nghỉ phép, bảo hiểm, nghỉ việc/offboarding |
| Lương | Tính lương từ giờ thực tế, đơn giá mục tiêu, phụ cấp, tạm ứng, khấu trừ, nghỉ phép, bảo hiểm, đối soát nguồn |
| Kho | Vật tư, đồng phục, nhập/xuất, cấp phát, thu hồi tài sản, mất/hỏng gắn offboarding |
| Thanh tra | Lịch tuần tra, kiểm tra hiện trường, biên bản vi phạm |
| Workflow | Đề xuất, phê duyệt, công việc nội bộ |
| Dashboard | Bảng điều hành vận hành cho lãnh đạo và điều phối |

---

## 3. Kiến trúc chính thức

SCMD Pro được triển khai theo kiến trúc **layered monolith**. Đây là quyết định kiến trúc chính thức từ dòng 3.x.

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
- [`cursorrules.md`](cursorrules.md): AI/tooling governance, subordinate to the four authority docs above

Lưu ý tài liệu:

- `README.md`, `WHITEPAPER.md`, `DOCUMENTATION.md`, `UI_SYSTEM_REFACTOR_SPEC.md`, và `cursorrules.md` là current contract.
- `CHANGELOG.md`, release notes, patch reports, verify reports, và hardening reports là tài liệu lịch sử/xác minh theo từng đợt, không tự động ghi đè current contract.

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
inventory/    Vật tư, đồng phục, nhập/xuất/cấp phát/thu hồi tài sản
inspection/   Thanh tra, tuần tra, biên bản vi phạm
workflow/     Đề xuất, phê duyệt, công việc nội bộ
notifications/ Thông báo, push, realtime alerts
dashboard/    Operations cockpit, KPI aggregation
mobile/       Mobile/API surface cho nhân viên hiện trường
```


### 6.1 Business workflow A→F đã được chuẩn hóa

Từ Phase A đến Phase F, SCMD Pro đã chuyển nhiều nghiệp vụ từ “field rời/admin record” thành hồ sơ nguồn có vòng đời riêng:

| Phase | Nghiệp vụ | SSOT/source records |
|---|---|---|
| A | Hợp đồng lao động | `users.HopDongLaoDong`, `users.PhuLucHopDongLaoDong` |
| B | Nghỉ phép, nghỉ việc, bảo hiểm, đổi ca, tạm ứng/khấu trừ, nghiệm thu/hóa đơn/công nợ | Dedicated records trong `users`, `operations`, `accounting`, `clients` |
| C | Workflow integration | transition policy, `ShiftChangeRequest APPLIED`, payroll reconciliation |
| D | Scope/report/payroll hardening | scoped swap-rate report, payroll snapshot protection, leave proration, direct-status static guard |
| E | Thanh toán khách hàng/công nợ | `clients.ThanhToanKhachHang`, `clients.PhanBoThanhToanHoaDon` |
| F | Thu hồi tài sản/offboarding inventory | `inventory.PhieuThuHoi`, `ChiTietPhieuThuHoi`, `BienBanMatHongVatTu` |

Tài liệu hệ thống: [`docs/BUSINESS_WORKFLOW_A_TO_F_SYSTEM_CONTRACT.md`](docs/BUSINESS_WORKFLOW_A_TO_F_SYSTEM_CONTRACT.md).

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
- CORS_ALLOWED_ORIGINS
- UI tokens (colors, fonts, spacing) phải dùng SSOT từ `theme/tailwind.config.js`
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

Quy tắc production/demo Docker:

- Không để long-running web/worker container tự chạy migration ngầm nếu chưa có migration plan.
- Migration production phải có backup, rollback note và kiểm tra post-deploy.
- Dữ liệu chấm công/lương/sự cố phải được đối soát sau các migration liên quan.
- `docker-compose.prod.yml` bắt buộc dùng PostGIS qua `DATABASE_URL=postgis://...@db:5432/...`; không dùng `localhost` và không fallback SQLite.
- Redis bắt buộc dùng `REDIS_URL=redis://redis:6379/0` trong compose.
- `.env` tối thiểu phải có `SQL_DATABASE`, `SQL_USER`, `SQL_PASSWORD`, `DATABASE_URL`, `REDIS_URL`, `SCMD_ORGANIZATION_ID`.

---

## 9. Validation commands

Các lệnh kiểm tra tối thiểu trước khi merge/release:

```bash
python manage.py check
python manage.py test
python manage.py showmigrations --plan
python manage.py test users.tests_labor_contract_phase_a users.tests_business_domain_phase_b
python manage.py test users.tests_business_workflow_phase_c users.tests_business_workflow_phase_d
python manage.py test clients.tests_phase_e_customer_payment
python manage.py test inventory.tests_phase_f_asset_recovery
find static/ -name "*.py"
find . -path "*/templates/*" -name "*.py"
grep -R "Tailwind CDN" -n .
grep -R "from .* import \*" -n */application/*.py
```

Các lệnh grep có thể trả về vendor/minified artifacts. Khi đánh giá phải phân loại rõ: file do team sở hữu là lỗi cần xử lý; vendor artifact chỉ xử lý nếu được serve hoặc ảnh hưởng runtime.

---

## 10. Development rules

- Không dùng `Tailwind CDN` trong template production.
- Không đặt file Python trong `static/` hoặc `templates/`.
- Không dùng wildcard import trong application layer.
- Không tạo duplicate manager, duplicate model, duplicate use case SSOT.
- Không đưa lại ngôn ngữ legacy kiểu cyber-console vào UI người dùng; dùng SCMD Pro và thuật ngữ vận hành nghiệp vụ.
- Mọi flow chấm công, lương, sự cố, hợp đồng lao động, đổi ca, nghỉ phép, thanh toán khách hàng, công nợ, thu hồi tài sản, offboarding và export dữ liệu nhạy cảm phải có audit trail.
- Production surface hardening: xem `docs/PRODUCTION_SURFACE_HARDENING_CONTRACT.md` cho `/media/`, HTTPS, backup/restore và release ZIP hygiene.
- Incident lifecycle SSOT: xem `docs/INCIDENT_LIFECYCLE_CONTRACT.md`; không dùng nhãn legacy/migration làm contract mới.
- Không dùng `Proposal`/`BaoCaoDeXuat` thay cho hồ sơ nghiệp vụ có vòng đời riêng như đổi ca, nghỉ phép, thanh toán khách hàng hoặc thu hồi tài sản.
- Nếu code lệch tài liệu, phải tạo issue để sửa code hoặc cập nhật contract có lý do và changelog.

---

## 11. Tình trạng hiện tại

Bộ tài liệu này là contract mục tiêu cho SCMD/SCMD Pro dòng 3.x. Các debt lịch sử như file Python đặt sai trong `static/`/`templates/`, Tailwind CDN runtime, duplicate manager và brand/copy kiểu cyber/war-room phải tiếp tục được kiểm tra trước release, nhưng không được tự động xem là current P0 nếu scan codebase hiện tại không còn bằng chứng.

Phân loại khi audit/release:

- **Historical debt đã xử lý:** ghi trong changelog/verify report, không hạ điểm runtime nếu grep hiện tại sạch.
- **Validation checklist bắt buộc:** vẫn chạy `find`/`grep` trước khi release để ngăn tái phát.
- **Current known issues:** chỉ ghi nhận khi có bằng chứng file:line hoặc log runtime mới.

Nếu phát hiện tái xuất hiện một trong các lỗi sau trong source do dự án sở hữu, phải mở P1/P2 tương ứng và ghi vào VERIFY_REPORT.md: `.py` trong `static/`/`templates/`, Tailwind CDN runtime, wildcard facade application layer, duplicate organization-scope manager, hardcoded tenant/org id ngoài settings, hoặc brand copy sai định vị SCMD Pro.
