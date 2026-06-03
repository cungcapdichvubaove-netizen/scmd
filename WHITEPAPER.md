# WHITEPAPER.md — SCMD Pro Architecture & Product Contract

Version: 3.5.0
Release date: 2026-06-03
Status: **Authoritative target contract**

Tài liệu này là contract chiến lược và kiến trúc mục tiêu cho SCMD/SCMD Pro. Khi code và tài liệu lệch nhau, đội phát triển phải xử lý bằng một trong hai cách: sửa code để tuân thủ contract, hoặc cập nhật contract bằng quyết định có lý do, changelog và owner chịu trách nhiệm.

Patch note 3.5.0:
- Chuẩn hóa kiến trúc thương hiệu mới: **SCMD** là công ty/thương hiệu mẹ; **SCMD Pro** là sản phẩm phần mềm thương mại bán cho doanh nghiệp dịch vụ bảo vệ.
- Dòng định vị sản phẩm chính thức: **SCMD Pro — Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp**.
- `ERP` không còn là tên thương hiệu chính; chỉ được dùng như năng lực/chức năng quản trị doanh nghiệp bên trong SCMD Pro.
- Public authentication surfaces (`homepage.html`, `login.html`) phải dùng local Tailwind build qua `{% tailwind_css %}` và brand tokens của SCMD Pro; không được nạp `cdn.tailwindcss.com`.
- Attendance và payroll application use cases phải có regression coverage tối thiểu cho các nhánh integrity quan trọng của check-in/check-out và payroll audit.

---

## 1. Định vị hệ thống

**SCMD** là công ty/thương hiệu mẹ, viết tắt từ **Security Commander**.

**SCMD Pro** là sản phẩm phần mềm thương mại chính do SCMD cung cấp cho doanh nghiệp dịch vụ bảo vệ.

**Định vị công ty:** SCMD — Công ty công nghệ phần mềm cho ngành dịch vụ bảo vệ.

**Định vị sản phẩm:** SCMD Pro — Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp.

SCMD Pro là nền tảng chỉ huy và quản trị chuyên biệt cho doanh nghiệp kinh doanh dịch vụ bảo vệ. Giá trị lõi không phải số lượng màn hình, mà là khả năng tạo ra **operational truth** — dữ liệu vận hành có thể tin cậy để điều phối, kiểm soát, đối soát và tính lương.

Hệ thống phải trả lời được các câu hỏi cốt lõi:

- Ai đang trực, trực ở đâu, ca nào, chốt nào?
- Check-in/check-out có hợp lệ không?
- Mục tiêu nào thiếu quân số, có ca trống, có sự cố mở?
- Dữ liệu nào sẽ ảnh hưởng lương, khấu trừ, tạm ứng, đồng phục, đền bù?
- Kho còn đủ vật tư/đồng phục cho vận hành không?
- Quản lý có thể đối soát dữ liệu và khóa kỳ lương minh bạch không?

SCMD Pro hiện phục vụ **một tổ chức duy nhất**. Multi-tenant thật sự không nằm trong roadmap hiện tại. Tất cả cơ chế `tenant_id` trong code hiện tại phải được hiểu là **single-organization guard / organization scope legacy naming**, không phải tenant động theo request, domain, subdomain hoặc khách hàng SaaS.

---

## 2. Nguyên tắc chiến lược

1. **Ổn định monolith trước khi mở rộng.** Không tách service, không event choreography, không multi-tenant thật khi boundary trong monolith còn lệch.
2. **Một nguồn sự thật cho mỗi subsystem.** Không tạo duplicate model, duplicate manager, duplicate use case hoặc duplicate identity generator.
3. **Operational truth thắng UI trình diễn.** Dashboard phải phản ánh dữ liệu nghiệp vụ thật, không ưu tiên hiệu ứng, màu mè hoặc ngôn ngữ war-room.
4. **Dữ liệu lương/chấm công/sự cố là dữ liệu kiểm toán.** Mọi sửa đổi nhạy cảm phải có audit trail và cơ chế đối soát.
5. **Deploy phải deterministic.** Bootstrap, migration, static build, environment và credential phải rõ ràng, lặp lại được.
6. **Contract phải enforce được.** Tài liệu không chỉ mô tả ý tưởng; mỗi contract phải có checklist, grep, test hoặc acceptance criteria.

