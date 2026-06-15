# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Tầng Application: Nghiệp vụ phân tích nhân sự (HR Analytics).
"""

import calendar
from datetime import date
import logging
from django.db.models import Count, Q
from django.core.cache import cache

from ..domain.analytics import calculate_turnover_rate
from users.models import NhanVien, PhongBan

logger = logging.getLogger(__name__)


class HRAnalyticsUseCase:
    """
    Thực hiện thống kê và phân tích nhân sự.
    Hỗ trợ tính toán tỷ lệ biến động nhân sự (Turnover Rate) theo từng khu vực (Phòng ban).
    """

    @staticmethod
    def get_turnover_report_by_region(month: int, year: int, tenant_id):
        # Rule 9: Giới hạn (scoping) cache theo tổ chức, tháng và năm.
        cache_key = f"hr_analytics:turnover:t{tenant_id}:m{month}:y{year}"
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached HR turnover report for month {month}/{year}")
            return cached_result

        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        # Rule 4 & 9: Sử dụng for_tenant() và Conditional Aggregation để lấy dữ liệu thống kê trong 1 query.
        # Đếm các nhân viên liên quan đến từng phòng ban dựa trên các điều kiện thời gian hiệu lực.
        regions = PhongBan.objects.for_tenant(tenant_id).annotate(
            start_count_agg=Count(
                'nhan_vien',
                filter=Q(
                    nhan_vien__ngay_vao_lam__lt=first_day
                ) & (Q(nhan_vien__ngay_nghi_viec__isnull=True) | Q(nhan_vien__ngay_nghi_viec__gte=first_day))
            ),
            leaver_count_agg=Count(
                'nhan_vien',
                filter=Q(
                    nhan_vien__trang_thai_lam_viec="NGHIVIEC",
                    nhan_vien__ngay_nghi_viec__range=[first_day, last_day]
                )
            ),
            end_count_agg=Count(
                'nhan_vien',
                filter=Q(
                    nhan_vien__ngay_vao_lam__lte=last_day
                ) & (Q(nhan_vien__ngay_nghi_viec__isnull=True) | Q(nhan_vien__ngay_nghi_viec__gt=last_day))
            )
        ).only('id', 'ten_phong_ban')

        report_data = []

        for region in regions:
            turnover_rate = calculate_turnover_rate(
                region.leaver_count_agg, region.start_count_agg, region.end_count_agg
            )

            report_data.append({
                    "region_id": region.id,
                    "region_name": region.ten_phong_ban,
                    "start_count": region.start_count_agg,
                    "end_count": region.end_count_agg,
                    "leaver_count": region.leaver_count_agg,
                    "turnover_rate": turnover_rate,
            })

        report_data.sort(key=lambda x: x["turnover_rate"], reverse=True)

        # --- TỔNG HỢP TOÀN TỔ CHỨC (Organization-wide Aggregate) ---
        # Sử dụng aggregate trực tiếp trên Model NhanVien để lấy số liệu tổng hợp (SSOT).
        org_totals = NhanVien.objects.for_tenant(tenant_id).aggregate(
            total_start=Count(
                'id',
                filter=Q(ngay_vao_lam__lt=first_day) & 
                       (Q(ngay_nghi_viec__isnull=True) | Q(ngay_nghi_viec__gte=first_day))
            ),
            total_leaver=Count(
                'id',
                filter=Q(trang_thai_lam_viec="NGHIVIEC", ngay_nghi_viec__range=[first_day, last_day])
            ),
            total_end=Count(
                'id',
                filter=Q(ngay_vao_lam__lte=last_day) & 
                       (Q(ngay_nghi_viec__isnull=True) | Q(ngay_nghi_viec__gt=last_day))
            )
        )

        org_rate = calculate_turnover_rate(
            org_totals["total_leaver"], org_totals["total_start"], org_totals["total_end"]
        )

        result = {
            "month": month, "year": year,
            "summary": {**org_totals, "turnover_rate": org_rate},
            "details": report_data
        }
        
        # Lưu cache trong 1 giờ (Sẽ bị vô hiệu hóa nếu có tín hiệu thay đổi dữ liệu nhân sự).
        cache.set(cache_key, result, 3600)
        return result
