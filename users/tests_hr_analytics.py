# -*- coding: utf-8 -*-
"""
SCMD Pro - HR Analytics Regression Tests
-----------------------------------------
Kiểm thử Rule 9 (Organization scoping) và Rule 8 (Performance aggregate).
"""

from datetime import date
from django.test import TestCase
from django.conf import settings
from django.core.cache import cache
from users.models import NhanVien, PhongBan
from users.application.hr_analytics_use_cases import HRAnalyticsUseCase

class HRAnalyticsScopingTest(TestCase):
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.other_tenant = "00000000-0000-0000-0000-000000000002"
        
        # 1. Tạo dữ liệu cho Tenant hiện tại
        self.pb_main = PhongBan.objects.create(ten_phong_ban="Phòng Chính", tenant_id=self.tenant_id)
        NhanVien.objects.create(
            ho_ten="Nhân viên chính", 
            ma_nhan_vien="NV-MAIN",
            phong_ban=self.pb_main,
            ngay_vao_lam=date(2026, 1, 1),
            tenant_id=self.tenant_id
        )

        # 2. Tạo dữ liệu rò rỉ (Other tenant)
        self.pb_other = PhongBan.objects.create(ten_phong_ban="Phòng Lạ", tenant_id=self.other_tenant)
        NhanVien.objects.create(
            ho_ten="Nhân viên lạ", 
            ma_nhan_vien="NV-LEAK",
            phong_ban=self.pb_other,
            ngay_vao_lam=date(2026, 1, 1),
            tenant_id=self.other_tenant
        )
        
        cache.clear()

    def test_hr_turnover_report_enforces_tenant_isolation(self):
        """Rule 9: Báo cáo HR không được phép hiển thị dữ liệu của tổ chức khác."""
        # Thực thi report cho tenant chính
        result = HRAnalyticsUseCase.get_turnover_report_by_region(
            month=6, year=2026, tenant_id=self.tenant_id
        )

        # Kiểm tra Summary (SSOT Aggregate)
        self.assertEqual(result["summary"]["total_start"], 1, "Summary đếm nhầm nhân viên tổ chức khác!")
        
        # Kiểm tra chi tiết phòng ban (Annotate query)
        self.assertEqual(len(result["details"]), 1)
        self.assertEqual(result["details"][0]["region_name"], "Phòng Chính")
        self.assertNotIn("Phòng Lạ", [d["region_name"] for d in result["details"]])

    def test_hr_turnover_report_is_n_plus_one_safe(self):
        """Rule 8: Thống kê biến động nhân sự phải dùng Conditional Aggregation (O(1) queries)."""
        # Baseline: 2 query (1 PhongBan + 1 NhanVien aggregate)
        with self.assertNumQueries(2):
            HRAnalyticsUseCase.get_turnover_report_by_region(
                month=6, year=2026, tenant_id=self.tenant_id
            )
            
        # Thêm 5 phòng ban nữa
        for i in range(5):
            PhongBan.objects.create(ten_phong_ban=f"Phòng {i}", tenant_id=self.tenant_id)
            
        # Query count phải không đổi (nhờ annotate và aggregate thay vì vòng lặp)
        cache.clear()
        with self.assertNumQueries(2):
            HRAnalyticsUseCase.get_turnover_report_by_region(
                month=6, year=2026, tenant_id=self.tenant_id
            )