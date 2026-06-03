# -*- coding: utf-8 -*-

from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from accounting.application.payroll_use_cases import CalculatePayrollUseCase
from accounting.models import BangLuongThang, CauHinhLuong, ChiTietLuong
from accounting.models_soquy import SoQuy
from accounting.services.payroll import PayrollService
from clients.models import HopDong, MucTieu
from inspection.models import BienBanViPham
from inventory.models import PhieuXuat
from operations.models import CaLamViec, ChamCong, PhanCongCaTruc, ViTriChot, BaoCaoSuCo
from users.models import NhanVien


class PayrollHotfixTest(TestCase):
    def setUp(self):
        today = timezone.now().date()
        self.today = today
        self.nhan_vien = NhanVien.objects.create(
            ma_nhan_vien="PAY001",
            ho_ten="Nhan vien Payroll",
            ngay_sinh="1990-01-01",
            trang_thai_lam_viec="CHINHTHUC",
            sdt_chinh="+84999999999",
        )
        CauHinhLuong.objects.create(
            nhan_vien=self.nhan_vien,
            phu_cap_trach_nhiem=500000,
            phu_cap_xang_xe=200000,
            phu_cap_an_uong=300000,
        )
        self.hop_dong = HopDong.objects.create(
            so_hop_dong="HD-PAY-001",
            ngay_ky=today,
            ngay_hieu_luc=today,
            ngay_het_han=today,
            gia_tri=1000000,
        )
        self.muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Muc tieu Payroll",
            dia_chi="Dia chi test",
            sdt_lien_he="0123",
            luong_khoan_bao_ve=7200000,
            so_gio_mot_ngay=8,
        )
        self.vi_tri = ViTriChot.objects.create(
            muc_tieu=self.muc_tieu,
            ten_vi_tri="Cong chinh",
        )
        self.ca_lam = CaLamViec.objects.create(
            ten_ca="Ca A",
            gio_bat_dau="06:00",
            gio_ket_thuc="14:00",
        )
        self.bang_luong = BangLuongThang.objects.create(
            ten_bang_luong=f"Bang luong {today.month}/{today.year}",
            thang=today.month,
            nam=today.year,
        )

    def _create_attendance(self, hours):
        phan_cong = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=self.nhan_vien,
            ca_lam_viec=self.ca_lam,
            ngay_truc=self.today,
        )
        return ChamCong.objects.create(
            ca_truc=phan_cong,
            thoi_gian_check_in=timezone.make_aware(
                datetime.combine(self.today, datetime.strptime("06:00", "%H:%M").time())
            ),
            thoi_gian_check_out=timezone.make_aware(
                datetime.combine(self.today, datetime.strptime("14:00", "%H:%M").time())
            ),
            thuc_lam_gio=hours,
        )

    def test_calculate_payroll_maps_to_current_model_fields(self):
        self._create_attendance(8)

        phieu = CalculatePayrollUseCase.execute(
            nhan_vien=self.nhan_vien,
            bang_luong=self.bang_luong,
            tenant_id=self.bang_luong.tenant_id,
        )

        self.assertEqual(phieu.tong_gio_lam, 8.0)
        self.assertEqual(phieu.luong_chinh, Decimal("240000"))
        self.assertEqual(phieu.phu_cap_khac, Decimal("1000000"))
        self.assertEqual(phieu.tong_phu_cap, Decimal("1000000"))
        self.assertEqual(phieu.thuc_lanh, Decimal("1240000"))

    def test_calculate_payroll_collects_current_deduction_sources(self):
        self._create_attendance(10)
        BienBanViPham.objects.create(
            doi_tuong_vi_pham=self.nhan_vien,
            muc_tieu=self.muc_tieu,
            hinh_thuc_xu_ly="PHAT_TIEN",
            so_tien_phat=50000,
            trang_thai="DA_DUYET",
            ngay_vi_pham=timezone.now(),
        )
        SoQuy.objects.create(
            ma_phieu="SQ-PAY-001",
            loai_phieu="CHI",
            hang_muc="TAM_UNG",
            so_tien=100000,
            ngay_lap=timezone.now(),
            nhan_vien=self.nhan_vien,
            dien_giai="Tam ung test",
            trang_thai="DA_DUYET",
        )
        PhieuXuat.objects.create(
            ma_phieu="PX-PAY-001",
            loai_xuat="BAN_TRU_LUONG",
            ngay_xuat=timezone.now(),
            nhan_vien_nhan=self.nhan_vien,
            ghi_chu="Dong phuc",
            tong_tien_phai_thu=50000,
            trang_thai_thanh_toan="CHUA_TRU",
        )
        BaoCaoSuCo.objects.create(
            tieu_de="Su co test",
            muc_tieu=self.muc_tieu,
            nhan_vien_bao_cao=self.nhan_vien,
            nhan_vien_co_loi=self.nhan_vien,
            thoi_gian_phat_hien=timezone.now(),
            trang_thai="CHO_DEN_BU",
            phai_thu_nhan_vien=75000,
        )

        phieu = CalculatePayrollUseCase.execute(
            nhan_vien=self.nhan_vien,
            bang_luong=self.bang_luong,
            tenant_id=self.bang_luong.tenant_id,
        )

        self.assertEqual(phieu.luong_chinh, Decimal("300000"))
        self.assertEqual(phieu.phat_vi_pham, Decimal("50000"))
        self.assertEqual(phieu.ung_luong, Decimal("100000"))
        self.assertEqual(phieu.tien_dong_phuc, Decimal("50000"))
        self.assertEqual(phieu.tien_den_bu, Decimal("75000"))
        self.assertEqual(phieu.thuc_lanh, Decimal("1025000"))

    @patch("accounting.services.payroll.AuditPayrollUseCase.execute")
    def test_payroll_service_degrades_cleanly_when_audit_fails(self, mock_audit):
        mock_audit.return_value = {"status": "error", "message": "audit unavailable"}
        self._create_attendance(8)

        success, message = PayrollService.tinh_luong_thang(
            self.today.month,
            self.today.year,
        )

        self.assertTrue(success)
        self.assertIn("hau kiem payroll chua chay duoc", message.lower())
        self.assertTrue(
            ChiTietLuong.objects.filter(
                bang_luong__thang=self.today.month,
                bang_luong__nam=self.today.year,
                nhan_vien=self.nhan_vien,
            ).exists()
        )
