# -*- coding: utf-8 -*-
"""
Benchmark payroll batch calculation with synthetic employees.
"""

import time
import uuid
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounting.models import BangLuongThang, CauHinhLuong, ChiTietLuong
from accounting.services.payroll import PayrollService
from clients.models import HopDong, MucTieu
from operations.models import CaLamViec, ChamCong, PhanCongCaTruc, ViTriChot
from users.models import NhanVien


class Command(BaseCommand):
    help = "Benchmark monthly payroll calculation with synthetic 1k/5k/10k staff batches."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sizes",
            nargs="+",
            type=int,
            default=[1000, 5000, 10000],
            help="Employee counts to benchmark.",
        )
        parser.add_argument(
            "--month",
            type=int,
            default=timezone.now().month,
            help="Payroll month for the benchmark dataset.",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=timezone.now().year,
            help="Payroll year for the benchmark dataset.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Iterator chunk size for payroll processing.",
        )
        parser.add_argument(
            "--persist",
            action="store_true",
            help="Keep generated benchmark data instead of rolling it back.",
        )

    def handle(self, *args, **options):
        sizes = options["sizes"]
        month = options["month"]
        year = options["year"]
        batch_size = options["batch_size"]
        persist = options["persist"]

        if not sizes:
            self.stdout.write(self.style.WARNING("No benchmark sizes requested."))
            return

        context_manager = transaction.atomic()
        with context_manager:
            results = []
            for size in sizes:
                result = self._run_single_benchmark(size, month, year, batch_size)
                results.append(result)
                self.stdout.write(
                    f"{size} nhan su | tao du lieu: {result['setup_seconds']:.2f}s | "
                    f"tinh luong: {result['payroll_seconds']:.2f}s | "
                    f"tong: {result['total_seconds']:.2f}s | "
                    f"phieu luong: {result['payslip_count']}"
                )

            if not persist:
                transaction.set_rollback(True)
                self.stdout.write(
                    self.style.WARNING(
                        "Benchmark data was rolled back after measurement."
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING("Benchmark data persisted by request.")
                )

    def _run_single_benchmark(self, size, month, year, batch_size):
        started_at = time.perf_counter()
        benchmark_tag = uuid.uuid4().hex[:8].upper()
        period_date = datetime(year, month, 1).date()

        setup_started_at = time.perf_counter()
        employees = self._create_employees(size, benchmark_tag)
        employee_ids = [employee.id for employee in employees]
        self._create_supporting_data(employee_ids, period_date, benchmark_tag)
        setup_seconds = time.perf_counter() - setup_started_at

        payroll_started_at = time.perf_counter()
        success, message = PayrollService.tinh_luong_thang(
            month,
            year,
            nhan_vien_queryset=NhanVien.objects.filter(id__in=employee_ids),
            batch_size=batch_size,
        )
        payroll_seconds = time.perf_counter() - payroll_started_at

        if not success:
            raise RuntimeError(
                f"Payroll benchmark failed for batch {size}: {message}"
            )

        bang_luong = BangLuongThang.objects.get(thang=month, nam=year)
        payslip_count = ChiTietLuong.objects.filter(
            bang_luong=bang_luong,
            nhan_vien_id__in=employee_ids,
        ).count()

        return {
            "size": size,
            "setup_seconds": setup_seconds,
            "payroll_seconds": payroll_seconds,
            "total_seconds": time.perf_counter() - started_at,
            "payslip_count": payslip_count,
        }

    def _create_employees(self, size, benchmark_tag):
        employees = [
            NhanVien(
                ma_nhan_vien=f"BM{benchmark_tag}{index:05d}",
                ho_ten=f"Benchmark Payroll {benchmark_tag} {index}",
                ngay_sinh="1990-01-01",
                trang_thai_lam_viec=NhanVien.TrangThaiLamViec.CHINH_THUC,
                sdt_chinh=f"0{(900000000 + index) % 1000000000:09d}",
            )
            for index in range(size)
        ]
        created_employees = NhanVien.objects.bulk_create(employees, batch_size=1000)

        CauHinhLuong.objects.bulk_create(
            [
                CauHinhLuong(
                    nhan_vien=employee,
                    phu_cap_trach_nhiem=Decimal("100000"),
                    phu_cap_xang_xe=Decimal("50000"),
                    phu_cap_an_uong=Decimal("50000"),
                )
                for employee in created_employees
            ],
            batch_size=1000,
        )
        return created_employees

    def _create_supporting_data(self, employee_ids, period_date, benchmark_tag):
        hop_dong = HopDong.objects.create(
            so_hop_dong=f"HD-BM-{benchmark_tag}",
            ngay_ky=period_date,
            ngay_hieu_luc=period_date,
            ngay_het_han=period_date,
            gia_tri=Decimal("100000000"),
        )
        muc_tieu = MucTieu.objects.create(
            hop_dong=hop_dong,
            ten_muc_tieu=f"Muc tieu benchmark {benchmark_tag}",
            dia_chi="Benchmark address",
            sdt_lien_he="0123456789",
            luong_khoan_bao_ve=Decimal("7200000"),
            so_gio_mot_ngay=8,
        )
        vi_tri = ViTriChot.objects.create(
            muc_tieu=muc_tieu,
            ten_vi_tri=f"Vi tri benchmark {benchmark_tag}",
        )
        ca_lam = CaLamViec.objects.create(
            ten_ca=f"Ca benchmark {benchmark_tag}",
            gio_bat_dau="06:00",
            gio_ket_thuc="14:00",
        )

        assignments = PhanCongCaTruc.objects.bulk_create(
            [
                PhanCongCaTruc(
                    vi_tri_chot=vi_tri,
                    nhan_vien_id=employee_id,
                    ca_lam_viec=ca_lam,
                    ngay_truc=period_date,
                )
                for employee_id in employee_ids
            ],
            batch_size=1000,
        )

        check_in_time = timezone.make_aware(datetime(year=period_date.year, month=period_date.month, day=period_date.day, hour=6))
        check_out_time = timezone.make_aware(datetime(year=period_date.year, month=period_date.month, day=period_date.day, hour=14))
        ChamCong.objects.bulk_create(
            [
                ChamCong(
                    ca_truc=assignment,
                    thoi_gian_check_in=check_in_time,
                    thoi_gian_check_out=check_out_time,
                    thuc_lam_gio=8,
                )
                for assignment in assignments
            ],
            batch_size=1000,
        )
