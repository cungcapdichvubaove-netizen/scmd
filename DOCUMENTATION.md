# DOCUMENTATION.md — SCMD Pro Technical Reference

Status: **Technical reference for implementation**
Version: 3.5.0
Updated: 2026-06-03

Tài liệu này mô tả kỹ thuật triển khai sản phẩm SCMD Pro thuộc thương hiệu/công ty SCMD. `WHITEPAPER.md` là contract chiến lược/kiến trúc; file này là reference để developer, operator và reviewer kiểm tra code, runtime, module map, flow nghiệp vụ và deployment.

Patch note 3.5.0:
- Chuẩn hóa kiến trúc thương hiệu: **SCMD** là công ty/thương hiệu mẹ; **SCMD Pro** là sản phẩm phần mềm thương mại.
- Tagline sản phẩm chính thức: **Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp**.
- `ERP` chỉ còn là nhóm năng lực quản trị nội bộ trong SCMD Pro, không phải tên brand user-facing.
- Public auth templates phải chạy trên local Tailwind build và `static/common/css/brand_system.css`, không dùng Tailwind CDN runtime.
- Regression coverage tối thiểu hiện bao gồm attendance application use cases (`CheckInUseCase`, `CheckOutUseCase`, `CalculateWorkHoursUseCase`) và payroll audit use case (`AuditPayrollUseCase`).

---

## 0. Brand Architecture

- **SCMD**: công ty/thương hiệu mẹ, viết tắt từ **Security Commander**.
- **SCMD Pro**: sản phẩm phần mềm thương mại bán cho doanh nghiệp dịch vụ bảo vệ.
- User-facing product name trong login, dashboard, PWA, admin title, print/export: **SCMD Pro**.
- `ERP` chỉ là năng lực quản trị nội bộ của SCMD Pro, không phải tên sản phẩm.

## 1. System Position

**SCMD** là công ty/thương hiệu mẹ, viết tắt từ **Security Commander**.

**Định vị công ty:** SCMD — Công ty công nghệ phần mềm cho ngành dịch vụ bảo vệ.

**Định vị sản phẩm:** SCMD Pro — Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp.

SCMD Pro là phần mềm chỉ huy và quản trị chuyên biệt cho doanh nghiệp dịch vụ bảo vệ, triển khai theo mô hình **single-organization hardened**. Hệ thống tối ưu cho các flow:

- CRM: lead → khách hàng → hợp đồng → mục tiêu bảo vệ → vị trí chốt.
- Vận hành: phân công ca → chấm công GPS/ảnh → kiểm tra quân số → sự cố/alive check.
- Tài chính: giờ công thực tế → đơn giá mục tiêu → phụ cấp/khấu trừ → bảng lương.
- Hỗ trợ: kho vật tư/đồng phục, thanh tra, workflow nội bộ, notification.

`tenant_id` nếu có trong code hiện tại là legacy naming cho organization scope cố định, không phải SaaS multi-tenant.

---

## 2. Architecture

### 2.1 Layered Monolith

```text
Interface Layer       views.py, api_views.py, serializers.py, templates/, consumers.py
Application Layer     */application/*.py, use case classes, orchestration, transaction boundary
Domain Helpers        core/domain/, geo.py, validators, payroll formulas, state transition rules
Infrastructure Layer  models.py, tasks.py, signals.py, storage, Redis, Celery, Channels
```

Boundary rules:

- Views/API không chứa business orchestration dài.
- Use case class chịu trách nhiệm điều phối flow nhiều bước.
- Domain helper không phụ thuộc request/session/template.
- ORM model không gọi qua lại như service layer.
- Celery task gọi application layer, không nhân bản logic nghiệp vụ.

### 2.2 Runtime Stack