---

## 3. Kiến trúc chính thức: Layered Monolith

Kể từ dòng 3.x, kiến trúc chính thức là **layered monolith**. Quyết định này thay thế các tuyên bố cũ về “strict clean architecture”. Với Django ERP nội bộ, layered monolith là lựa chọn phù hợp hơn vì dễ debug, dễ deploy, dễ refactor theo nghiệp vụ và phù hợp với team nhỏ/vừa.

```text
Interface Layer       Django views, DRF endpoints, serializers, templates, WebSocket consumers
Application Layer     Use case classes, transaction boundary, orchestration logic
Domain Helpers        Pure Python rules: geofence, payroll formulas, validators, state transition checks
Infrastructure Layer  Django ORM, Celery, Redis, Channels, storage, SMTP, external integrations
```

### 3.1 Quy tắc ranh giới

- Interface Layer chỉ nhận request, gọi use case, định dạng response.
- Application Layer điều phối business flow và chịu trách nhiệm transaction boundary.
- Domain Helpers chứa logic thuần, dễ test, không phụ thuộc HTTP, template hoặc Celery.
- Infrastructure Layer chứa ORM, task runner, storage, queue, email, push notification.
- Model method chỉ nên chứa invariant gần dữ liệu; orchestration nhiều bước phải nằm ở application layer.
- Không tạo parallel model definitions hoặc duplicate source of truth.

### 3.2 Application Layer Contract

Application layer hiện có nợ kỹ thuật: một số file trong `*/application/` chỉ là wildcard re-export facade.

Ví dụ sai:

```python
from operations.attendance_use_cases import *  # noqa
```

Contract bắt buộc:

- Mỗi file `*/application/*.py` phải chứa class/function thực, có signature rõ ràng.
- Cấm `from module import *` trong application layer.
- Không giữ legacy root `*_use_cases.py` song song với application use case mới quá một release.
- Views/API/Celery task phải import từ application layer chính thức.
- Mọi use case quan trọng phải có test cho happy path, permission failure và data integrity failure.

Definition of Done:

- `grep -R "from .* import \*" -n */application/*.py` không còn hit trong file do team sở hữu.
- Không còn file application chỉ re-export.
- Import graph không vòng lặp.
- `python manage.py check` và test use case chính pass.

---

## 4. Technical SSOTs

| Subsystem | SSOT mục tiêu | Ghi chú |
|---|---|---|
| Audit Log | `main.models.AuditLog` | Legacy re-export phải bị loại bỏ theo roadmap |
| Worker Health | `main.models.WorkerHeartbeat` | Theo dõi worker/Celery/runtime health |
| Alive Check | `operations.models.KiemTraQuanSo` | Không tạo model alive-check song song |
| Attendance API | `operations.api_views` + application use cases | Mobile contract phải ổn định |
| Organization Scope | `core.managers.OrganizationScopedManager` hoặc tên hiện tại `TenantAwareManager` tập trung | `tenant_id` là legacy naming, không phải SaaS tenant |
| Payroll Calculation | `accounting.application.payroll_use_cases.CalculatePayrollUseCase` | Phải có reconciliation và lock policy |
| Incident Identity | `operations.models.BaoCaoSuCo.ma_su_co` | Model-level guard, không generate rải rác |
| Frontend Tokens | `static/common/css/brand_system.css` + `tailwind.config.js` | Không dùng CDN Tailwind production |
| UI Brand Language | `UI_SYSTEM_REFACTOR_SPEC.md` | SCMD là tên thương hiệu duy nhất trong user-facing UI |

---

## 5. Data flow cốt lõi

Chuỗi nghiệp vụ chính phải trace được trong code:

