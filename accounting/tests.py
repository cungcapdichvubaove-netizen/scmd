# Create your tests here.
# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: accounting/tests.py
Author: Mr. Anh
Created Date: 2025-12-04
Description: Unit Tests cho Module Tính Lương.
             Đảm bảo tiền nong chính xác tuyệt đối.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from users.models import NhanVien
from clients.models import MucTieu, HopDong
from operations.models import PhanCongCaTruc, CaLamViec, ViTriChot, ChamCong
from inspection.models import BienBanViPham
from accounting.models import CauHinhLuong, BangLuongThang, ChiTietLuong, AuditLog
from accounting.models_soquy import SoQuy
from accounting.services.payroll import PayrollService
from accounting.tasks import accounting_calculate_monthly_payroll

class PayrollServiceTest(TestCase):
    def setUp(self):
        """Chuẩn bị dữ liệu giả lập trước khi test"""
        # 1. Tạo Nhân viên
        self.nv = NhanVien.objects.create(
            ma_nhan_vien="TEST001", ho_ten="Bảo Vệ Test", 
            ngay_sinh="1990-01-01", trang_thai_lam_viec="CHINHTHUC"
        )
        
        # 2. Tạo Cấu hình Lương (Phụ cấp)
        CauHinhLuong.objects.create(
            nhan_vien=self.nv,
            phu_cap_trach_nhiem=500000, # 500k
            phu_cap_xang_xe=200000,     # 200k
            phu_cap_an_uong=300000      # 300k
        )
        # -> Tổng phụ cấp = 1.000.000 VNĐ

        # 3. Tạo Mục tiêu & Đơn giá (Quan trọng)
        # Giả sử lương khoán 7.200.000 / 240h chuẩn = 30.000đ/h
        self.hd = HopDong.objects.create(so_hop_dong="HD-TEST", gia_tri=100000000, ngay_ky=timezone.now())
        self.mt = MucTieu.objects.create(
            hop_dong=self.hd, ten_muc_tieu="Mục Tiêu A", 
            luong_khoan_bao_ve=7200000, so_gio_mot_ngay=8
        )
        self.vi_tri = ViTriChot.objects.create(muc_tieu=self.mt, ten_vi_tri="Cổng Chính")
        
        # 4. Tạo Ca làm việc
        self.ca_lam = CaLamViec.objects.create(ten_ca="Ca A", gio_bat_dau="06:00", gio_ket_thuc="14:00") # 8 tiếng

    def test_tinh_luong_chuan(self):
        """
        Kịch bản 1: Đi làm 1 ngày đủ 8 tiếng. Không phạt, không ứng.
        Kỳ vọng:
        - Giờ công: 8h
        - Lương chính: 8 * 30.000 = 240.000
        - Phụ cấp: 1.000.000
        - Thực lãnh: 1.240.000
        """
        today = timezone.now().date()
        
        # Giả lập chấm công
        pc = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri, nhan_vien=self.nv, ca_lam_viec=self.ca_lam, ngay_truc=today
        )
        ChamCong.objects.create(
            ca_truc=pc,
            thoi_gian_check_in=timezone.make_aware(datetime.combine(today, datetime.strptime("06:00", "%H:%M").time())),
            thoi_gian_check_out=timezone.make_aware(datetime.combine(today, datetime.strptime("14:00", "%H:%M").time()))
        )
        
        # Chạy tính lương
        PayrollService.tinh_luong_thang(today.month, today.year)
        
        # Kiểm tra kết quả
        phieu = ChiTietLuong.objects.get(nhan_vien=self.nv)
        
        self.assertEqual(phieu.tong_gio_lam, 8.0)
        self.assertEqual(phieu.luong_chinh, 240000)
        self.assertEqual(phieu.tong_phu_cap, 1000000)
        self.assertEqual(phieu.thuc_lanh, 1240000)
        print("✅ Test 1 (Chuẩn): PASS")

    def test_tru_tien_phat_va_tam_ung(self):
        """
        Kịch bản 2: 
        - Làm 10 tiếng (300.000 lương)
        - Bị phạt 50.000 (Inspection)
        - Tạm ứng 100.000 (Accounting)
        Kỳ vọng Thực lãnh: 300k + 1tr (PC) - 50k - 100k = 1.150.000
        """
        today = timezone.now().date()
        
        # 1. Chấm công 10h
        pc = PhanCongCaTruc.objects.create(vi_tri_chot=self.vi_tri, nhan_vien=self.nv, ca_lam_viec=self.ca_lam, ngay_truc=today)
        ChamCong.objects.create(
            ca_truc=pc,
            thoi_gian_check_in=timezone.make_aware(datetime.combine(today, datetime.strptime("06:00", "%H:%M").time())),
            thoi_gian_check_out=timezone.make_aware(datetime.combine(today, datetime.strptime("16:00", "%H:%M").time())) # 10 tiếng
        )
        
        # 2. Tạo biên bản phạt (Đã duyệt)
        BienBanViPham.objects.create(
            doi_tuong_vi_pham=self.nv, muc_tieu=self.mt,
            hinh_thuc_xu_ly='PHAT_TIEN', so_tien_phat=50000,
            trang_thai='DA_DUYET'
        )
        
        # 3. Tạo phiếu tạm ứng (Đã duyệt)
        SoQuy.objects.create(
            ma_phieu="CHI01", loai_phieu='CHI', hang_muc='TAM_UNG',
            so_tien=100000, nhan_vien=self.nv,
            trang_thai='DA_DUYET'
        )

        # Chạy tính lương
        PayrollService.tinh_luong_thang(today.month, today.year)
        
        # Kiểm tra
        phieu = ChiTietLuong.objects.get(nhan_vien=self.nv)
        
        self.assertEqual(phieu.tong_gio_lam, 10.0)
        self.assertEqual(phieu.luong_chinh, 300000) # 10h * 30k
        self.assertEqual(phieu.phat_vi_pham, 50000)
        self.assertEqual(phieu.ung_luong, 100000)
        self.assertEqual(phieu.thuc_lanh, 1150000) # 300k + 1000k - 50k - 100k
        print("✅ Test 2 (Phạt/Ứng): PASS")

