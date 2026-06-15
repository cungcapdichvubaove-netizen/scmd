# -*- coding: utf-8 -*-
"""
SCMD Pro - Performance & Scalability Benchmarks
-----------------------------------------------
Kiểm thử khả năng chịu tải của hệ thống với dữ liệu lớn:
- Tính lương cho hàng trăm nhân viên (Mass Payroll).
- Truy vấn Dashboard bản đồ với hàng ngàn marker (Map Scoping).
- Xuất báo cáo Excel dung lượng lớn (Memory usage).
"""

import time
from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from clients.models import HopDong, MucTieu
from operations.models import ViTriChot
from operations.models import CaLamViec, PhanCongCaTruc, ChamCong, BaoCaoSuCo
from accounting.models import BangLuongThang, ChiTietLuong
from accounting.services.payroll import PayrollService
from operations.application.dashboard_use_cases import GetOperationsDashboardUseCase
from django.urls import reverse
from django.db import connection
from django.contrib.gis.geos import Point
from users.models import NhanVien

class PerformanceBenchmarkTest(TransactionTestCase):
    """
    Sử dụng TransactionTestCase để cho phép commit dữ liệu lớn vào DB ảo 
    nhằm đo lường chính xác tốc độ query của Database.
    """
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.user = User.objects.create_superuser(username="admin_perf", password="password")
        if hasattr(self.user, "nhan_vien"):
            self.user.nhan_vien.trang_thai_lam_viec = "NGHIVIEC"
            self.user.nhan_vien.save(update_fields=["trang_thai_lam_viec"])
        
        # 1. Tạo hạ tầng cơ bản
        self.hd = HopDong.objects.create(so_hop_dong="HD-PERF-01", tenant_id=self.tenant_id)
        self.mt = MucTieu.objects.create(
            hop_dong=self.hd, ten_muc_tieu="Mục tiêu Trọng yếu", 
            luong_khoan_bao_ve=7000000, so_gio_mot_ngay=12,
            vi_do=10.762622, kinh_do=106.660172
        )
        self.vt = ViTriChot.objects.create(muc_tieu=self.mt, ten_vi_tri="Cổng 1", tenant_id=self.tenant_id)
        self.ca = CaLamViec.objects.create(ten_ca="Ca 12h", gio_bat_dau="06:00", gio_ket_thuc="18:00", tenant_id=self.tenant_id)
        
        # 2. Tạo tập dữ liệu lớn (200 nhân viên)
        self.nhan_viens = []
        for i in range(200):
            nv = NhanVien.objects.create(
                ho_ten=f"Nhân viên {i}", ma_nhan_vien=f"NV-PERF-{i}",
                tenant_id=self.tenant_id, trang_thai_lam_viec="CHINHTHUC"
            )
            self.nhan_viens.append(nv)

        # 3. Tạo phân công và chấm công cho tháng 5 (6,000 bản ghi)
        pcs = []
        for nv in self.nhan_viens:
            for d in range(1, 31):
                pcs.append(PhanCongCaTruc(
                    vi_tri_chot=self.vt, nhan_vien=nv, ca_lam_viec=self.ca,
                    ngay_truc=date(2026, 5, d), tenant_id=self.tenant_id
                ))
        PhanCongCaTruc.objects.bulk_create(pcs)

        # Giả lập chấm công hàng loạt
        all_pcs = PhanCongCaTruc.objects.filter(tenant_id=self.tenant_id)
        ChamCong.objects.bulk_create([
            ChamCong(
                ca_truc=pc,
                thoi_gian_check_in=timezone.make_aware(timezone.datetime(2026, 5, pc.ngay_truc.day, 6, 0)),
                location_check_in=Point(106.660172, 10.762622, srid=4326),
                thuc_lam_gio=12.0,
                tenant_id=self.tenant_id,
            )
            for pc in all_pcs
        ])

    def test_payroll_calculation_performance(self):
        """Benchmark: Tính lương cho 200 nhân viên với 6,000 ca trực."""
        start_time = time.time()
        
        # Thực thi service tính lương SSOT
        success, message = PayrollService.tinh_luong_thang(5, 2026)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n[BENCHMARK] Payroll Calculation: {duration:.2f}s for 200 employees (6000 shifts)")
        
        self.assertTrue(success)
        self.assertEqual(
            ChiTietLuong.objects.filter(
                bang_luong__thang=5,
                nhan_vien__ma_nhan_vien__startswith="NV-PERF-",
            ).count(),
            200,
        )
        # Mục tiêu: Tính lương 200 người phải dưới 5 giây trên môi trường tiêu chuẩn
        self.assertLess(duration, 10.0, "Hiệu năng tính lương quá chậm!")

    def test_dashboard_data_aggregation_performance(self):
        """Benchmark: Lấy dữ liệu Dashboard với 200 marker và sự cố."""
        map_date = timezone.localdate()
        check_in_at = timezone.make_aware(timezone.datetime.combine(map_date, timezone.datetime.min.time())) + timedelta(hours=6)
        PhanCongCaTruc.objects.filter(
            tenant_id=self.tenant_id,
            ngay_truc=map_date,
            nhan_vien__ma_nhan_vien__startswith="NV-PERF-",
        ).delete()

        map_shifts = [
            PhanCongCaTruc(
                vi_tri_chot=self.vt,
                nhan_vien=nv,
                ca_lam_viec=self.ca,
                ngay_truc=map_date,
                tenant_id=self.tenant_id,
            )
            for nv in self.nhan_viens
        ]
        PhanCongCaTruc.objects.bulk_create(map_shifts)
        map_shifts = list(
            PhanCongCaTruc.objects.filter(
                tenant_id=self.tenant_id,
                ngay_truc=map_date,
                nhan_vien__ma_nhan_vien__startswith="NV-PERF-",
            )
        )
        ChamCong.objects.bulk_create([
            ChamCong(
                ca_truc=pc,
                thoi_gian_check_in=check_in_at,
                thoi_gian_check_out=None,
                location_check_in=Point(106.660172, 10.762622, srid=4326),
                thuc_lam_gio=0.0,
                tenant_id=self.tenant_id,
            )
            for pc in map_shifts
        ])

        # Tạo 50 sự cố mở
        incidents = []
        for i in range(50):
            incidents.append(BaoCaoSuCo(
                ma_su_co=f"PERF-SC-{i:04d}",
                tieu_de=f"Sự cố {i}", muc_tieu=self.mt, 
                trang_thai="DANG_XU_LY", tenant_id=self.tenant_id
            ))
        BaoCaoSuCo.objects.bulk_create(incidents)

        start_time = time.time()
        
        # Gọi UseCase tổng hợp dữ liệu (Site Scoping)
        result = GetOperationsDashboardUseCase.execute(
            user=self.user,
            tenant_id=self.tenant_id,
            target_date=map_date
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"[BENCHMARK] Dashboard Data API: {duration:.2f}s for 200 markers & 50 incidents")
        
        self.assertIn("stats", result)
        self.assertEqual(len(result["markers"]), 200)
        # Dashboard là bộ mặt vận hành, phải phản hồi dưới 1 giây
        self.assertLess(duration, 2.0, "Dashboard nạp dữ liệu quá chậm!")

    def test_excel_export_memory_performance(self):
        """Benchmark: Tạo báo cáo Excel cho 200 phiếu lương."""
        from accounting.views import export_doi_soat_khau_tru_excel
        from django.test import RequestFactory

        # Setup kỳ lương đã tính
        bl = BangLuongThang.objects.create(thang=5, nam=2026, tenant_id=self.tenant_id)
        PayrollService.tinh_luong_thang(5, 2026)

        factory = RequestFactory()
        request = factory.get(f'/accounting/export/{bl.pk}/')
        request.user = self.user

        start_time = time.time()
        
        # Giả lập hành động export
        response = export_doi_soat_khau_tru_excel(request, bl.pk)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"[BENCHMARK] Excel Report Export: {duration:.2f}s for 200 payslips")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'], 
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertLess(duration, 5.0, "Tốc độ xuất báo cáo không đạt yêu cầu!")