| Component | Technology | Ghi chú |
|---|---|---|
| Framework | Django 5.x | Version cụ thể lấy từ dependency source of truth |
| API | DRF, SimpleJWT, drf-spectacular | Mobile/API contract |
| Database production | PostgreSQL + PostGIS | Bắt buộc cho geospatial production |
| Database development | SQLite | Chỉ local/dev |
| Async jobs | Celery + Redis | Worker/beat tách khỏi web |
| Realtime | Django Channels + Daphne | WebSocket/notifications |
| Admin | Django Admin + Jazzmin | Technical console |
| Frontend | Django templates + Tailwind local build | Không dùng CDN production |
| Deploy | Docker Compose | Dev/prod compose tách biệt |

Version trong bảng không được coi là nguồn sự thật nếu khác `requirements.txt`, lock file hoặc Docker image đang dùng.

### 2.3 Installed Apps Order

`daphne` phải đứng trước Django contrib apps nếu dùng ASGI/Channels. `jazzmin` phải đứng trước `django.contrib.admin` để override admin UI.

```python
INSTALLED_APPS = [
    "daphne",
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    # third-party apps...
    "main", "users", "clients", "operations",
    "inventory", "inspection", "accounting",
    "workflow", "notifications", "backup_restore",
    "reports", "dashboard", "mobile",
]
```

---

## 3. Module Map

| Module | Vai trò | Model/Surface chính |
|---|---|---|
| `main` | Core config, audit, worker health | `AuditLog`, `WorkerHeartbeat`, `CompanyInfo` |
| `users` | Nhân sự | `NhanVien`, `ChucDanh`, `PhongBan` |
| `clients` | CRM/hợp đồng/mục tiêu | `KhachHangTiemNang`, `HopDong`, `MucTieu` |
| `operations` | Vận hành hiện trường | `PhanCongCaTruc`, `ChamCong`, `BaoCaoSuCo`, `KiemTraQuanSo` |
| `accounting` | Lương, phụ cấp, khấu trừ, sổ quỹ | `BangLuongThang`, `ChiTietLuong`, `CauHinhLuong`, `SoQuy` |
| `inventory` | Kho vật tư/đồng phục | `VatTu`, `PhieuNhap`, `PhieuXuat` |
| `inspection` | Thanh tra/tuần tra | `LichThanhTra`, `BienBanViPham` |
| `workflow` | Đề xuất/phê duyệt/công việc | `Proposal`, `Task` |
| `notifications` | Push/realtime notification | Consumers, tasks, FCM integration |
| `dashboard` | Operations cockpit | KPI aggregation, executive dashboard use case |
| `mobile` | Mobile/API composition | API routing/surface |

---

## 4. Technical SSOTs

### 4.1 Audit

SSOT: `main.models.AuditLog`.

Rules:

- Không tạo audit model thứ hai.
- Legacy re-export chỉ được tồn tại tạm thời.
- Mọi sửa dữ liệu nhạy cảm phải ghi audit theo `WHITEPAPER.md`.

### 4.2 Worker Health

SSOT: `main.models.WorkerHeartbeat`.

Worker heartbeat dùng để theo dõi Celery/worker runtime. Dashboard/system health không được tự tạo cơ chế heartbeat riêng nếu chưa có lý do kiến trúc.

### 4.3 Alive Check

SSOT: `operations.models.KiemTraQuanSo`.

Không tạo model alive-check song song trong file khác. Nếu còn re-export legacy như `operations.models_alive_check`, phải lên kế hoạch loại bỏ.

### 4.4 Organization Scope

SSOT mục tiêu: `core.managers.OrganizationScopedManager` hoặc tên hiện tại `TenantAwareManager` nhưng chỉ định nghĩa một lần.

Rules:

- Không định nghĩa manager scope tổ chức trong nhiều app.
- Không nhận `tenant_id` tùy ý từ request.
- `SCMD_ORGANIZATION_ID` là single-org guard.
- Model không có scope trực tiếp phải document scope gián tiếp qua parent model.
- Dashboard và payroll query phải được rà soát scope.

### 4.5 Mobile Attendance API

