<<<<<<< HEAD
# SCMD Pro Architectural Enforcement Contract

Path contract:
- Canonical Markdown source: `cursorrules.md`
- Cursor compatibility mirror: `.cursorrules`
- Invalid/non-existent repository path: `.cursorrules/cursorrules.md`

Version: 3.5.0-doc-normalized
Status: Active AI/code-generation governance contract

## 1. Authority hierarchy

When documents disagree, follow this order:

1. `DOCUMENTATION.md`
2. `WHITEPAPER.md`
3. `README.md`
4. `UI_SYSTEM_REFACTOR_SPEC.md`
5. This file and `.cursorrules`
6. Existing code, only where it does not conflict with higher documents

This file must not override the product, architecture, or security contracts above.

## 2. Product positioning

- Product name: `SCMD Pro`
- Parent company / legal / vendor name: `SCMD`
- Current system model: `single-organization hardened layered monolith`
- `tenant_id` in code is legacy organization-scope naming, not dynamic SaaS tenancy
- `/dashboard/` is the business operations cockpit
- `/admin/` is the technical admin console

Do not describe SCMD Pro as:

- a cyber dashboard
- a war-room UI
- a generic ERP product name
- a microservices system
- a true multi-tenant SaaS platform

## 3. Architecture contract

SCMD Pro is a pragmatic layered monolith.

Layers:

```text
Interface Layer       Django views, DRF endpoints, templates, consumers
Application Layer     Use cases, orchestration, transaction boundary
Domain Helpers        Pure Python rules and validators
Infrastructure Layer  Django ORM, Celery, Redis, Channels, storage, SMTP, integrations
```

Required:

- Views/API receive request, call use cases, and format response.
- Application layer owns multi-step orchestration and transaction boundaries.
- Domain helpers do not depend on request/session/template.
- Celery tasks call application-layer logic rather than duplicating it.
- Avoid duplicate models, duplicate managers, duplicate use cases, or duplicate identity generation.
- Do not use wildcard imports in `*/application/*.py`.

Forbidden:

- large business orchestration inside views/serializers/templates
- ORM queries inside templates
- application-layer code that depends on HTTP request objects
- large workflow logic hidden in model `save()` overrides
- broad refactors without first measuring the real bottleneck or defect cause

## 4. Organization scope and authorization

SCMD Pro currently serves one fixed organization.

Required:

- Resolve organization scope through `settings.SCMD_ORGANIZATION_ID`.
- Use the centralized organization-scoped manager SSOT in `core.managers.TenantAwareManager`.
- Use access-policy/queryset scoping for staff, site, shift, incident, inventory, payroll, export, and dashboard workflows.
- Enforce object-level authorization on sensitive reads and mutations.
- Scope caches by user/scope when cached data depends on visibility.

Forbidden:

- using `request.tenant`
- implementing dynamic SaaS tenant loading
- accepting arbitrary `tenant_id` from request payload/form/query string
- global unscoped querysets in user-facing sensitive workflows
- bypassing object-level authorization because UI already hid the action

## 5. Operational-truth and data-integrity rules

Treat attendance, GPS, photo, incident, payroll, deduction, inventory, export, and audit data as sensitive operational records.

Required:

- preserve auditability for sensitive changes
- protect payroll lock/paid invariants
- preserve incident identity and lifecycle rules
- preserve inventory ledger integrity
- preserve KPI correctness

Forbidden:

- silent rewrites of attendance/payroll source records without audit
- broad shared caches that mix user scope
- changing payroll, attendance, inventory, or incident rules without explicit need
- introducing misleading demo data into production dashboards

## 6. UI and frontend contract

Required:

- user-facing product name is `SCMD Pro`
- local Tailwind build and local assets only
- navy/blue/neutral business UI language
- Vietnamese operational wording with standard UTF-8 text
- mobile/PWA/login/admin/dashboard copy aligned to SCMD Pro

Forbidden:

- `cdn.tailwindcss.com` in production templates
- cyber / war-room / tactical / sentinel wording in business UI
- Python business code inside `static/` or `templates/`
- public shells that drift away from SCMD Pro brand language

## 7. Performance and change discipline

Required:

