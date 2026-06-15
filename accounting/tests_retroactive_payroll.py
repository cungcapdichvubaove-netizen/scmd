# -*- coding: utf-8 -*-
"""
SCMD Pro - Payroll Retroactive & Snapshot Regression Tests
---------------------------------------------------------
Kiểm thử Section 6.2 của WHITEPAPER.md:
- Resolve đơn giá hồi tố theo từng ngày trực (effective-dated).
- Tính toàn vẹn của snapshot đối soát trong ChiTietLuong.
"""

from datetime import date
from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Permission, User
from django.urls import reverse
from main.models import AuditLog
from clients.models import HopDong, MucTieu, MucTieuDonGiaHistory
from accounting.models import BangLuongThang, ChiTietLuong
from operations.models import ViTriChot, CaLamViec, PhanCongCaTruc, ChamCong, BaoCaoSuCo
from inventory.models import LoaiVatTu, VatTu, PhieuNhap, ChiTietPhieuNhap, PhieuXuat, ChiTietPhieuXuat
from inventory.models_ledger import InventoryLedgerEntry
from inventory.application.inventory_document_use_cases import InventoryDocumentUseCase
from operations.application.attendance_correction_use_cases import CorrectAttendanceUseCase
from operations.application.incident_transition_policy import IncidentTransitionPolicy
from accounting.services.payroll import PayrollService
from accounting.tasks import accounting_calculate_monthly_payroll
from accounting.admin import ChiTietLuongAdmin
from unittest.mock import MagicMock, patch
from rolepermissions.roles import assign_role
from users.models import NhanVien

class RetroactivePayrollTest(TestCase):
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        
        # 1. Tạo nhân viên
        self.nv = NhanVien.objects.create(
            ho_ten="Nguyễn Văn A",
            ma_nhan_vien="NV001",
            tenant_id=self.tenant_id
        )

        # 2. Tạo hợp đồng
        self.hd = HopDong.objects.create(
            so_hop_dong="HD-2026-RETRO",
            ngay_hieu_luc=date(2026, 1, 1),
            tenant_id=self.tenant_id
        )

        # 3. Tạo mục tiêu với đơn giá baseline (Mặc định: 6tr, 12h/ngày)
        self.mt = MucTieu.objects.create(
            hop_dong=self.hd,
            ten_muc_tieu="Mục tiêu Alpha",
            luong_khoan_bao_ve=6000000,
            so_gio_mot_ngay=Decimal("12.00"),
            ban_kinh_cho_phep=100
        )

    def test_payroll_rate_resolution_without_history(self):
        """
        Kiểm tra: Nếu không có lịch sử, hệ thống lấy cấu hình hiện tại của mục tiêu.
        """
        ngay_truc = date(2026, 5, 10)
        context = self.mt.get_payroll_rate_context(ngay_truc)
        
        self.assertEqual(context["source"], "CURRENT_TARGET_CONFIG")
        self.assertEqual(context["monthly_salary"], Decimal("6000000"))
        self.assertIsNone(context["rate_record_id"])

    def test_retroactive_rate_resolution_by_shift_date(self):
        """
        Rule 6.2: Với thay đổi đơn giá hồi tố, payroll phải resolve đơn giá theo 'ngày trực'.
        """
        # Tạo lịch sử: Từ 01/05 đơn giá 7tr
        h1 = MucTieuDonGiaHistory.objects.create(
            muc_tieu=self.mt,
            ngay_hieu_luc=date(2026, 5, 1),
            luong_khoan_bao_ve=7000000,
            so_gio_mot_ngay=Decimal("12.00"),
            tenant_id=self.tenant_id
        )
        # Tạo lịch sử: Từ 15/05 tăng lên 8tr
        h2 = MucTieuDonGiaHistory.objects.create(
            muc_tieu=self.mt,
            ngay_hieu_luc=date(2026, 5, 15),
            luong_khoan_bao_ve=8000000,
            so_gio_mot_ngay=Decimal("12.00"),
            tenant_id=self.tenant_id
        )

        # Kiểm tra ngày 10/05 (phải lấy mốc 7tr)
        ctx1 = self.mt.get_payroll_rate_context(date(2026, 5, 10))
        self.assertEqual(ctx1["rate_record_id"], h1.id)
        self.assertEqual(ctx1["monthly_salary"], Decimal("7000000"))

        # Kiểm tra ngày 20/05 (phải lấy mốc 8tr)
        ctx2 = self.mt.get_payroll_rate_context(date(2026, 5, 20))
        self.assertEqual(ctx2["rate_record_id"], h2.id)
        self.assertEqual(ctx2["monthly_salary"], Decimal("8000000"))

    def test_chi_tiet_luong_snapshot_integrity(self):
        """
        Rule 6.2: ChiTietLuong phải lưu đủ snapshot dữ liệu nguồn để giải thích kết quả.
        """
        bang_luong = BangLuongThang.objects.create(
            thang=5, nam=2026, tenant_id=self.tenant_id
        )
        
        # Giả lập dữ liệu snapshot mà CalculatePayrollUseCase sẽ tạo ra
        rate_ctx = self.mt.get_payroll_rate_context(date(2026, 5, 10))
        
        snapshot_data = {
            "attendance_snapshot": [
                {
                    "date": "2026-05-10",
                    "hours": 12.0,
                    "hourly_rate": str(rate_ctx["hourly_rate"]),
                    "don_gia_hieu_luc_tu": rate_ctx["effective_date"].isoformat(),
                    "nguon_don_gia": rate_ctx["source"],
                    "rate_record_id": rate_ctx["rate_record_id"]
                }
            ],
            "audit": {
                "engine_version": "3.5.0",
                "calculated_at": timezone.now().isoformat()
            }
        }

        slip = ChiTietLuong.objects.create(
            bang_luong=bang_luong,
            nhan_vien=self.nv,
            luong_chinh=Decimal("7000000"),
            nguon_du_lieu_snapshot=snapshot_data,
            tenant_id=self.tenant_id
        )

        # Kiểm tra dữ liệu đã lưu
        persisted = ChiTietLuong.objects.get(pk=slip.pk)
        entry = persisted.nguon_du_lieu_snapshot["attendance_snapshot"][0]
        
        self.assertEqual(entry["nguon_don_gia"], "CURRENT_TARGET_CONFIG")
        self.assertIn("hourly_rate", entry)
        self.assertEqual(entry["don_gia_hieu_luc_tu"], self.hd.ngay_hieu_luc.isoformat())