```text
Lead/Khách hàng
  -> Hợp đồng
  -> Mục tiêu bảo vệ
  -> Vị trí chốt
  -> Phân công ca trực
  -> Chấm công GPS/ảnh
  -> Sự cố / Kiểm tra quân số / Alive check
  -> Đối soát vận hành
  -> Bảng lương / Chi tiết lương / Khấu trừ
```

Các model trung tâm:

- `clients.MucTieu`: mục tiêu bảo vệ, tọa độ, bán kính GPS, định biên, đơn giá.
- `operations.PhanCongCaTruc`: phân công nhân viên vào ca/chốt/ngày.
- `operations.ChamCong`: check-in/check-out, GPS, ảnh, thiết bị, giờ thực tế.
- `operations.BaoCaoSuCo`: sự cố hiện trường, mức độ, trạng thái xử lý, thiệt hại.
- `operations.KiemTraQuanSo`: kiểm soát quân số/alive check.
- `accounting.ChiTietLuong`: hệ quả tài chính từ vận hành.

Quy tắc sản phẩm: SCMD là **operations-led security management platform**. Finance/payroll phải lấy dữ liệu từ vận hành đã đối soát, không nhập tay rời rạc như một finance-led ERP.

---

## 6. Data Integrity & Reconciliation Contract

Đây là phần bắt buộc vì SCMD xử lý dữ liệu có thể dẫn đến tranh chấp lương, trách nhiệm hiện trường và nghĩa vụ với khách hàng.

### 6.1 Attendance correction

- Không sửa âm thầm `ChamCong` đã dùng cho tính lương.
- Sửa chấm công phải có lý do, người sửa, thời điểm sửa, giá trị cũ, giá trị mới.
- Nếu sửa sau khi kỳ lương đã khóa, phải tạo adjustment record hoặc mở khóa có audit đặc biệt.
- GPS/photo/device metadata gốc phải được giữ nếu có thể.

### 6.2 Payroll reconciliation

- `ChiTietLuong` phải lưu đủ dữ liệu snapshot cần thiết để giải thích kết quả tại thời điểm tính: giờ công, đơn giá, phụ cấp, tạm ứng, khấu trừ, vi phạm, đồng phục, bảo hiểm, đền bù.
- Tính lại lương phải phân biệt rõ: recalculation draft, reviewed, locked, paid.
- Kỳ lương đã `LOCKED` hoặc `PAID` không được sửa trực tiếp nếu không có quyền đặc biệt và audit.
- Bất kỳ thay đổi nào làm đổi thực lãnh phải có reconciliation note.

### 6.3 Incident reconciliation

- Sự cố đã đóng không được sửa nội dung chính mà không có reopen/audit.
- Thiệt hại, đền bù hoặc khấu trừ liên quan sự cố phải trace được sang payroll/accounting.
- `ma_su_co` là identity bất biến sau khi tạo.

### 6.4 Inventory reconciliation

- Phiếu xuất/nhập đã xác nhận không được xóa vật lý nếu đã ảnh hưởng tồn kho.
- Điều chỉnh tồn kho phải có phiếu điều chỉnh hoặc audit record.
- Cấp phát đồng phục/vật tư cho nhân viên/mục tiêu phải trace được khi tính khấu trừ hoặc thu hồi.

---

## 7. State Machine mục tiêu

State machine không nhất thiết phải implement đầy đủ ngay trong một sprint, nhưng đây là contract nghiệp vụ mục tiêu.

### 7.1 Ca trực

```text
DRAFT -> ASSIGNED -> CHECKED_IN -> CHECKED_OUT -> VERIFIED -> PAYROLL_LOCKED
```

Không được chuyển ngược trạng thái nếu không có audit và quyền đặc biệt.

### 7.2 Sự cố

```text
OPEN -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> CLOSED
```

Ngoại lệ:

```text
CLOSED -> REOPENED -> IN_PROGRESS
```

Reopen phải có lý do.

### 7.3 Bảng lương