- measure bottlenecks before refactoring for performance
- prefer focused fixes over speculative rewrites
- use `select_related`, `prefetch_related`, aggregate/annotate, request-local caching, and short TTL per-scope cache only where justified
- keep permission and scope enforcement intact while optimizing

Forbidden:

- removing scope checks for speed
- broad caching that is not keyed by organization/user/scope when data visibility differs
- proposing microservices as a default answer

## 8. Verification expectations

Before closing work, run the smallest relevant verification set you can support in the environment, for example:

```bash
python manage.py check
python manage.py test
python manage.py showmigrations --plan
python manage.py collectstatic --dry-run --noinput
grep -R "cdn.tailwindcss.com" -n .
grep -RInE "War Room|WarRoom|Sentinel|Tactical|Cyber|SCMD ERP|ESP" -n templates static main dashboard users operations accounting clients
grep -R "from .* import \\*" -n */application/*.py
```

If environment limitations block runtime checks, state the blocker clearly and provide static verification instead.

## 9. Expected implementation notes

For non-trivial changes, report:

1. Which documents/contracts were read
2. What scope was changed
3. Root cause or reason for change
4. Risks to permission, scope, payroll, attendance, incident, inventory, export, or audit integrity
5. Verification commands run or still required
6. Any extra technical debt found but intentionally left untouched
=======
# .cursorrules — SCMD ERP Project: Architectural Enforcement Contract

> **Phiên bản**: 2.1.0-strict  
> **Mục đích**: Quy tắc bắt buộc cho AI-assisted code generation (Cursor/Claude/Gemini).
> **Trạng thái**: Enforced Contract (Không phải Guidelines).

## 1. THỨ TỰ ƯU TIÊN THẨM QUYỀN (AUTHORITY HIERARCHY)

Khi có mâu thuẫn, AI PHẢI tuân thủ theo thứ tự:
1. **DOCUMENTATION.md** (SSOT cao nhất)
2. **WHITEPAPER.md** (Chiến lược & Tầm nhìn)
3. **File .cursorrules này** (Hợp đồng kiến trúc)
4. Existing codebase (Chỉ tham khảo patterns đúng)

## 2. AI BEHAVIOR RULES

- **KHÔNG** tự ý thêm framework/thư viện mới nếu không có yêu cầu rõ ràng.
- **ƯU TIÊN** mở rộng các Service/Use Case hiện có trước khi tạo mới.
- **LUÔN** đảm bảo Backward Compatibility (Tính tương thích ngược).
- **KHÔNG** duplicate logic nghiệp vụ (DRY tuyệt đối).
- **NẾU THIẾU THÔNG TIN**: Dừng lại và yêu cầu người dùng cung cấp tài liệu.

## 3. CLEAN ARCHITECTURE (STRICT ENFORCEMENT)

### 3.1 Cấu trúc phân lớp
- **Domain Layer**: Pure business rules, Entities, Value Objects. **CẤM** import Django (models, settings, orm).
- **Application Layer**: Use Cases, Services, Celery Tasks. **CẤM** chứa logic HTTP (request, response).
- **Infrastructure Layer**: **Django ORM Models**, Redis, External APIs, File Storage.
- **Interface Layer**: DRF Views, Django Templates, Serializers, WebSocket Consumers.

### 3.2 FORBIDDEN (NGHIÊM CẤM)
- **CẤM** Business logic bên trong Django Views hoặc Serializers.
- **CẤM** Truy cập ORM (Query) bên trong Templates.
- **CẤM** Xử lý HTTP request bên trong Use Cases.
- **CẤM** Signal dùng cho logic nghiệp vụ quan trọng (chỉ dùng cho side-effects như nén ảnh, thông báo).
- **CẤM** Ghi đè `save()` của Model để xử lý Workflow phức tạp (Dùng Use Case + `transaction.atomic`).

## 4. MULTI-TENANCY & DATA ISOLATION

Hệ thống hoạt động theo chế độ Single-organization ERP nhưng sẵn sàng cho SaaS (SCMD PRO).

