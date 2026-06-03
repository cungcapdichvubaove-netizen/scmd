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