SSOT interface: `operations.api_views` + application use cases liên quan attendance.

API contract tối thiểu:

- Authenticated user only.
- User chỉ check-in/check-out ca được phân công.
- Check-in phải validate ca, thời gian, trạng thái, GPS, ảnh nếu policy yêu cầu.
- Check-out phải validate đã check-in và chưa check-out.
- Mọi override/manual correction phải audit.

### 4.6 Payroll Calculation

SSOT: `accounting.application.payroll_use_cases.CalculatePayrollUseCase`.

Flow mục tiêu:

```text
ChamCong verified
  -> giờ làm thực tế
  -> đơn giá mục tiêu tại kỳ tính
  -> phụ cấp / tạm ứng / khấu trừ / vi phạm / đồng phục / bảo hiểm
  -> ChiTietLuong
  -> BangLuongThang
  -> review
  -> lock
  -> paid
```

Rules:

- Không tính lương từ nhập tay rời rạc nếu đã có dữ liệu vận hành.
- Kỳ lương locked/paid không sửa trực tiếp.
- Tính lại lương phải có reconciliation note nếu làm đổi thực lãnh.

### 4.7 Incident Identity

SSOT: `operations.models.BaoCaoSuCo.ma_su_co`.

Rules:

- `ma_su_co` generate ở model-level hoặc service SSOT.
- Không generate mã sự cố trong template/view tùy tiện.
- Mã sự cố không đổi sau khi tạo.

---

## 5. Core Data Flow

### 5.1 Business Flow

```text
KhachHangTiemNang
  -> HopDong
  -> MucTieu
  -> ViTriChot
  -> PhanCongCaTruc
  -> ChamCong
  -> BaoCaoSuCo / KiemTraQuanSo / Alive Check
  -> Payroll / Inventory / Inspection / Dashboard
```

### 5.2 Attendance Flow

```text
User authenticated
  -> load assigned shift
  -> validate ownership/role
  -> validate shift window
  -> validate GPS/geofence
  -> validate photo/device policy
  -> create/update ChamCong
  -> audit
  -> notify/realtime update if needed
```

Failure cases phải trả lỗi rõ:

- không có phân công,
- sai người,
- ngoài khung giờ,
- ngoài bán kính GPS,
- thiếu ảnh nếu bắt buộc,
- đã check-in/check-out trước đó,
- ca đã khóa payroll.

### 5.3 Payroll Flow

```text
Payroll period opened
  -> collect verified attendance
  -> calculate base salary
  -> apply allowances
  -> apply advances/deductions/violations/uniform compensation
  -> create draft payroll
  -> review/reconcile
  -> lock
  -> paid
```

Required audit:

- calculate/recalculate,
- manual adjustment,
- lock/unlock,
- paid marking,
- export payroll.

### 5.4 Incident Flow

```text
OPEN -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> CLOSED
```

Reopen path:

```text
CLOSED -> REOPENED -> IN_PROGRESS
```

Rules:

- Reopen phải có reason.
- Incident liên quan đền bù/khấu trừ phải trace sang payroll/accounting.
- Incident export phải audit nếu chứa dữ liệu nhạy cảm.

---

## 6. Interface Contracts

### 6.1 Admin Shell `/admin/`

Role: technical console.

Mục đích:

- data administration,
- configuration,
- audit review,
- worker/system health,
- emergency technical correction.

Rules:

- Không dùng `/admin/` làm business dashboard chính.
- Sửa dữ liệu nghiệp vụ nhạy cảm qua admin vẫn phải audit.
- Admin UI phải dùng brand SCMD, không dùng war-room/cyber language. Admin là console kỹ thuật, không phải trung tâm trình diễn marketing.

### 6.2 Dashboard `/dashboard/`

Role: business operations cockpit.

Dashboard phải thể hiện:

- tổng quan nhân sự,
- trạng thái mục tiêu,
- ca trực hôm nay,
- check-in/check-out,
- sự cố mở,
- cảnh báo quân số,
- kho/vật tư đáng chú ý,
- dữ liệu lương/kỳ lương ở mức tổng quan.

Rules:

- KPI phải có source rõ.
- Query phải organization-scoped hoặc document single-org exception.
- Không hardcode số liệu demo vào dashboard production.
- Màu trạng thái phải mang meaning nghiệp vụ.

### 6.3 Authentication `/login/`

Rules:

- Không dùng `cdn.tailwindcss.com`.
- Không dùng brand cũ `Sentinel`, `Security Command`, `War Room`.
- Login là cổng vào ERP nội bộ, không phải marketing/cyber landing page.
- Copy phải rõ, tiếng Việt chuẩn UTF-8.

### 6.4 Print / Export

Rules:

- Export chứa lương/GPS/ảnh/nhân sự/sự cố phải kiểm tra permission.
- Export phải audit.
- Export nhạy cảm nên có password hoặc cơ chế bảo vệ tương đương.
- Print template không dùng Tailwind CDN production nếu có thể build local hoặc inline CSS kiểm soát.

---

## 7. Celery Tasks

Tasks nên là orchestration mỏng, gọi application/domain services thay vì nhân bản logic.

Nhóm task chính:

| Nhóm | Ví dụ |
|---|---|
| Notifications | gửi thông báo, push, email |
| Alive check | kiểm tra quân số định kỳ, cảnh báo thiếu check-in |
| Payroll | tính/làm mới dữ liệu tổng hợp nếu có schedule |
| Reports | tạo báo cáo/export nền |
| Worker health | heartbeat, monitor |
| Cleanup | dọn session, file tạm, log tạm theo policy |

Rules:

- Task phải idempotent nếu có thể.
- Task lặp định kỳ không được tạo duplicate effect.
- Task liên quan payroll/attendance phải audit hoặc ghi job log.
- Task failure phải có retry/backoff hợp lý.

---

## 8. Environment Bootstrap

### 8.1 Local Admin

Credential mẫu chỉ dành cho local/dev. Production bắt buộc override.

```text
username: admin
email: admin@scmd.local
password: local/dev only
```

### 8.2 Local Bootstrap Path

```bash
python manage.py migrate
python manage.py create_scmd_structure
python manage.py seed_data
python manage.py createsuperuser
python manage.py runserver
```

Nếu dùng command bootstrap custom, command phải idempotent: chạy lại không tạo duplicate dữ liệu nền.

### 8.3 Docker Development

```bash
docker compose up --build
```

### 8.4 Docker Production

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Production rules:

- Không dùng default secret.
- Không tự chạy destructive migration.
- Phải có backup trước migration dữ liệu nhạy cảm.
- Phải có smoke test sau deploy.

### 8.5 GIS Configuration

Production nên dùng PostgreSQL + PostGIS cho GPS/geofence. SQLite chỉ phù hợp local/dev và không đại diện đầy đủ cho behavior geospatial production.

---

## 9. API Security

Minimum rules:

- Auth bắt buộc cho API nghiệp vụ.
- Object-level permission cho ca trực/chấm công/lương/sự cố.
- Không trả dữ liệu GPS/ảnh/lương nếu user không có quyền.
- Rate limit hoặc guard cho endpoint mobile nhạy cảm.
- SimpleJWT token lifetime phải phù hợp môi trường vận hành.
- Export/report endpoint phải audit.

Attendance API specific:

- Không tin `employee_id` từ client nếu có thể derive từ authenticated user.
- Không cho check-in hộ nếu không có role đặc biệt và audit.
- Không cho chỉnh GPS client-side sau khi gửi mà không có correction audit.

---

## 10. Testing Strategy

### 10.1 Test pyramid mục tiêu