class PayrollImmutabilityTest(TestCase):
    """
    Kiểm thử Section 6.2 & 7.3 của WHITEPAPER.md:
    Đảm bảo bảng lương LOCKED/PAID không thể bị sửa đổi qua Admin, Service, API hoặc Task.
    """
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.admin_user = User.objects.create_superuser(
            username="payroll_admin",
            password="password",
            email="payroll_admin@example.com",
        )
        self.nv = NhanVien.objects.create(
            ho_ten="Trần Văn B", ma_nhan_vien="NV002", tenant_id=self.tenant_id
        )
        self.bl = BangLuongThang.objects.create(
            thang=6, nam=2026,
            trang_thai=BangLuongThang.TrangThai.DRAFT,
            tenant_id=self.tenant_id
        )
        # Thiết lập dữ liệu CRM/Operations cho tháng 6
        self.hd = HopDong.objects.create(so_hop_dong="HD-IMMUTABLE-TEST", tenant_id=self.tenant_id)
        self.mt = MucTieu.objects.create(
            hop_dong=self.hd, 
            ten_muc_tieu="Mục tiêu Bảo mật", 
            luong_khoan_bao_ve=7000000, 
            so_gio_mot_ngay=12,
        )
        self.slip = ChiTietLuong.objects.create(
            bang_luong=self.bl, nhan_vien=self.nv,
            luong_chinh=Decimal("5000000"), tenant_id=self.tenant_id
        )
        self.bl.trang_thai = BangLuongThang.TrangThai.LOCKED
        self.bl.save(update_fields=["trang_thai"])

    def test_model_blocks_save_when_locked(self):
        """Model level guard: save() gọi clean() và chặn sửa phiếu lương đã khóa."""
        self.slip.luong_chinh = Decimal("6000000")
        with self.assertRaises(ValidationError):
            self.slip.save()

    def test_service_blocks_calculation_for_locked_period(self):
        """Service Layer guard: PayrollService.tinh_luong_thang chặn kỳ đã khóa."""
        success, message = PayrollService.tinh_luong_thang(6, 2026)
        self.assertFalse(success)
        self.assertIn("da khoa so", message.lower())

    def test_admin_blocks_edit_on_locked_payroll(self):
        """Admin Layer guard: ChiTietLuongAdmin chặn quyền sửa/xóa khi kỳ đã khóa."""
        from django.contrib.admin.sites import AdminSite
        model_admin = ChiTietLuongAdmin(ChiTietLuong, AdminSite())
        request = RequestFactory().get('/admin/accounting/chitietluong/')
        request.user = self.admin_user
        
        self.assertFalse(model_admin.has_change_permission(request, self.slip))
        self.assertFalse(model_admin.has_delete_permission(request, self.slip))

    @patch("accounting.tasks.PayrollService.tinh_luong_thang")
    def test_task_skips_retry_for_locked_error(self, mock_service):
        """Task Layer logic: Không retry khi gặp lỗi 'đã khóa kỳ'."""
        mock_service.return_value = (False, "Bang luong thang 6/2026 da khoa so.")

        with patch.object(accounting_calculate_monthly_payroll, "retry") as mock_retry:
            result = accounting_calculate_monthly_payroll.run()

        self.assertEqual(result, "Bang luong thang 6/2026 da khoa so.")
        mock_retry.assert_not_called()

    def test_attendance_correction_blocked_when_locked(self):
        """Rule 6.1: Đảm bảo CorrectAttendanceUseCase chặn việc sửa chấm công nếu kỳ lương đã LOCKED."""
        # 1. Tạo ca trực và chấm công khi kỳ còn DRAFT, sau đó mới khóa kỳ.
        # Model guard phải chặn sửa sau khóa, không chặn setup dữ liệu hợp lệ trước khóa.
        self.bl.trang_thai = BangLuongThang.TrangThai.DRAFT
        self.bl.save(update_fields=["trang_thai"])

        vt = ViTriChot.objects.create(muc_tieu=self.mt, ten_vi_tri="Cổng chính", tenant_id=self.tenant_id)
        ca = CaLamViec.objects.create(ten_ca="Ca 12h", gio_bat_dau="06:00", gio_ket_thuc="18:00", tenant_id=self.tenant_id)
        pc = PhanCongCaTruc.objects.create(
            vi_tri_chot=vt, nhan_vien=self.nv, ca_lam_viec=ca, 
            ngay_truc=date(2026, 6, 10), tenant_id=self.tenant_id
        )
        cc = ChamCong.objects.create(ca_truc=pc, thoi_gian_check_in=timezone.now(), tenant_id=self.tenant_id)

        self.bl.trang_thai = BangLuongThang.TrangThai.LOCKED
        self.bl.save(update_fields=["trang_thai"])

        # 2. Cố gắng thực hiện correction qua Use Case chính thức
        candidate = ChamCong(ghi_chu="Sửa đổi sau khi chốt")
        with self.assertRaises(ValidationError) as cm:
            CorrectAttendanceUseCase.execute(
                cham_cong_id=cc.id,
                candidate=candidate,
                changed_fields=["ghi_chu"],
                reason="Điều chỉnh sai sót",
            )
        self.assertIn("LOCKED", str(cm.exception))