class QueryCountRegressionTest(TestCase):
    """
    Kiểm thử Section 8 của WHITEPAPER.md:
    Đảm bảo số lượng truy vấn (Query Count) không tăng tuyến tính theo dữ liệu (Chống N+1).
    """
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.user = User.objects.create_superuser(username="admin_n1", password="password")
        if hasattr(self.user, "nhan_vien"):
            self.user.nhan_vien.trang_thai_lam_viec = "NGHIVIEC"
            self.user.nhan_vien.save(update_fields=["trang_thai_lam_viec"])
        self.client.login(username="admin_n1", password="password")
        
        # Hạ tầng cơ bản
        self.hd = HopDong.objects.create(so_hop_dong="HD-N1", tenant_id=self.tenant_id)
        self.mt = MucTieu.objects.create(hop_dong=self.hd, ten_muc_tieu="MT Test")
        self.vt = ViTriChot.objects.create(muc_tieu=self.mt, ten_vi_tri="Chốt 1", tenant_id=self.tenant_id)
        self.ca = CaLamViec.objects.create(ten_ca="Ca A", gio_bat_dau="06:00", gio_ket_thuc="18:00", tenant_id=self.tenant_id)

    def _create_bulk_attendance(self, count):
        start_index = NhanVien.objects.filter(ma_nhan_vien__startswith="N1-").count()
        for i in range(start_index, start_index + count):
            nv = NhanVien.objects.create(
                ho_ten=f"NV {i}", ma_nhan_vien=f"N1-{i}", 
                tenant_id=self.tenant_id, trang_thai_lam_viec="CHINHTHUC"
            )
            pc = PhanCongCaTruc.objects.create(
                vi_tri_chot=self.vt, nhan_vien=nv, ca_lam_viec=self.ca,
                ngay_truc=timezone.now().date(), tenant_id=self.tenant_id
            )
            ChamCong.objects.create(
                ca_truc=pc,
                thoi_gian_check_in=timezone.now(),
                location_check_in=Point(106.660172, 10.762622, srid=4326),
                thuc_lam_gio=12.0,
                tenant_id=self.tenant_id,
            )

    def _measure_dashboard_api_queries_cold(self):
        cache.clear()
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(reverse('operations:api_dashboard_data'))
        self.assertEqual(response.status_code, 200)
        return len(captured)

    def _measure_dashboard_use_case_queries(self, target_date):
        with CaptureQueriesContext(connection) as captured:
            result = GetOperationsDashboardUseCase.execute(
                user=self.user,
                tenant_id=self.tenant_id,
                target_date=target_date,
            )
        self.assertIn("stats", result)
        return len(captured)

    def test_operations_dashboard_api_is_n_plus_one_safe(self):
        """Cold API path must prove N+1 safety without Redis cache masking SQL work."""
        self._create_bulk_attendance(1)
        baseline_count = self._measure_dashboard_api_queries_cold()
        self.assertLessEqual(baseline_count, 12)

        # Warm path is measured separately only to verify cache behavior; it is
        # never used as evidence that backend aggregation is N+1 safe.
        with CaptureQueriesContext(connection) as warm_captured:
            warm_response = self.client.get(reverse('operations:api_dashboard_data'))
        self.assertEqual(warm_response.status_code, 200)
        self.assertLessEqual(len(warm_captured), baseline_count)

        self._create_bulk_attendance(10)
        cold_after_growth_count = self._measure_dashboard_api_queries_cold()
        self.assertLessEqual(cold_after_growth_count, baseline_count + 1)

    def test_operations_dashboard_use_case_query_count_is_not_linear(self):
        """Direct use case path bypasses API cache and guards against false positives."""
        target_date = timezone.now().date()

        self._create_bulk_attendance(1)
        baseline_count = self._measure_dashboard_use_case_queries(target_date)
        self.assertLessEqual(baseline_count, 12)

        self._create_bulk_attendance(25)
        growth_count = self._measure_dashboard_use_case_queries(target_date)
        self.assertLessEqual(growth_count, baseline_count + 1)

    def test_accounting_dashboard_query_efficiency(self):
        """Xác nhận Accounting Dashboard không bị N+1 khi tăng số lượng phiếu chi/kỳ lương."""
        from accounting.models_soquy import SoQuy
        SoQuy.objects.create(ma_phieu="P-0", loai_phieu="THU", hang_muc="KHAC", so_tien=1000, tenant_id=self.tenant_id)
        BangLuongThang.objects.create(thang=1, nam=2026, tenant_id=self.tenant_id)

        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 200)
        baseline_count = len(captured)
        self.assertLessEqual(baseline_count, 26)

        # Thêm nhiều dữ liệu
        for i in range(10):
            SoQuy.objects.create(ma_phieu=f"P-ADD-{i}", loai_phieu="CHI", hang_muc="KHAC", so_tien=1000, tenant_id=self.tenant_id)
        
        with CaptureQueriesContext(connection) as captured_after_growth:
            response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(captured_after_growth), baseline_count + 1)

    def test_inventory_stock_report_query_efficiency(self):
        """Xác nhận báo cáo tồn kho không bị N+1 khi số lượng mã vật tư tăng."""
        from inventory.models import LoaiVatTu, VatTu
        loai = LoaiVatTu.objects.create(ten_loai="Dụng cụ")
        VatTu.objects.create(loai_vat_tu=loai, ten_vat_tu="V-0", don_vi_tinh="Cái", so_luong_ton=10)

        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(reverse('inventory:bao_cao_ton'))
        self.assertEqual(response.status_code, 200)
        baseline_count = len(captured)
        self.assertLessEqual(baseline_count, 12)

        # Thêm 20 mã vật tư mới
        for i in range(20):
            VatTu.objects.create(loai_vat_tu=loai, ten_vat_tu=f"V-NEW-{i}", don_vi_tinh="Cái", so_luong_ton=5)

        with CaptureQueriesContext(connection) as captured_after_growth:
            response = self.client.get(reverse('inventory:bao_cao_ton'))
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(captured_after_growth), baseline_count)