| Loại test | Trọng tâm |
|---|---|
| Unit test | geofence, payroll formula, validators, state transition |
| Application test | check-in/check-out, payroll calculate/recalculate, incident lifecycle |
| Integration/API test | mobile attendance API, auth, permission failure |
| Regression test | payroll result, correction audit, locked period behavior |
| Smoke test | login, dashboard, admin, Celery worker, static files |

### 10.2 Test bắt buộc cho nghiệp vụ lõi

- Check-in đúng vị trí.
- Check-in ngoài bán kính GPS.
- Check-in sai người/sai ca.
- Check-out sau check-in hợp lệ.
- Alive check quá hạn.
- Sự cố mở/đóng/reopen.
- Tính lương từ giờ thực tế.
- Khấu trừ tạm ứng/vi phạm/đồng phục.
- Khóa kỳ lương và chặn sửa trực tiếp.
- Export dữ liệu nhạy cảm có permission + audit.

---

## 11. Migration Discipline

Migration production phải được xem là thao tác rủi ro cao nếu chạm vào attendance, payroll, incident, inventory.

Rules:

- Migration phải idempotent nếu là data migration.
- Trước migration production phải có backup.
- Migration thay đổi payroll/attendance phải có reconciliation note.
- Không xóa field dữ liệu nhạy cảm trong cùng release với việc migrate sang field mới nếu chưa có verification.
- Rollback plan phải ghi rõ: rollback schema, rollback data hoặc forward-fix.

---

## 12. Verification Checklist

Trước khi merge/release:

```bash
python manage.py check
python manage.py test
python manage.py showmigrations --plan
find static/ -name "*.py"
find . -path "*/templates/*" -name "*.py"
grep -R "cdn.tailwindcss.com" -n .
grep -R "SCMD Pro\|Security Command System\|Sentinel Command\|War Room\|Tactical" -n templates static dashboard main users operations accounting clients
grep -R "from .* import \*" -n */application/*.py
```

Manual QA:

- Login hiển thị SCMD, không còn brand cũ.
- Dashboard load được KPI thật.
- Admin title/copy đúng Technical Console.
- Chấm công mobile/API hoạt động.
- Export nhạy cảm yêu cầu quyền phù hợp.
- Worker heartbeat/task queue ổn.

---

## 13. Strategic Boundaries

Không triển khai các hướng sau trước khi hoàn tất hardening trong `WHITEPAPER.md`:

- multi-tenant SaaS thật,
- microservices/service split,
- event choreography phức tạp,
- data warehouse/BI tách riêng,
- rewrite frontend sang SPA chỉ vì thẩm mỹ,
- thêm brand surface mới ngoài SCMD.

Ưu tiên trước mắt:

1. P0 security/layout cleanup.
2. Application layer hardening.
3. Organization scope SSOT.
4. Attendance/payroll reconciliation.
5. UI/brand cleanup.
6. Test/release governance.
## 3.3.1 Static exposure rule

- WhiteNoise is active in middleware and serves the static contract rooted at `STATICFILES_DIRS = [BASE_DIR / "static"]` with output under `STATIC_ROOT = BASE_DIR / "staticfiles"`.
- Any `.py` file under `static/` is publicly exposable once collected and must be treated as a release-blocking defect.
- Any application-layer Python module under a `templates/` path is an architecture violation even if it is not served by WhiteNoise.
- Cleanup for misplaced static source must include the already-collected artifact under `staticfiles/`.
- Local verification must fail if `.py` files are detected under `static/` or `templates/`.

## 3.3.2 Cleanup milestone

- Shared organization-scope manager SSOT: `core.managers.TenantAwareManager`.
- Duplicate manager definitions removed from `clients`, `operations`, and `accounting` runtime model modules.
- Wildcard-only facades removed from active `application/` modules; application imports now resolve to real use-case implementations.
- Legacy root use-case modules are compatibility wrappers only and should be removed after the import transition is complete.
- UTF-8 cleanup in this patch is intentionally scoped to runtime/admin/application files with the highest operational value.
