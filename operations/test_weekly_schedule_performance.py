# -*- coding: utf-8 -*-
"""Performance regression coverage for weekly schedule dashboard."""

from datetime import date

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rolepermissions.roles import assign_role

from clients.models import HopDong, MucTieu
from operations.application.weekly_schedule_use_cases import GetWeeklyScheduleUseCase
from operations.models import CaLamViec, PhanCongCaTruc, ViTriChot
from users.models import NhanVien


class WeeklySchedulePerformanceTest(TestCase):
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.user = User.objects.create_user(username="schedule_manager", password="password")
        assign_role(self.user, "ban_giam_doc")
        self.manager = NhanVien.objects.create(
            user=self.user,
            ho_ten="Quản lý lịch",
            ma_nhan_vien="QL0001",
            tenant_id=self.tenant_id,
            trang_thai_lam_viec="CHINHTHUC",
        )
        self.contract = HopDong.objects.create(so_hop_dong="HD-SCHEDULE-PERF", tenant_id=self.tenant_id)
        self.site = MucTieu.objects.create(hop_dong=self.contract, ten_muc_tieu="Mục tiêu hiệu năng")
        self.shift_type = CaLamViec.objects.create(
            ten_ca="Ca hiệu năng",
            gio_bat_dau="08:00",
            gio_ket_thuc="17:00",
            tenant_id=self.tenant_id,
        )
        for idx in range(5):
            vi_tri = ViTriChot.objects.create(
                muc_tieu=self.site,
                ten_vi_tri=f"Chốt {idx + 1}",
                tenant_id=self.tenant_id,
            )
            guard = NhanVien.objects.create(
                ho_ten=f"Nhân viên {idx + 1}",
                ma_nhan_vien=f"NVPERF{idx + 1:03d}",
                tenant_id=self.tenant_id,
                trang_thai_lam_viec="CHINHTHUC",
            )
            PhanCongCaTruc.objects.create(
                nhan_vien=guard,
                vi_tri_chot=vi_tri,
                ca_lam_viec=self.shift_type,
                ngay_truc=date.today(),
                tenant_id=self.tenant_id,
            )

    def test_weekly_schedule_query_count_is_bounded(self):
        with CaptureQueriesContext(connection) as captured:
            context = GetWeeklyScheduleUseCase.execute(
                user=self.user,
                tenant_id=self.tenant_id,
                date_str=date.today().strftime("%Y-%m-%d"),
                muc_tieu_id=str(self.site.id),
            )
            # Force evaluation of lazy querysets used by the template.
            list(context["ca_lam_viecs"])
            list(context["nhan_viens"])
            list(context["muc_tieus"])

        self.assertLessEqual(
            len(captured),
            12,
            f"Weekly schedule dashboard query count regressed: {len(captured)} queries",
        )