class AccountingTaskTest(TestCase):
    """Test Celery Tasks cho module Kế toán"""

    @patch('accounting.tasks.timezone.now')
    @patch('accounting.services.payroll.PayrollService.tinh_luong_thang')
    def test_calculate_payroll_date_logic(self, mock_service, mock_now):
        """Đảm bảo Task xác định đúng tháng/năm cần quyết toán dựa trên ngày chạy"""
        # Giả lập Task instance (vì task có bind=True)
        mock_task = MagicMock()
        mock_service.return_value = (True, "Hoàn tất")

        # Kịch bản 1: Chạy vào ngày 01/02/2026 -> Phải quyết toán cho tháng 01/2026
        mock_now.return_value = datetime(2026, 2, 1, 1, 0, 0, tzinfo=timezone.utc)
        accounting_calculate_monthly_payroll(mock_task)
        mock_service.assert_called_with(1, 2026)

        # Kịch bản 2: Chạy vào ngày 01/01/2026 -> Phải quyết toán cho tháng 12/2025 (Chuyển năm)
        mock_now.return_value = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        accounting_calculate_monthly_payroll(mock_task)
        mock_service.assert_called_with(12, 2025)

        print("✅ Test 3 (Task Date Logic): PASS")

class AccountingIntegrationTest(TestCase):
    """Integration Test kiểm tra luồng nghiệp vụ thực tế từ Task đến Database"""

    def setUp(self):
        """Thiết lập dữ liệu nền cho Integration Test"""
        # Tạo nhân viên và cấu hình lương
        self.nv = NhanVien.objects.create(
            ma_nhan_vien="INT-001", ho_ten="NV Integration Test",
            ngay_sinh="1995-05-05", trang_thai_lam_viec="CHINHTHUC"
        )
        CauHinhLuong.objects.create(nhan_vien=self.nv, phu_cap_trach_nhiem=100000)
        
        # Thiết lập tổ chức (SSOT Context)
        self.tenant_id = settings.SCMD_ORGANIZATION_ID

    @patch('accounting.tasks.timezone.now')
    def test_task_creates_real_records(self, mock_now):
        """Kiểm tra việc tạo BangLuongThang và AuditLog thực tế sau khi Task chạy"""
        # 1. Giả lập hôm nay là ngày 01/06/2026 (Quyết toán cho tháng 5)
        mock_now.return_value = datetime(2026, 6, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        # 2. Thực thi Task
        mock_task = MagicMock()
        accounting_calculate_monthly_payroll(mock_task)

        # 3. KIỂM TRA DATABASE (Assertions)
        
        # Kiểm tra bảng lương tổng đã được tạo đúng kỳ
        bang_luong_exists = BangLuongThang.objects.filter(thang=5, nam=2026).exists()
        self.assertTrue(bang_luong_exists, "BangLuongThang cho tháng 05/2026 chưa được tạo!")
        
        bang_luong = BangLuongThang.objects.get(thang=5, nam=2026)
        self.assertEqual(bang_luong.trang_thai, 'NHAP')

        # Kiểm tra phiếu lương chi tiết đã được tạo cho nhân viên
        chi_tiet_exists = ChiTietLuong.objects.filter(bang_luong=bang_luong, nhan_vien=self.nv).exists()
        self.assertTrue(chi_tiet_exists, f"Chưa tạo ChiTietLuong cho nhân viên {self.nv.ma_nhan_vien}")

        # Kiểm tra Audit Log (Tuân thủ Rule 8: Observability)
        audit_log_exists = AuditLog.objects.filter(
            module='accounting',
            model_name='BangLuongThang',
            object_id=str(bang_luong.pk),
            action=AuditLog.Action.EXECUTE
        ).exists()
        self.assertTrue(audit_log_exists, "AuditLog cho hành động quyết toán chưa được ghi nhận!")

        print(f"✅ Test 4 (Integration Payroll): PASS - BangLuongThang ID: {bang_luong.pk}")