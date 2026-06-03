# -*- coding: utf-8 -*-
"""
Application Layer: HR Analytics Use Cases.
"""

import calendar
from datetime import date

from django.db.models import Q

from users.domain.analytics import calculate_turnover_rate
from users.models import NhanVien, PhongBan


class HRAnalyticsUseCase:
    """
    Thá»±c hiá»‡n thá»‘ng kÃª vÃ  phÃ¢n tÃ­ch nhÃ¢n sá»±.
    Há»— trá»£ tÃ­nh toÃ¡n tá»· lá»‡ biáº¿n Ä‘á»™ng nhÃ¢n sá»± theo tá»«ng khu vá»±c (PhÃ²ng ban).
    """

    @staticmethod
    def get_turnover_report_by_region(month: int, year: int, tenant_id):
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        regions = PhongBan.objects.all()
        report_data = []

        for region in regions:
            start_count = NhanVien.objects.filter(
                phong_ban=region,
                tenant_id=tenant_id,
                ngay_vao_lam__lt=first_day,
            ).filter(
                Q(ngay_nghi_viec__isnull=True) | Q(ngay_nghi_viec__gte=first_day)
            ).count()

            leaver_count = NhanVien.objects.filter(
                phong_ban=region,
                tenant_id=tenant_id,
                trang_thai_lam_viec="NGHIVIEC",
                ngay_nghi_viec__range=[first_day, last_day],
            ).count()

            end_count = NhanVien.objects.filter(
                phong_ban=region,
                tenant_id=tenant_id,
                ngay_vao_lam__lte=last_day,
            ).filter(
                Q(ngay_nghi_viec__isnull=True) | Q(ngay_nghi_viec__gt=last_day)
            ).count()

            turnover_rate = calculate_turnover_rate(leaver_count, start_count, end_count)

            report_data.append(
                {
                    "region_id": region.id,
                    "region_name": region.ten_phong_ban,
                    "start_count": start_count,
                    "end_count": end_count,
                    "leaver_count": leaver_count,
                    "turnover_rate": turnover_rate,
                }
            )

        report_data.sort(key=lambda x: x["turnover_rate"], reverse=True)

        return {"month": month, "year": year, "details": report_data}