class IncidentLifecycleTest(TestCase):
    """
    Kiểm thử Section 6.3 & 7.2 của WHITEPAPER.md:
    Quy trình đóng/mở sự cố và tính bất biến của dữ liệu khi đã đóng.
    """
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.hd = HopDong.objects.create(so_hop_dong="HD-INC-REG-01", tenant_id=self.tenant_id)
        self.mt = MucTieu.objects.create(
            hop_dong=self.hd, ten_muc_tieu="Mục tiêu Alpha"
        )

    def test_incident_state_machine_enforcement(self):
        """Rule 7.2: Chặn các bước chuyển trạng thái không hợp lệ từ HOAN_TAT tại Model Layer."""
        incident = BaoCaoSuCo.objects.create(
            tieu_de="Sự cố test", muc_tieu=self.mt, 
            trang_thai="HOAN_TAT", tenant_id=self.tenant_id
        )
        
        # Cố gắng chuyển sang trạng thái không phải Reopen (DANG_XU_LY)
        incident.trang_thai = "CHO_DEN_BU"
        with self.assertRaises(ValidationError):
            incident.save()

    def test_closed_incident_data_immutability(self):
        """Rule 6.3: Kiểm tra logic chặn sửa nội dung chính khi hồ sơ đã đóng thông qua Policy."""
        # Case 1: Sửa nội dung (tiêu đề) khi đang ở trạng thái HOAN_TAT
        with self.assertRaisesRegex(ValueError, "Không được sửa trực tiếp"):
            IncidentTransitionPolicy.validate_closed_incident_edit(
                previous_status="HOAN_TAT",
                new_status="HOAN_TAT",
                changed_fields={"tieu_de"}
            )

        # Case 2: Sửa nội dung chính kèm theo hành động Reopen
        with self.assertRaisesRegex(ValueError, "Không được sửa trực tiếp các trường nội dung chính"):
            IncidentTransitionPolicy.validate_closed_incident_edit(
                previous_status="HUY",
                new_status="DANG_XU_LY",
                changed_fields={"trang_thai", "mo_ta_chi_tiet"}
            )

    def test_reopen_path_is_valid_when_clean(self):
        """Đảm bảo Reopen hợp lệ chỉ khi chỉ thay đổi trường 'trang_thai'."""
        # Không bắn lỗi nếu chỉ đổi status sang DANG_XU_LY
        IncidentTransitionPolicy.validate_closed_incident_edit(
            previous_status="HOAN_TAT",
            new_status="DANG_XU_LY",
            changed_fields={"trang_thai"}
        )