```text
DRAFT -> CALCULATED -> REVIEWED -> LOCKED -> PAID
```

- `LOCKED`: không sửa chi tiết trực tiếp.
- `PAID`: chỉ adjustment kỳ sau hoặc reversal có kiểm soát.

### 7.4 Phiếu kho

```text
DRAFT -> CONFIRMED -> POSTED -> VOIDED
```

`VOIDED` không xóa lịch sử; phải tạo reverse effect nếu đã post tồn kho.

---

## 8. Permission & Audit Governance

### 8.1 Nguyên tắc

- Phân quyền phải theo vai trò nghiệp vụ, không chỉ theo Django superuser.
- Technical admin có thể truy cập console kỹ thuật, nhưng thao tác dữ liệu nghiệp vụ nhạy cảm vẫn phải audit.
- Dữ liệu GPS, ảnh, lương, tạm ứng, vi phạm, đền bù là dữ liệu nhạy cảm.

### 8.2 Các thao tác bắt buộc audit

- Tạo/sửa/xóa phân công ca đã phát sinh check-in.
- Sửa check-in/check-out, GPS, ảnh, giờ công.
- Duyệt hoặc hủy duyệt biên bản/sự cố.
- Tính lại, khóa, mở khóa, chỉnh bảng lương.
- Xuất Excel/PDF chứa lương, thông tin nhân viên, GPS, ảnh, sự cố.
- Thay đổi cấu hình đơn giá, phụ cấp, khấu trừ, bán kính GPS.
- Thao tác qua `/admin/` vào dữ liệu nghiệp vụ nhạy cảm.

### 8.3 Audit record tối thiểu

- actor/user,
- action,
- object type,
- object id,
- timestamp,
- before/after hoặc diff nếu phù hợp,
- reason/note đối với sửa dữ liệu nhạy cảm,
- request metadata nếu có: IP, user agent, device.

---

## 9. Organization Scope Contract

Hiện tại hệ thống là single-organization. `tenant_id` nếu tồn tại trong code là legacy naming cho `organization_id` cố định.

Contract hiện tại:

- Không nhận `tenant_id` tùy ý từ request để scope dữ liệu.
- Không dùng `tenant_id` như SaaS tenant thực.
- `SCMD_ORGANIZATION_ID` là guard để ngăn dữ liệu lệch tổ chức.
- Các model nghiệp vụ quan trọng phải có organization scope trực tiếp hoặc được document rõ scope gián tiếp qua parent model.
- Dashboard/payroll/attendance query phải hoặc scope rõ, hoặc ghi rõ là single-org exception.

Definition of Done cho debt này:

- Chỉ còn một manager scope tổ chức trong `core/managers.py` hoặc tên tương đương.
- Không còn duplicate `TenantAwareManager` trong app riêng.
- Tất cả model dùng chung manager import từ SSOT.
- Query dashboard được rà soát scope.
- Tài liệu gọi rõ `tenant_id` là legacy naming nếu schema chưa đổi được.

Roadmap naming:

- Ngắn hạn: giữ `tenant_id` để tránh migration lớn.
- Trung hạn: document alias `organization_id` ở service/application layer.
- Dài hạn: đổi schema chỉ khi có migration plan và test đối soát.

---

## 10. Frontend & Brand Contract

SCMD là nền tảng chỉ huy và quản trị vận hành nội bộ, không phải cyber command center.

### 10.0 Brand hierarchy

- **Công ty / thương hiệu mẹ:** SCMD
- **Nguồn gốc tên:** Security Commander
- **Sản phẩm thương mại:** SCMD Pro
- **Tagline công ty:** Công ty công nghệ phần mềm cho ngành dịch vụ bảo vệ
- **Tagline sản phẩm:** Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp
- **English descriptor:** Security Command & Management Platform for Professional Security Companies
- **Product category:** operations-led security management platform with ERP capabilities
- **Quy tắc:** `SCMD` dùng cho công ty/thương hiệu mẹ; `SCMD Pro` dùng cho sản phẩm bán ra thị trường. `ERP` chỉ được dùng khi mô tả nhóm năng lực như tài chính, nhân sự, kho, hợp đồng, lương và quản trị doanh nghiệp.

