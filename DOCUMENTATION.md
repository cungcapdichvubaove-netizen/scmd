# DOCUMENTATION.md — SCMD Pro Technical Reference

Status: **Technical reference for implementation**
Version: 3.5.0
<<<<<<< HEAD
Updated: 2026-06-12

Tài liệu này mô tả kỹ thuật triển khai sản phẩm SCMD Pro thuộc thương hiệu/công ty SCMD. `WHITEPAPER.md` là contract chiến lược/kiến trúc; file này là reference để developer, operator và reviewer kiểm tra code, runtime, module map, flow nghiệp vụ và deployment.

Documentation map:
- `README.md`: overview, module map, operator/developer orientation
- `WHITEPAPER.md`: strategic product/architecture contract
- `DOCUMENTATION.md`: current technical reference and implementation contract
- `UI_SYSTEM_REFACTOR_SPEC.md`: UI/brand/runtime surface governance
- `cursorrules.md` and `.cursorrules`: AI/tooling compatibility rules, subordinate to the documents above
- `CHANGELOG.md`, release reports, patch notes, and hardening reports: historical records, not current source-of-truth contracts unless explicitly promoted here

=======
Updated: 2026-06-03

Tài liệu này mô tả kỹ thuật triển khai sản phẩm SCMD Pro thuộc thương hiệu/công ty SCMD. `WHITEPAPER.md` là contract chiến lược/kiến trúc; file này là reference để developer, operator và reviewer kiểm tra code, runtime, module map, flow nghiệp vụ và deployment.

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
Patch note 3.5.0:
- Chuẩn hóa kiến trúc thương hiệu: **SCMD** là công ty/thương hiệu mẹ; **SCMD Pro** là sản phẩm phần mềm thương mại.
- Tagline sản phẩm chính thức: **Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp**.
- `ERP` chỉ còn là nhóm năng lực quản trị nội bộ trong SCMD Pro, không phải tên brand user-facing.
- Public auth templates phải chạy trên local Tailwind build và `static/common/css/brand_system.css`, không dùng Tailwind CDN runtime.
- Regression coverage tối thiểu hiện bao gồm attendance application use cases (`CheckInUseCase`, `CheckOutUseCase`, `CalculateWorkHoursUseCase`) và payroll audit use case (`AuditPayrollUseCase`).
<<<<<<< HEAD
- Business workflow A→F đã chuẩn hóa các hồ sơ nguồn có vòng đời riêng: HĐLĐ, nghỉ phép, đổi ca, payroll reconciliation, thanh toán khách hàng/công nợ, thu hồi tài sản/offboarding inventory. Xem `docs/BUSINESS_WORKFLOW_A_TO_F_SYSTEM_CONTRACT.md`.
- AI rules path contract: canonical Markdown source là `cursorrules.md`; file `.cursorrules` chỉ là compatibility mirror cho Cursor; không dùng path `.cursorrules/cursorrules.md`.
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

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
<<<<<<< HEAD
| `users` | Nhân sự | `NhanVien`, `ChucDanh`, `PhongBan`, `NhanVienRegionAssignment`, `HopDongLaoDong`, `PhuLucHopDongLaoDong`, `DonNghiPhep`, `QuyetDinhNghiViec`, `OffboardingChecklist`, `HoSoBaoHiem` |
| `clients` | CRM/hợp đồng/mục tiêu/công nợ khách hàng | `KhachHangTiemNang`, `HopDong`, `MucTieu`, `PhuLucHopDongDichVu`, `BienBanNghiemThu`, `HoaDon`, `CongNo`, `ThanhToanKhachHang`, `PhanBoThanhToanHoaDon` |
| `operations` | Vận hành hiện trường | `PhanCongCaTruc`, `ChamCong`, `BaoCaoSuCo`, `KiemTraQuanSo`, `ShiftChangeRequest` |
| `accounting` | Lương, phụ cấp, tạm ứng, khấu trừ, sổ quỹ | `BangLuongThang`, `ChiTietLuong`, `PayrollAdjustment`, `TamUngLuong`, `KhoanKhauTruNhanVien`, `CauHinhLuong`, `SoQuy` |
| `inventory` | Kho vật tư/đồng phục/thu hồi tài sản | `VatTu`, `PhieuNhap`, `PhieuXuat`, `PhieuThuHoi`, `ChiTietPhieuThuHoi`, `BienBanMatHongVatTu`, `InventoryLedgerEntry` |
=======
| `users` | Nhân sự | `NhanVien`, `ChucDanh`, `PhongBan` |
| `clients` | CRM/hợp đồng/mục tiêu | `KhachHangTiemNang`, `HopDong`, `MucTieu` |
| `operations` | Vận hành hiện trường | `PhanCongCaTruc`, `ChamCong`, `BaoCaoSuCo`, `KiemTraQuanSo` |
| `accounting` | Lương, phụ cấp, khấu trừ, sổ quỹ | `BangLuongThang`, `ChiTietLuong`, `CauHinhLuong`, `SoQuy` |
| `inventory` | Kho vật tư/đồng phục | `VatTu`, `PhieuNhap`, `PhieuXuat` |
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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