class InventoryReconciliationTest(TestCase):
    """
    Kiểm thử Section 6.4 & 7.4 của WHITEPAPER.md:
    Quy trình ghi sổ/hủy chứng từ kho và tính bất biến/đảo ngược của ledger.
    """
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.loai = LoaiVatTu.objects.create(ten_loai="Công cụ hỗ trợ")
        self.vat_tu = VatTu.objects.create(
            loai_vat_tu=self.loai,
            ten_vat_tu="Bộ đàm Motorola",
            don_vi_tinh="Cái",
            gia_ban=150000,
            so_luong_ton=10
        )
        self.user = User.objects.create_user(username="inv_manager", password="password")
        assign_role(self.user, "thu_kho")
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="inventory",
                codename__in=[
                    "view_phieunhap",
                    "change_phieunhap",
                    "delete_phieunhap",
                    "view_phieuxuat",
                    "change_phieuxuat",
                    "delete_phieuxuat",
                ],
            )
        )

    def test_receipt_posting_and_reversal_ledger(self):
        """Rule 6.4: Kiểm tra ledger khi ghi sổ và hủy phiếu nhập (Reverse logic)."""
        # 1. Tạo phiếu nhập nháp
        pn = PhieuNhap.objects.create(ma_phieu="PN-REG-01")
        detail = ChiTietPhieuNhap.objects.create(phieu_nhap=pn, vat_tu=self.vat_tu, so_luong=5)

        # 2. Ghi sổ (Posting) -> Tăng tồn
        InventoryDocumentUseCase.post_inventory_document(pn, user=self.user)
        self.vat_tu.refresh_from_db()
        self.assertEqual(self.vat_tu.so_luong_ton, 15)

        # Kiểm tra ledger entry đầu tiên (POSTING / IN)
        entry1 = InventoryLedgerEntry.objects.get(chi_tiet_phieu_nhap=detail, movement_type="POSTING")
        self.assertEqual(entry1.direction, "IN")
        self.assertEqual(entry1.quantity_delta, 5)

        # 3. Hủy phiếu (Reversal/Void) -> Giảm tồn trả lại
        InventoryDocumentUseCase.void_inventory_document(pn, reason="Nhập sai số lượng", user=self.user)
        self.vat_tu.refresh_from_db()
        self.assertEqual(self.vat_tu.so_luong_ton, 10)

        # Kiểm tra ledger entry thứ hai (REVERSAL / OUT)
        entry2 = InventoryLedgerEntry.objects.get(chi_tiet_phieu_nhap=detail, movement_type="REVERSAL")
        self.assertEqual(entry2.direction, "OUT")
        self.assertEqual(entry2.quantity_delta, -5)

    def test_issue_posting_and_reversal_ledger(self):
        """Rule 6.4: Kiểm tra ledger khi ghi sổ và hủy phiếu xuất (Reverse logic)."""
        # 1. Tạo phiếu xuất nháp
        px = PhieuXuat.objects.create(ma_phieu="PX-REG-01", loai_xuat="KHAC")
        detail = ChiTietPhieuXuat.objects.create(phieu_xuat=px, vat_tu=self.vat_tu, so_luong=3)

        # 2. Ghi sổ (Posting) -> Giảm tồn
        InventoryDocumentUseCase.post_inventory_document(px, user=self.user)
        self.vat_tu.refresh_from_db()
        self.assertEqual(self.vat_tu.so_luong_ton, 7)

        # Kiểm tra ledger (POSTING / OUT)
        entry1 = InventoryLedgerEntry.objects.get(chi_tiet_phieu_xuat=detail, movement_type="POSTING")
        self.assertEqual(entry1.direction, "OUT")
        self.assertEqual(entry1.quantity_delta, -3)

        # 3. Hủy phiếu (Reversal/Void) -> Tăng tồn trả lại
        InventoryDocumentUseCase.void_inventory_document(px, reason="Khách trả lại", user=self.user)
        self.vat_tu.refresh_from_db()
        self.assertEqual(self.vat_tu.so_luong_ton, 10)

        # Kiểm tra ledger entry thứ hai (REVERSAL / IN)
        entry2 = InventoryLedgerEntry.objects.get(chi_tiet_phieu_xuat=detail, movement_type="REVERSAL")
        self.assertEqual(entry2.direction, "IN")
        self.assertEqual(entry2.quantity_delta, 3)