### 10.1 Tên sản phẩm

Tên user-facing của sản phẩm: **SCMD Pro**. Tên công ty/thương hiệu mẹ: **SCMD**. Dòng mô tả chính thức: **Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp**.

Không dùng trên UI sản phẩm:

- SCMD ERP như tên sản phẩm chính
- SCMD như tên sản phẩm bán hàng chính
- Security Command System
- Sentinel Command System
- War Room
- Tactical
- Command Center nếu không được Việt hóa thành “Bảng điều hành vận hành” hoặc “Trung tâm điều hành SCMD Pro”
- ESP như tên sản phẩm chính

### 10.2 Asset contract

- Không dùng `cdn.tailwindcss.com` trong production template.
- Tailwind phải build local qua `theme/static_src/src/styles.css`, `tailwind.config.js`, compiled output được kiểm soát.
- Color token dùng từ brand system, không hardcode neon/cyber color trên surface nội bộ.
- Trạng thái nghiệp vụ có màu riêng nhưng màu chỉ dùng khi có ý nghĩa: success, warning, danger, info, neutral.

---

## 11. Production Deployment Contract

Production deployment phải deterministic.

Bắt buộc:

- Secrets đến từ environment/secret manager, không dùng default trong code.
- Migration production có backup và rollback note.
- Static build rõ ràng, không phụ thuộc CDN development.
- Web/worker/beat không tự chạy migration ngầm nếu chưa có release plan.
- Post-deploy phải kiểm tra health, worker heartbeat, task queue, static files, login, dashboard, admin.

Không được dùng production default cho:

- `SECRET_KEY`,
- database password,
- `FIELD_ENCRYPTION_KEY`,
- export password,
- admin password,
- external service credentials.

---

## 12. Release Governance

### 12.1 SemVer policy

| Loại release | Được phép |
|---|---|
| Patch | Bugfix, UI copy, guard nhỏ, query fix không breaking |
| Minor | Thêm use case, thêm màn hình, refactor có migration path, thêm contract không phá dữ liệu |
| Major | Đổi data model hoặc business flow có breaking change, đổi state machine quan trọng |

### 12.2 Release checklist

Mỗi release phải có:

- changelog,
- migration plan nếu có migration,
- rollback note cho thay đổi dữ liệu,
- test summary,
- debt status P0/P1/P2,
- screenshot hoặc QA note cho UI thay đổi lớn,
- xác nhận không có secret/default production mới.

### 12.3 Documentation update rule

Nếu thay đổi một trong các phần sau, phải cập nhật tài liệu cùng PR/release:

- data flow,
- model trung tâm,
- use case signature,
- permission/audit,
- payroll formula,
- attendance API,
- dashboard KPI,
- deployment/bootstrap,
- brand/UI language.

---

## 13. Technical debt đã xác nhận

### P0 — Bảo mật / lộ source / layout nguy hiểm

| Debt | Vấn đề | Action |
|---|---|---|
| `.py` trong `static/` | Có thể bị serve public qua static files | Xóa khỏi static, chuyển vào app/application đúng chỗ |
| Credential default production | Secret/export/encryption default dễ bị dùng nhầm | Bắt buộc override, fail-fast nếu production dùng default |
| Export dữ liệu nhạy cảm | Excel/PDF có thể chứa lương/GPS/nhân sự | Password/audit/permission rõ ràng |

### P1 — Kiến trúc

| Debt | Vấn đề | Action |
|---|---|---|
| Duplicate manager | `TenantAwareManager` định nghĩa nhiều nơi | Gom về SSOT trong core |
| Wildcard facade | Application layer không thực chất | Tạo use case class thật, xóa wildcard |
| Legacy root use cases | Import path mơ hồ | Migrate vào `*/application/`, xóa shim sau một release |
| Dashboard query scope | Một số query chưa organization-scoped rõ | Rà soát và document exception |