<<<<<<< HEAD
### 4.2 Company Information

SSOT: `main.models.CompanyInfo`.

Rules:

- Thông tin pháp lý/liên hệ công ty dùng trên bảng lương, lý lịch trích ngang, hợp đồng, phiếu kho và báo cáo phải lấy từ `CompanyInfo`, không hard-code trong template/export service.
- `CompanyInfo` là singleton theo `tenant_id`; DB constraint `uq_companyinfo_one_per_org` cưỡng chế mỗi organization chỉ có một hồ sơ công ty.
- Admin chỉ cho thêm hồ sơ khi organization hiện tại chưa có hồ sơ.
- Template có thể dùng `COMPANY` hoặc `COMPANY_INFO` do `main.context_processors.company_info` cung cấp. Context processor chỉ load profile một lần và helper dùng cache ngắn hạn, invalidate khi `CompanyInfo` được lưu/xóa.
- Mẫu biểu có logo phải ưu tiên `COMPANY.logo`/`COMPANY_INFO.logo_url` hoặc `logo_path`, fallback về brand logo tĩnh nếu chưa upload logo công ty. Export service không có request phải gọi `main.company_info.get_company_report_context()`.

### 4.3 Worker Health
=======
### 4.2 Worker Health
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

SSOT: `main.models.WorkerHeartbeat`.

Worker heartbeat dùng để theo dõi Celery/worker runtime. Dashboard/system health không được tự tạo cơ chế heartbeat riêng nếu chưa có lý do kiến trúc.

<<<<<<< HEAD
### 4.4 Alive Check
=======
### 4.3 Alive Check
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

SSOT: `operations.models.KiemTraQuanSo`.

Không tạo model alive-check song song trong file khác. Nếu còn re-export legacy như `operations.models_alive_check`, phải lên kế hoạch loại bỏ.

<<<<<<< HEAD
Alive check policy/runtime:

- Phản hồi alive check phải kiểm tra đúng ownership của user với `ca_truc.nhan_vien.user_id`.
- Response path phải khóa row `KiemTraQuanSo` bằng `select_for_update()` để tránh race với task quá hạn.
- `ALIVE_CHECK_REQUIRE_SELFIE` là default policy cho yêu cầu ảnh xác thực; mặc định `False` để tránh breaking change nghiệp vụ hiện tại.
- `device_id` nên được lưu ở field riêng để phục vụ audit/reconciliation; không nên chỉ nhét trong chuỗi tọa độ xác thực.

### 4.5 Organization Scope
=======
### 4.4 Organization Scope
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

SSOT mục tiêu: `core.managers.OrganizationScopedManager` hoặc tên hiện tại `TenantAwareManager` nhưng chỉ định nghĩa một lần.

Rules:

- Không định nghĩa manager scope tổ chức trong nhiều app.
- Không nhận `tenant_id` tùy ý từ request.
- `SCMD_ORGANIZATION_ID` là single-org guard.
- Model không có scope trực tiếp phải document scope gián tiếp qua parent model.
- Dashboard và payroll query phải được rà soát scope.

<<<<<<< HEAD
### 4.6 Mobile Attendance API
=======
### 4.5 Mobile Attendance API
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

SSOT interface: `operations.api_views` + application use cases liên quan attendance.

API contract tối thiểu:

- Authenticated user only.
- User chỉ check-in/check-out ca được phân công.
- Check-in phải validate ca, thời gian, trạng thái, GPS, ảnh nếu policy yêu cầu.
- Check-out phải validate đã check-in và chưa check-out.
- Mọi override/manual correction phải audit.

<<<<<<< HEAD
### 4.7 Payroll Calculation
=======
### 4.6 Payroll Calculation
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

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
<<<<<<< HEAD
- Đơn giá mục tiêu phải được resolve theo `ngày trực` khi tồn tại lịch sử đơn giá effective-dated; không được dùng một đơn giá duy nhất cho cả tháng trong case hồi tố.
- Lịch sử đơn giá payroll của mục tiêu dùng SSOT `clients.MucTieuDonGiaHistory`; mỗi record mang `ngày hiệu lực`, `lương khoán bảo vệ`, `số giờ một ngày`.
- Snapshot attendance trong `ChiTietLuong.nguon_du_lieu_snapshot` phải lưu thêm `don_gia_hieu_luc_tu`, `nguon_don_gia`, `rate_record_id` khi có để phục vụ audit/reconciliation.
- Nếu có lịch sử đơn giá nhưng không có baseline hiệu lực trước ngày trực đang tính, use case phải fail fast bằng lỗi cấu hình payroll thay vì tự fallback về cấu hình hiện tại.
- Kỳ lương locked/paid không sửa trực tiếp.
- Tính lại lương phải có reconciliation note nếu làm đổi thực lãnh.

### 4.8 Incident Identity
=======
- Kỳ lương locked/paid không sửa trực tiếp.
- Tính lại lương phải có reconciliation note nếu làm đổi thực lãnh.

### 4.7 Incident Identity
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

SSOT: `operations.models.BaoCaoSuCo.ma_su_co`.

Rules:

- `ma_su_co` generate ở model-level hoặc service SSOT.
- Không generate mã sự cố trong template/view tùy tiện.
- Mã sự cố không đổi sau khi tạo.

<<<<<<< HEAD

### 4.8.1 Incident status language contract

The incident lifecycle SSOT uses stable status codes in `operations.models.BaoCaoSuCo`
and `operations.application.incident_transition_policy.IncidentTransitionPolicy`.
UI copy may include icons or richer Vietnamese wording, but the code values below
are the authoritative contract for business rules, tests, APIs and reconciliation.

| Code / contract key | Vietnamese display contract | English meaning |
|---|---|---|
| `CHO_XU_LY` | `Chờ xử lý` | `Pending` / waiting for handling |
| `DANG_XU_LY` | `Đang xử lý` | `In progress` |
| `DA_XU_LY` | `Đã xử lý (Không đền bù)` | `Resolved without compensation` |
| `CHO_DEN_BU` | `Chờ đền bù (Có thiệt hại)` | `Waiting compensation` |
| `HOAN_TAT` | `Hoàn tất xử lý` | `Closed` / fully completed |
| `HUY` | `Đã hủy bỏ` | `Cancelled` |

Lifecycle contract notes:

- Closed incident set = `HOAN_TAT`, `HUY`.
- Reopen target status = `DANG_XU_LY`.
- Do not confuse UI wording such as `Hoàn tất xử lý` with a generic `RESOLVED`; in the current contract the closed terminal state is `HOAN_TAT`.
- If an English-facing integration is added later, keep the stable Vietnamese code keys above and map them explicitly instead of renaming database values ad hoc.
- Authoritative incident lifecycle details are maintained in `docs/INCIDENT_LIFECYCLE_CONTRACT.md`. Legacy labels embedded in old migrations are historical records, not a competing state-machine contract.


### 4.9 Business Workflow A→F SSOTs

Authoritative contract: `docs/BUSINESS_WORKFLOW_A_TO_F_SYSTEM_CONTRACT.md`.