class SurfaceQATest(TestCase):
    """
    QA Verification theo Section 10 & 13 của WHITEPAPER.md:
    Kiểm tra Branding, Phân quyền Export và Bảo mật Static.
    """
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.user_admin = User.objects.create_superuser(username="qa_admin", password="password")
        self.client.login(username="qa_admin", password="password")
        
        # Tạo dữ liệu mẫu cho export test
        self.bl = BangLuongThang.objects.create(
            thang=1, nam=2026, tenant_id=self.tenant_id,
            trang_thai=BangLuongThang.TrangThai.LOCKED
        )

    def test_login_page_branding_and_integrity(self):
        """QA Login: Đảm bảo hiển thị SCMD Pro và không dùng Tailwind CDN."""
        self.client.logout()
        response = self.client.get(reverse('main:login'))
        content = response.content.decode('utf-8')
        
        # Kiểm tra Branding
        self.assertIn("SCMD Pro", content)
        self.assertIn("Điều hành công ty bảo vệ bằng dữ liệu", content)
        
        # Kiểm tra Hardening: Không dùng CDN (Rule 10.2)
        self.assertNotIn("cdn.tailwindcss" + ".com", content)
        self.assertIn("brand_system.css", content)

    def test_dashboard_scoping_and_naming(self):
        """QA Dashboard: Kiểm tra tên gọi và ranh giới tổ chức."""
        # Dashboard Vận hành
        response = self.client.get(reverse('operations:dashboard_vanhanh'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Bảng điều hành vận hành", response.content.decode('utf-8'))

        # Dashboard Kế toán
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 200)
        # Đảm bảo context chứa biến tenant_id chuẩn
        self.assertEqual(response.context['latest_payroll'].tenant_id, self.tenant_id)

    def test_export_security_and_audit_trail(self):
        """QA Export: Kiểm tra phân quyền và ghi log tự động (Rule 8.2)."""
        url = reverse('accounting:export_doi_soat_khau_tru_excel', args=[self.bl.pk])
        
        # 1. Thực hiện export
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        # 2. Kiểm tra Audit Log phát sinh (Section 12.3)
        audit = AuditLog.objects.filter(
            model_name="BangLuongThang",
            object_id=str(self.bl.pk),
            note__icontains="Export Excel"
        ).exists()
        self.assertTrue(audit, "Hành động Export dữ liệu lương nhạy cảm phải được ghi log.")

    def test_admin_shell_branding(self):
        """QA Admin: Kiểm tra tiêu đề Technical Console."""
        response = self.client.get('/admin/')
        self.assertIn("Quản trị kỹ thuật SCMD", response.content.decode('utf-8'))

    def test_static_and_template_security_scan(self):
        """QA Security: Chặn file thực thi (.py) nằm trong thư mục static (Debt P0)."""
        import os
        from django.conf import settings
        
        illegal_files = []
        # Quét thư mục static của project
        static_dir = os.path.join(settings.BASE_DIR, 'static')
        if os.path.exists(static_dir):
            for root, dirs, files in os.walk(static_dir):
                for file in files:
                    if file.endswith('.py'):
                        illegal_files.append(os.path.join(root, file))
        
        # Quét thư mục templates (kiến trúc layered monolith cấm logic py trong template)
        template_dir = os.path.join(settings.BASE_DIR, 'templates')
        if os.path.exists(template_dir):
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if file.endswith('.py'):
                        illegal_files.append(os.path.join(root, file))

        self.assertEqual(
            len(illegal_files), 0, 
            f"Phát hiện file .py nằm sai vị trí (Rủi ro rò rỉ source code): {illegal_files}"
        )