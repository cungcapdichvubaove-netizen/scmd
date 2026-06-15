# SCMD Pro Backup/Restore Drill — v3.5.0

**Mục tiêu:** Xác minh tính sẵn sàng của dữ liệu sao lưu trước mỗi kỳ chốt lương (Payroll Lock) và các đợt phát hành Major/Minor.
**Tần suất:** Hằng tháng hoặc trước khi thực hiện Migration Production.

## 1. Thành phần sao lưu (Backup Targets)
1. **Database:** PostgreSQL + PostGIS (SSOT cho mọi thực thể nghiệp vụ).
2. **Media Assets:** Ảnh chấm công (GPS Photos), ảnh sự cố, chứng từ sổ quỹ.
3. **Environment:** Các biến môi trường (.env) và Secrets (ngoại trừ Credential Production).

## 2. Kịch bản diễn tập (Drill Scenarios)

### Scenario A: Phục hồi sau lỗi Migration
1. Thực hiện `pg_dump` cơ sở dữ liệu hiện tại.
2. Chạy một migration giả lập gây lỗi hoặc làm hỏng dữ liệu (ví dụ xóa nhầm NhanVien).
3. Thực hiện khôi phục từ bản dump.
4. Chạy `verify_restore_integrity.py` để so sánh số lượng bản ghi chính.

### Scenario B: Khôi phục ảnh bằng chứng (Media Recovery)
1. Xóa thư mục `media/check_in/` và `media/su_co/`.
2. Khôi phục từ bản sao lưu gần nhất.
3. Truy cập Dashboard và xác nhận ảnh cũ vẫn hiển thị chính xác.

## 3. Checklist xác nhận thành công
- [ ] Database restore thành công không có lỗi syntax SQL.
- [ ] `AuditLog` khớp checksum (chứng minh bản sao lưu không bị tamper).
- [ ] Số lượng `ChiTietLuong` của kỳ LOCKED gần nhất không thay đổi.
- [ ] Toàn bộ tọa độ GPS (PointField) hoạt động bình thường trên bản đồ.
- [ ] Ghi Audit Log về hành động thực hiện diễn tập: `EXECUTE - System - BackupDrill`.

## 4. Rollback Note
Nếu diễn tập trên môi trường Staging thất bại:
1. Kiểm tra lại phiên bản `pg_dump` và `pg_restore` (phải khớp version).
2. Kiểm tra quyền của database user (phải có quyền tạo/xóa schema).
3. Báo cáo lỗi kỹ thuật cho đội hạ tầng.

---
*Phê duyệt: CTO Anh - SCMD Pro Architecture Team*