| Nghiệp vụ | SSOT/source records | Không còn được dùng làm SSOT |
|---|---|---|
| Hợp đồng lao động | `users.HopDongLaoDong`, `users.PhuLucHopDongLaoDong` | `NhanVien.loai_hop_dong` |
| Nghỉ phép | `users.DonNghiPhep` | generic proposal/free-text report |
| Đổi ca/tăng ca/hủy ca | `operations.ShiftChangeRequest` | `BaoCaoDeXuat`, constant legacy `DOI_CA` / `DA_XU_LY` |
| Nghỉ việc/offboarding | `users.QuyetDinhNghiViec`, `users.OffboardingChecklist` | checkbox boolean đơn lẻ |
| Bảo hiểm bắt buộc | `users.HoSoBaoHiem` với `BHXH ACTIVE` | `BAO_HIEM_KHAC` hoặc field nhân viên rời |
| Tạm ứng/khấu trừ payroll | `accounting.TamUngLuong`, `accounting.KhoanKhauTruNhanVien` | nhập tay trực tiếp vào chi tiết lương |
| Công nợ/thanh toán khách hàng | `clients.ThanhToanKhachHang`, `clients.PhanBoThanhToanHoaDon`, `HoaDon`, `CongNo` | sửa tay `CongNo.so_tien_da_thu` |
| Thu hồi tài sản offboarding | `inventory.PhieuThuHoi`, `ChiTietPhieuThuHoi`, `BienBanMatHongVatTu` | `OffboardingChecklist` boolean, fake `PhieuNhap` |

Rules:

- Record có vòng đời riêng phải có trạng thái, ngày hiệu lực/ngày phát sinh, người thực hiện/duyệt nếu có, file/bằng chứng nếu cần, audit trail và dashboard cảnh báo nếu tác động vận hành.
- Trạng thái phải đi qua transition policy/use case; production code không set `.trang_thai = ...` trực tiếp ngoài vùng được whitelist bởi regression test.
- Các flow tài chính/kho sau khi phát sinh downstream effect phải append-only; correction phải dùng reversal/adjustment record ở phase sau, không edit/delete âm thầm.

### 4.10 UI Tokens

SSOT: `theme/tailwind.config.js`.

Rules:
- Tất cả màu sắc, font, spacing, breakpoint phải được định nghĩa trong `theme/tailwind.config.js`.
- `static/common/css/brand_system.css` phải tiêu thụ hoặc phản ánh các giá trị từ `tailwind.config.js` thông qua CSS variables.
- Không định nghĩa token màu sắc cục bộ trong các template (ví dụ: `--hr-navy` trong `dashboard_hr.html`).
- Không hardcode giá trị màu sắc trong CSS hoặc template nếu đã có token tương ứng.

### 4.11 Access Scope & Operational Authorization

SSOT contract: `docs/access_scope/ACCESS_SCOPE_AUTHORIZATION_CONTRACT.md`.

Supporting documents:

- `docs/access_scope/ACCESS_SCOPE_IMPLEMENTATION_ROADMAP.md`
- `docs/access_scope/ACCESS_SCOPE_TEST_MATRIX.md`
- `docs/access_scope/VIBE_CODING_ACCESS_SCOPE_PLAYBOOK.md`
- `docs/GLOSSARY.md`

Models to introduce during Phase 1 hardening:

| Model | Authoritative module | Purpose |
|---|---|---|
| `AccessDelegation` | Planned `delegation.models` app | Target model only; chưa được triển khai trong bản hiện tại nên không được claim là deployed |
| `NhanVienRegionAssignment` | `users.models_assignment` | SSOT hiện tại cho historical/multi-region staff scope; không có `NhanVienSiteAssignment` trong bản hiện tại |
| `PayrollAdjustment` | `accounting` | Retroactive salary adjustment after payroll lock/paid status |

Rules:

- RBAC/role name is insufficient for sensitive workflows. Querysets must be scoped by object-level access policy.
- `tenant_id` is legacy organization-scope naming and must resolve to `SCMD_ORGANIZATION_ID`; it is not SaaS tenant context.
- Historical checks for attendance/payroll/incidents must use event-time scope. Overnight shifts use the local date of `shift.start_at` as canonical `work_date` unless the shift is explicitly split.
- Temporary delegation must be modeled explicitly; do not implement it via shared passwords, temporary superuser status, or permanent role escalation.
- Denied actions must return contextual `PolicyResult` with stable error code and user-friendly business message.

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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

<<<<<<< HEAD
Attendance window policy runtime:

- `ATTENDANCE_CHECKIN_EARLY_MINUTES`: số phút cho phép check-in sớm trước giờ bắt đầu ca.
- `ATTENDANCE_CHECKIN_LATE_MINUTES`: số phút grace sau giờ kết thúc ca.
- Check-in hợp lệ trong khoảng `start_at - early_minutes` đến `end_at + late_minutes`.
- Với giá trị mặc định `ATTENDANCE_CHECKIN_LATE_MINUTES = 0`, nhân viên vẫn được check-in đến đúng giờ kết thúc ca. Đây là policy chủ đích cho vận hành ca thực tế, không phải bug.
- `ATTENDANCE_CHECKOUT_EARLY_MINUTES` và `ATTENDANCE_CHECKOUT_LATE_MINUTES` điều khiển cửa sổ check-out tương ứng.
- `ATTENDANCE_REQUIRE_IMAGE_CHECKIN` và `ATTENDANCE_REQUIRE_IMAGE_CHECKOUT` là default policy; ca/vị trí/mục tiêu có thể override nếu model có cờ riêng.

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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
<<<<<<< HEAD
- Lifecycle guard đã được enforce ở `operations.application.incident_transition_policy.IncidentTransitionPolicy` và `operations.admin.BaoCaoSuCoAdminForm`; closed incident không được sửa trực tiếp nội dung chính nếu chưa reopen hợp lệ.
- Incident liên quan đền bù/khấu trừ phải trace sang payroll/accounting.
- Incident export phải audit nếu chứa dữ liệu nhạy cảm.


### 5.5 Business Workflow A→F Flow

```text
NhanVien
  -> HopDongLaoDong / HoSoBaoHiem / DonNghiPhep / QuyetDinhNghiViec
  -> ShiftChangeRequest / PhanCongCaTruc / ChamCong
  -> PayrollSourceReconciliationUseCase
  -> BangLuongThang review -> LOCKED/PAID
```

```text
KhachHang / HopDong
  -> BienBanNghiemThu / HoaDon / CongNo
  -> ThanhToanKhachHang
  -> PhanBoThanhToanHoaDon
  -> RecalculateReceivableStatusUseCase
```

```text
PhieuXuat / ChiTietPhieuXuat
  -> PhieuThuHoi / ChiTietPhieuThuHoi
  -> InventoryLedgerEntry
  -> BienBanMatHongVatTu
  -> KhoanKhauTruNhanVien PENDING_APPROVAL
```

These flows are operational source-of-truth paths. Do not replace them with generic proposals, manually edited result fields, or fake inventory/payroll documents.

=======
- Incident liên quan đền bù/khấu trừ phải trace sang payroll/accounting.
- Incident export phải audit nếu chứa dữ liệu nhạy cảm.

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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
<<<<<<< HEAD
- Quyền truy cập dashboard phải đi qua `main.dashboard_router.DashboardRouter` và decorator `dashboard_access_required()`; không tự rải role/group checks ở từng dashboard view nếu có thể dùng policy tập trung.
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

### 6.3 Authentication `/login/`

Rules:

<<<<<<< HEAD
- Không dùng `Tailwind CDN`.
- Không dùng brand/copy cũ kiểu cyber-console; chỉ dùng SCMD Pro và ngôn ngữ vận hành nghiệp vụ.
=======
- Không dùng `cdn.tailwindcss.com`.
- Không dùng brand cũ `Sentinel`, `Security Command`, `War Room`.
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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

<<<<<<< HEAD
Production/demo Docker rules:
=======
Production rules:
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

- Không dùng default secret.
- Không tự chạy destructive migration.
- Phải có backup trước migration dữ liệu nhạy cảm.
- Phải có smoke test sau deploy.
<<<<<<< HEAD
- Compose production/demo phải dùng PostGIS thật: `DATABASE_URL=postgis://<SQL_USER>:<SQL_PASSWORD>@db:5432/<SQL_DATABASE>`.
- Compose production/demo phải dùng Redis service host: `REDIS_URL=redis://redis:6379/0`.
- SQLite chỉ được phép cho local development có chủ đích; `docker-compose.prod.yml` sẽ fail-fast nếu thiếu `DATABASE_URL`, dùng SQLite, hoặc trỏ DB/Redis về `localhost`.
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

### 8.5 GIS Configuration

Production nên dùng PostgreSQL + PostGIS cho GPS/geofence. SQLite chỉ phù hợp local/dev và không đại diện đầy đủ cho behavior geospatial production.

---

## 9. API Security

Minimum rules:

- Auth bắt buộc cho API nghiệp vụ.
- Object-level permission cho ca trực/chấm công/lương/sự cố.
- Không trả dữ liệu GPS/ảnh/lương nếu user không có quyền.
- Rate limit hoặc guard cho endpoint mobile nhạy cảm.
<<<<<<< HEAD
- Explicit CORS Origins (Rule 12.4) bắt buộc cấu hình cho các domain tin cậy.
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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

<<<<<<< HEAD
### 11.1 Chiến lược xử lý Mojibake (Encoding)

Tuân thủ chiến lược **Forward-fix** để bảo vệ tính toàn vẹn của production:
1. **Không sửa lịch sử**: Cấm thay đổi nội dung các file `.py` trong `migrations/` đã được merge vào `main` hoặc đã deploy (tránh sai lệch mã băm history).
2. **Sửa tại gốc (Models)**: Chỉnh sửa các chuỗi ký tự tiếng Việt bị lỗi trong `models.py` (`verbose_name`, `help_text`) và chạy `makemigrations` để tạo file mới ghi nhận thay đổi metadata.
3. **Data Correction**: Với dữ liệu seed hoặc dữ liệu nghiệp vụ bị lỗi encoding trong DB, sử dụng migration `RunPython` để thực hiện lệnh `UPDATE` sửa lỗi trên các bản ghi cụ thể.
4. **Enforcement**: Đảm bảo IDE/Editor luôn lưu file ở định dạng **UTF-8 (No BOM)**. Kiểm tra bằng lệnh `file -i` trước khi commit.

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
---

## 12. Verification Checklist

<<<<<<< HEAD
See also: `RELEASE_CHECKLIST.md` for the standalone pre-merge/release checklist that can be copied into CI or PR templates.


=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
Trước khi merge/release:

```bash
python manage.py check
python manage.py test
python manage.py showmigrations --plan
find static/ -name "*.py"
find . -path "*/templates/*" -name "*.py"
<<<<<<< HEAD
grep -R "Tailwind CDN" -n .
grep -RInE "War Room|WarRoom|Sentinel|Tactical|Cyber|SCMD ERP|ESP" -n templates static main dashboard users operations accounting clients
=======
grep -R "cdn.tailwindcss.com" -n .
grep -R "SCMD Pro\|Security Command System\|Sentinel Command\|War Room\|Tactical" -n templates static dashboard main users operations accounting clients
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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
<<<<<<< HEAD


## Dashboard/admin language hardening

- Dashboard UI text follows `docs/CAPITALIZATION_GUIDELINE.md`: Vietnamese labels use sentence case by default; uppercase is limited to technical abbreviations or short semantic markers.
- Owned JS/CSS asset names and comments must not reintroduce legacy `War Room`/`Cyber` naming.
- `/admin/` is localized as `Quản trị kỹ thuật SCMD` / `Bảng quản trị kỹ thuật`; technical runtime terms may remain in English when listed as exceptions in `docs/ADMIN_LOCALIZATION_AUDIT.md`.

## 3.5.4 Release contract hardening note

- Release verification now fails fast when Python source files are detected under `static/`, `staticfiles/`, or any Django `templates/` path.
- Release verification now fails fast when any active `*/application/*.py` module uses wildcard imports, including `from .models import *`.
- Organization-scope manager definitions remain centralized in `core.managers.TenantAwareManager`; domain apps such as `clients`, `operations`, and `accounting` must import the shared manager instead of redefining it.


## Access Scope companion contracts

Phase 1 hardening uses these standalone contracts:

- `docs/access_scope/ACCESS_SCOPE_AUTHORIZATION_CONTRACT.md`
- `docs/access_scope/ADMIN_AUTHORIZATION_CONTRACT.md`
- `docs/access_scope/ACCESS_SCOPE_MIGRATION_BACKFILL_PLAN.md`
- `docs/access_scope/SENSITIVE_DATA_EXPORT_CONTRACT.md`
- `docs/access_scope/ACCESS_SCOPE_DECISION_RECORD.md`
- `RELEASE_CHECKLIST.md`
- `UI_SYSTEM_REFACTOR_SPEC.md`

These files must be read before modifying staff visibility, site visibility, scheduling, dispatch, admin actions, imports, sensitive exports, payroll adjustments or migration/backfill logic.
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
