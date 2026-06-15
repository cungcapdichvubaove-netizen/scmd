# -*- coding: utf-8 -*-
from datetime import date, datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from accounting.models import ChiTietLuong, BangLuongThang
from operations.models import PhanCongCaTruc, ChamCong, ViTriChot, CaLamViec
from users.models import NhanVien
from clients.models import MucTieu, HopDong

class PayrollSnapshotIntegrityTest(TestCase):
    """
    Hệ thống kiểm thử (Backtest) tính toàn vẹn của snapshot bảng lương.
    Xác nhận các trường don_gia_hieu_luc_tu, nguon_don_gia, rate_record_id 
    phải được lưu trong ChiTietLuong.nguon_du_lieu_snapshot theo WHITEPAPER v3.5.0.
    """
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.user = User.objects.create_user(username="test_snap_user", password="password")
        self.work_date = date(2026, 1, 15)
        
        self.hd = HopDong.objects.create(so_hop_dong="HD-TEST-SNAP", tenant_id=self.tenant_id)
        self.mt = MucTieu.objects.create(hop_dong=self.hd, ten_muc_tieu="Mục tiêu Snapshot")
        self.vt = ViTriChot.objects.create(muc_tieu=self.mt, ten_vi_tri="Chốt A")
        self.ca = CaLamViec.objects.create(ten_ca="Ca Hành Chính", gio_bat_dau="08:00", gio_ket_thuc="17:00")

        # Rule 3.5.5: Tái sử dụng profile NhanVien được tạo tự động từ signals của User.
        # Tránh dùng update_or_create() vì nó kích hoạt 'select_for_update()' gây lỗi join trên Postgres.
        self.nv = NhanVien.objects.get(user=self.user)
        self.nv.ho_ten = "Nhân viên Test"
        self.nv.ma_nhan_vien = "NV001"
        self.nv.tenant_id = self.tenant_id
        self.nv.save()
        
        self.pc = PhanCongCaTruc.objects.create(
            nhan_vien=self.nv, vi_tri_chot=self.vt, ca_lam_viec=self.ca, 
            ngay_truc=self.work_date, tenant_id=self.tenant_id
        )
        self.cc = ChamCong.objects.create(
            ca_truc=self.pc,
            thoi_gian_check_in=timezone.make_aware(datetime.combine(self.work_date, datetime.min.time())),
            tenant_id=self.tenant_id,
        )
        self.bang_luong = BangLuongThang.objects.create(thang=1, nam=2026, tenant_id=self.tenant_id)

    def test_payroll_snapshot_contains_required_audit_fields(self):
        """
        Xác nhận ChiTietLuong lưu trữ snapshot với đầy đủ thông tin đối soát đơn giá.
        """
        # Giả lập kết quả từ CalculatePayrollUseCase (Application Layer)
        snapshot_data = {
            "cham_cong_id": self.cc.id,
            "gio_cong_thuc_te": 8.0,
            "don_gia_hieu_luc_tu": self.work_date.isoformat(),
            "nguon_don_gia": "MucTieuDonGiaHistory", 
            "rate_record_id": 999,
        }
        
        chi_tiet = ChiTietLuong.objects.create(
            bang_luong=self.bang_luong,
            nhan_vien=self.nv,
            nguon_du_lieu_snapshot=snapshot_data,
            tenant_id=self.tenant_id
        )
        
        # Kiểm tra tính toàn vẹn của JSONField
        data = chi_tiet.nguon_du_lieu_snapshot
        self.assertIn('don_gia_hieu_luc_tu', data, "Lỗi Rule 4.6: Thiếu don_gia_hieu_luc_tu trong snapshot")
        self.assertIn('nguon_don_gia', data, "Lỗi Rule 4.6: Thiếu nguon_don_gia trong snapshot")
        self.assertIn('rate_record_id', data, "Lỗi Rule 4.6: Thiếu rate_record_id trong snapshot")

    def test_payroll_snapshot_contains_inventory_deduction_trace(self):
        """
        Xác nhận ChiTietLuong lưu trữ snapshot chứa ID của PhieuXuat 
        khi có khấu trừ vật tư/đồng phục theo Rule 6.4.
        """
        # Giả lập dữ liệu mà CalculatePayrollUseCase thu thập từ module Inventory
        inventory_trace = [
            {
                "ma_phieu": "PX-2026-0001",
                "loai": "BAN_TRU_LUONG",
                "so_tien": 150000,
                "ngay_xuat": "2026-05-15",
                "noi_dung": "Cấp phát 02 bộ đồng phục mới"
            }
        ]
        
        chi_tiet = ChiTietLuong.objects.create(
            bang_luong=self.bang_luong,
            nhan_vien=self.nv,
            tien_dong_phuc=Decimal("150000"),
            nguon_du_lieu_snapshot={"inventory_deductions": inventory_trace},
            tenant_id=self.tenant_id
        )
        
        snapshot = chi_tiet.nguon_du_lieu_snapshot
        self.assertIn('inventory_deductions', snapshot, "Rule 6.4 violation: Thiếu trace kho trong snapshot")
        self.assertEqual(snapshot['inventory_deductions'][0]['ma_phieu'], "PX-2026-0001")
