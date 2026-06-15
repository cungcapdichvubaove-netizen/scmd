# Create your tests here.
# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: accounting/tests.py
Author: Mr. Anh
Created Date: 2025-12-04
Description: Unit Tests cho Module Tính Lương.
             Đảm bảo tiền nong chính xác tuyệt đối.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.utils import timezone

from accounting.admin import ChiTietLuongAdmin
from main.models import AuditLog
from accounting.models import BangLuongThang, CauHinhLuong, ChiTietLuong
from accounting.models_soquy import SoQuy
from accounting.services.payroll import PayrollService
from accounting.tasks import accounting_calculate_monthly_payroll
from clients.models import HopDong, MucTieu
from inspection.models import BienBanViPham
from operations.models import CaLamViec, ChamCong, PhanCongCaTruc, ViTriChot
from users.models import NhanVien


class PayrollServiceTest(TestCase):
    def setUp(self):
        self.nv = NhanVien.objects.create(
            ma_nhan_vien="TEST001",
            ho_ten="Bao Ve Test",
            ngay_sinh="1990-01-01",
            trang_thai_lam_viec="CHINHTHUC",
        )
        CauHinhLuong.objects.create(
            nhan_vien=self.nv,
            phu_cap_trach_nhiem=500000,
            phu_cap_xang_xe=200000,
            phu_cap_an_uong=300000,
        )
        self.hd = HopDong.objects.create(
            so_hop_dong="HD-TEST",
            gia_tri=100000000,
            ngay_ky=timezone.now(),
        )
        self.mt = MucTieu.objects.create(
            hop_dong=self.hd,
            ten_muc_tieu="Muc Tieu A",
            dia_chi="Dia chi test",
            sdt_lien_he="0123456789",
            luong_khoan_bao_ve=7200000,
            so_gio_mot_ngay=8,
        )
        self.vi_tri = ViTriChot.objects.create(
            muc_tieu=self.mt,
            ten_vi_tri="Cong Chinh",
        )
        self.ca_lam = CaLamViec.objects.create(
            ten_ca="Ca A",
            gio_bat_dau="06:00",
            gio_ket_thuc="14:00",
        )

    def test_tinh_luong_chuan(self):
        today = timezone.now().date()
        pc = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=self.nv,
            ca_lam_viec=self.ca_lam,
            ngay_truc=today,
        )
        ChamCong.objects.create(
            ca_truc=pc,
            thoi_gian_check_in=timezone.make_aware(
                datetime.combine(today, datetime.strptime("06:00", "%H:%M").time())
            ),
            thoi_gian_check_out=timezone.make_aware(
                datetime.combine(today, datetime.strptime("14:00", "%H:%M").time())
            ),
        )

        PayrollService.tinh_luong_thang(today.month, today.year)

        phieu = ChiTietLuong.objects.get(nhan_vien=self.nv)
        self.assertEqual(phieu.tong_gio_lam, 8.0)
        self.assertEqual(phieu.luong_chinh, 240000)
        self.assertEqual(phieu.tong_phu_cap, 1000000)
        self.assertEqual(phieu.thuc_lanh, 1240000)

    def test_tru_tien_phat_va_tam_ung(self):
        today = timezone.now().date()
        pc = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=self.nv,
            ca_lam_viec=self.ca_lam,
            ngay_truc=today,
        )
        ChamCong.objects.create(
            ca_truc=pc,
            thoi_gian_check_in=timezone.make_aware(
                datetime.combine(today, datetime.strptime("06:00", "%H:%M").time())
            ),
            thoi_gian_check_out=timezone.make_aware(
                datetime.combine(today, datetime.strptime("16:00", "%H:%M").time())
            ),
        )
        BienBanViPham.objects.create(
            doi_tuong_vi_pham=self.nv,
            muc_tieu=self.mt,
            hinh_thuc_xu_ly="PHAT_TIEN",
            so_tien_phat=50000,
            trang_thai="DA_DUYET",
        )
        SoQuy.objects.create(
            ma_phieu="CHI01",
            loai_phieu="CHI",
            hang_muc="TAM_UNG",
            so_tien=100000,
            nhan_vien=self.nv,
            trang_thai="DA_DUYET",
        )

        PayrollService.tinh_luong_thang(today.month, today.year)

        phieu = ChiTietLuong.objects.get(nhan_vien=self.nv)
        self.assertEqual(phieu.tong_gio_lam, 10.0)
        self.assertEqual(phieu.luong_chinh, 300000)
        self.assertEqual(phieu.phat_vi_pham, 50000)
        self.assertEqual(phieu.ung_luong, 100000)
        self.assertEqual(phieu.thuc_lanh, 1150000)


