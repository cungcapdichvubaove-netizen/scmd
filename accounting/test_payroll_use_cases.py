# -*- coding: utf-8 -*-

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounting.application.payroll_use_cases import AuditPayrollUseCase
from accounting.models import BangLuongThang, ChiTietLuong
from users.models import NhanVien


class AuditPayrollUseCaseTest(TestCase):
    def setUp(self):
        today = timezone.now().date()
        self.nhan_vien = NhanVien.objects.create(
            ma_nhan_vien="AUD001",
            ho_ten="Nhân viên đối soát lương",
            ngay_sinh="1990-01-01",
            trang_thai_lam_viec="CHINHTHUC",
            sdt_chinh="0912345678",
        )
        self.previous_period = BangLuongThang.objects.create(
            ten_bang_luong="Bảng lương tháng trước",
            thang=5,
            nam=today.year,
        )
        self.current_period = BangLuongThang.objects.create(
            ten_bang_luong="Bảng lương tháng hiện tại",
            thang=6,
            nam=today.year,
        )

    def test_audit_payroll_returns_info_without_previous_period(self):
        only_period = BangLuongThang.objects.create(
            ten_bang_luong="Bảng lương đầu kỳ",
            thang=1,
            nam=2030,
        )

        result = AuditPayrollUseCase.execute(
            bang_luong=only_period,
            tenant_id=only_period.tenant_id,
        )

        self.assertEqual(result["status"], "info")
        self.assertEqual(result["anomalies"], [])

    def test_audit_payroll_flags_large_take_home_variance(self):
        ChiTietLuong.objects.create(
            bang_luong=self.previous_period,
            nhan_vien=self.nhan_vien,
            thuc_lanh=Decimal("1000000"),
        )
        ChiTietLuong.objects.create(
            bang_luong=self.current_period,
            nhan_vien=self.nhan_vien,
            thuc_lanh=Decimal("1500000"),
        )

        result = AuditPayrollUseCase.execute(
            bang_luong=self.current_period,
            tenant_id=self.current_period.tenant_id,
        )

        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["summary"]["total_checked"], 1)
        self.assertEqual(result["summary"]["anomaly_count"], 1)
        self.assertEqual(result["anomalies"][0]["ma_nv"], self.nhan_vien.ma_nhan_vien)