### 4.1 Quy tắc truy vấn
- **CẤM** sử dụng `Model.objects.all()` trên các model liên quan đến khách hàng.
- **BẮT BUỘC** sử dụng `Model.objects.for_tenant(request.tenant)`.
- **CẤM** chấp nhận `tenant_id` từ request payload (Phải lấy từ Auth Context).

### 4.2 FORBIDDEN (NGHIÊM CẤM)
- **CẤM** Cross-tenant joins (Join dữ liệu giữa các khách thuê khác nhau).
- **CẤM** Lưu trữ `tenant_id` trong cache mà không có prefix phân biệt.

## 5. API STANDARDS (STRICT)

- **Prefix**: Luôn sử dụng `/api/v1/`.
- **Response Format**:
```json
{ "success": true, "message": "Success message", "data": { ... } }
```
- **Error Format**:
```json
{ "success": false, "error_code": "CODE", "message": "User friendly message" }
```
- **Pagination Format**:
```json
{ "count": 100, "next": "url", "previous": "url", "results": [] }
```

## 6. NAMING CONVENTIONS

| Đối tượng | Quy ước | Ví dụ |
|---|---|---|
| Django Model | PascalCase (Tiếng Việt) | `NhanVien`, `PhanCongCaTruc` |
| Database Table | snake_case | `users_nhanvien`, `operations_chamcong` |
| API Endpoint | kebab-case | `/api/v1/attendance/check-in/` |
| Celery Task | `module_action_target` | `operations_resize_image_async` |
| WebSocket Event | dot.notation | `incident.new_alert` |
| Use Case Class | PascalCase + UseCase | `CheckInUseCase` |

## 7. THUMB-FIRST & MOBILE UI STANDARDS

- **Interaction**: Các hành động chính (Primary actions) PHẢI nằm ở `fixed-bottom`.
- **Navigation**: Bottom navbar cho tối đa 5 hành động chính.
- **Touch Target**: Tối thiểu 44x44px. Tránh modal-heavy UX.
- **Components**: Chỉ sử dụng DaisyUI components, hạn chế custom CSS.

## 8. PERFORMANCE & OBSERVABILITY

- **N+1 Avoidance**: BẮT BUỘC dùng `select_related` hoặc `prefetch_related` cho mọi list endpoint.
- **Pagination**: Mọi list endpoint BẮT BUỘC phải phân trang.
- **Audit Logging**: Mọi hành động làm thay đổi trạng thái dữ liệu nhạy cảm PHẢI ghi audit log (User, Action, Timestamp, IP).
- **Request Tracking**: Luôn bao gồm `request_id`, `tenant_id`, `user_id` trong logs.

## 9. SECURITY & DATA PROTECTION

- **CẤM** lưu mật khẩu dưới dạng plain text.
- **CẤM** trả về các trường nhạy cảm (CCCD, Bank Account, Password) trong Serializers mặc định.
- **CẤM** sử dụng `DEBUG=True` trong môi trường Production.
- **CẤM** Wildcard CORS trong Production.
- **PII Protection**: Tuyệt đối không log thông tin định danh cá nhân (PII).

## 10. TESTING STANDARDS

- **Domain Layer**: 100% Unit tests (không DB).
- **APIs**: Integration tests cho luồng chính và permission.
- **Tenant Isolation**: Bắt buộc có test case kiểm tra rò rỉ dữ liệu giữa các tenant.

## 11. EVENT-DRIVEN RULES

Khi phát sinh sự kiện nghiệp vụ (Domain Event):
1. Ghi Audit Log.
2. Phát WebSocket notification (nếu cần realtime).
3. Dispatch Celery task cho các tác vụ tốn tài nguyên (nén ảnh, gửi email).

## 12. FORBIDDEN PATTERNS (ANTI-PATTERNS)

- **CẤM** `print()` debugging. Dùng `logging`.
- **CẤM** Circular imports.
- **CẤM** Hardcoded permissions hoặc geofence radius. (Đọc từ `config/roles.py` hoặc `MucTieu`).
- **CẤM** Silent exception (`except Exception: pass`).
- **CẤM** truyền Django ORM objects vào Celery tasks (Chỉ truyền PK).

---
**Tài liệu này là kỷ luật kiến trúc. AI vi phạm các quy tắc "CẤM" sẽ bị coi là sinh code lỗi.**
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