class AccountingTaskTest(TestCase):
    @patch("accounting.tasks.timezone.now")
    @patch("accounting.services.payroll.PayrollService.tinh_luong_thang")
    def test_calculate_payroll_date_logic(self, mock_service, mock_now):
        mock_task = MagicMock()
        mock_service.return_value = (True, "Hoan tat")

        mock_now.return_value = datetime(2026, 2, 1, 1, 0, 0, tzinfo=timezone.utc)
        accounting_calculate_monthly_payroll(mock_task)
        mock_service.assert_called_with(1, 2026)

        mock_now.return_value = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        accounting_calculate_monthly_payroll(mock_task)
        mock_service.assert_called_with(12, 2025)


class AccountingIntegrationTest(TestCase):
    def setUp(self):
        self.nv = NhanVien.objects.create(
            ma_nhan_vien="INT-001",
            ho_ten="NV Integration Test",
            ngay_sinh="1995-05-05",
            trang_thai_lam_viec="CHINHTHUC",
        )
        CauHinhLuong.objects.create(nhan_vien=self.nv, phu_cap_trach_nhiem=100000)

    @patch("accounting.tasks.timezone.now")
    def test_task_creates_real_records(self, mock_now):
        mock_now.return_value = datetime(2026, 6, 1, 1, 0, 0, tzinfo=timezone.utc)
        mock_task = MagicMock()
        accounting_calculate_monthly_payroll(mock_task)

        bang_luong = BangLuongThang.objects.get(thang=5, nam=2026)
        self.assertEqual(bang_luong.trang_thai, BangLuongThang.TrangThai.CALCULATED)
        self.assertTrue(
            ChiTietLuong.objects.filter(
                bang_luong=bang_luong,
                nhan_vien=self.nv,
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                module="accounting",
                model_name="BangLuongThang",
                object_id=str(bang_luong.pk),
                action=AuditLog.Action.EXECUTE,
            ).exists()
        )


class ChiTietLuongAdminLockingTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = ChiTietLuongAdmin(ChiTietLuong, self.site)
        self.request = RequestFactory().get("/admin/accounting/chitietluong/1/change/")
        self.nhan_vien = NhanVien.objects.create(
            ma_nhan_vien="ADM001",
            ho_ten="Nhan vien khoa luong",
            ngay_sinh="1990-01-01",
            trang_thai_lam_viec="CHINHTHUC",
        )
        self.bang_luong = BangLuongThang.objects.create(
            thang=6,
            nam=2026,
        )
        self.chi_tiet = ChiTietLuong.objects.create(
            bang_luong=self.bang_luong,
            nhan_vien=self.nhan_vien,
            tong_gio_lam=26,
            luong_chinh=5000000,
            thuc_lanh=4800000,
        )
        self.bang_luong.trang_thai = BangLuongThang.TrangThai.LOCKED
        self.bang_luong.save(update_fields=["trang_thai"])

    def test_locked_payroll_detail_is_fully_readonly(self):
        readonly_fields = self.admin.get_readonly_fields(
            request=None,
            obj=self.chi_tiet,
        )
        self.assertIn("luong_chinh", readonly_fields)
        self.assertIn("tong_gio_lam", readonly_fields)
        self.assertIn("thuc_lanh", readonly_fields)

    def test_locked_payroll_detail_cannot_be_deleted(self):
        self.assertFalse(
            self.admin.has_delete_permission(request=None, obj=self.chi_tiet)
        )

    def test_locked_payroll_detail_rejects_direct_model_save(self):
        self.chi_tiet.luong_chinh = 5100000
        with self.assertRaises(ValidationError):
            self.chi_tiet.save()

    def test_cannot_edit_payslip_when_payroll_locked(self):
        self.chi_tiet.luong_chinh = Decimal("1")
        with self.assertRaises(ValidationError):
            self.admin.save_model(
                self.request,
                self.chi_tiet,
                form=None,
                change=True,
            )