### P2 — Brand / UI / chất lượng trình bày

| Debt | Vấn đề | Action |
|---|---|---|
| Cyber/war-room language | Lệch định vị ERP | Đổi copy và naming |
| Tailwind CDN | Lệch frontend contract | Build local |
| Mojibake trong file nội bộ | Giảm chất lượng Việt hóa | Chuẩn hóa UTF-8 |
| Màu neon/cyber | Lệch brand system | Chuyển về navy/blue/neutral + state colors |

---

## 14. Điều kiện trước khi mở rộng lớn

Không bàn nghiêm túc multi-tenant thật, service split hoặc event choreography cho đến khi đạt các điều kiện:

- P0 debt = 0.
- Application layer không còn wildcard facade.
- Organization scope có SSOT.
- Payroll reconciliation và lock policy rõ.
- Attendance correction có audit.
- Dashboard KPI có source và scope rõ.
- Frontend không phụ thuộc CDN production.
- Brand cũ/cyber/war-room được loại khỏi UI chính.
- Test tối thiểu cho attendance, payroll, incident, dashboard pass.
- Release process có migration/rollback discipline.

---

## 15. Changelog

### 3.3.0 — Strategy contract hardening

- Làm rõ SCMD Pro vs SCMD.
- Làm mềm cơ chế “tài liệu luôn đúng” thành target contract có governance.
- Bổ sung Data Integrity & Reconciliation Contract.
- Bổ sung Permission & Audit Governance.
- Bổ sung State Machine mục tiêu.
- Bổ sung Organization Scope Contract và legacy naming note cho `tenant_id`.
- Bổ sung Release Governance và Definition of Done cho debt chính.

### 3.2.0 — Debt-aware architecture contract

- Xác nhận layered monolith.
- Xác nhận operational truth làm trục sản phẩm.
- Ghi nhận debt: wildcard facade, duplicate manager, Tailwind CDN, brand cũ, mojibake.

### 3.0.0 — Monolith stabilization

- Chuyển trọng tâm từ clean architecture lý tưởng sang layered monolith thực dụng.
### 3.3.1 - Public asset boundary hardening

- WhiteNoise serves the static contract rooted at `STATICFILES_DIRS = [BASE_DIR / "static"]` and emitted into `STATIC_ROOT = BASE_DIR / "staticfiles"`.
- No Python source file may exist under a WhiteNoise-served static path.
- No application-layer Python module may live under a Django `templates/` tree.
- Removing a misplaced source file from `static/` is insufficient unless any previously collected artifact under `staticfiles/` is also removed or regenerated.
- Local verification must fail if any `.py` file is detected under `static/` or `templates/`.

### 3.3.2 - Manager SSOT and application cleanup

- Organization scope query enforcement now has one shared SSOT in `core.managers.TenantAwareManager`.
- `clients/models.py`, `operations/models.py`, and `accounting/models.py` no longer define parallel organization-scope managers.
- Files under `*/application/` must contain real implementation, not wildcard-only re-export facades.
- Legacy root `*_use_cases.py` files may remain only as explicit compatibility wrappers during the transition window.
- Runtime UTF-8 cleanup in this release is limited to priority operator/developer-facing files and does not authorize broad migration-history rewrites.


### 3.5.0 - Brand architecture update: SCMD company / SCMD Pro product

- Xác nhận **SCMD** là công ty/thương hiệu mẹ, viết tắt của `Security Commander`.
- Xác nhận **SCMD Pro** là sản phẩm phần mềm thương mại bán cho doanh nghiệp dịch vụ bảo vệ.
- Chốt tagline sản phẩm: `Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ chuyên nghiệp`.
- Giữ bản chất operations-led và các năng lực ERP, nhưng không dùng `ERP` làm tên sản phẩm chính.
- Cập nhật language contract để UI, tài liệu, admin, PWA, print/export và checklist QA đồng bộ theo SCMD Pro.
