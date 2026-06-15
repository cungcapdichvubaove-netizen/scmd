# -*- coding: utf-8 -*-
"""Regression tests for report/export object scope.

These tests protect the access-scope fixes for reports: report RBAC grants entry
only; querysets and exports still have to obey organization/object scope.
"""

from __future__ import annotations

from datetime import date, datetime, time
from io import BytesIO
from uuid import UUID

import openpyxl
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rolepermissions.roles import assign_role

from clients.models import HopDong, MucTieu
from operations.models import BaoCaoSuCo, CaLamViec, ChamCong, PhanCongCaTruc, ViTriChot
from reports.application.report_use_cases import (
    GetIncidentReportUseCase,
    GetMonthlyAttendanceMatrixUseCase,
    GetTargetAttendanceReportUseCase,
)
from users.models import LichSuCongTac, NhanVien


ORG_ID = UUID("00000000-0000-0000-0000-000000000735")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class ReportAccessScopeRegressionTests(TestCase):
    def setUp(self):
        self.today = timezone.now().date()
        self.month = self.today.month
        self.year = self.today.year
        User = get_user_model()

        self.board_user = User.objects.create_user(
            username="rpt-board",
            email="rpt-board@scmdpro.test",
            password="pass",
        )
        assign_role(self.board_user, "ban_giam_doc")
        self._delete_signal_profile(self.board_user)

        self.area_user = User.objects.create_user(
            username="rpt-area",
            email="rpt-area@scmdpro.test",
            password="pass",
        )
        assign_role(self.area_user, "quan_ly_vung")
        self.area_staff = self._staff("RPT-AREA", "Quản lý vùng", self.area_user)

        self.commander_user = User.objects.create_user(
            username="rpt-commander-a",
            email="rpt-commander-a@scmdpro.test",
            password="pass",
        )
        assign_role(self.commander_user, "doi_truong")
        self.commander_staff = self._staff("RPT-CMD-A", "Đội trưởng A", self.commander_user)

        self.guard_a_user = User.objects.create_user(
            username="rpt-guard-a",
            email="rpt-guard-a@scmdpro.test",
            password="pass",
        )
        self.guard_b_user = User.objects.create_user(
            username="rpt-guard-b",
            email="rpt-guard-b@scmdpro.test",
            password="pass",
        )
        self.guard_a = self._staff("RPT-G-A", "Nhân viên site A", self.guard_a_user)
        self.guard_b = self._staff("RPT-G-B", "Nhân viên site B", self.guard_b_user)

        self.contract = HopDong.objects.create(
            tenant_id=ORG_ID,
            so_hop_dong="HD-RPT-SCOPE-001",
            ngay_ky=date(2026, 1, 1),
            ngay_hieu_luc=date(2026, 1, 1),
            ngay_het_han=date(2026, 12, 31),
            gia_tri=0,
        )
        self.site_a = MucTieu.objects.create(
            hop_dong=self.contract,
            ten_muc_tieu="Mục tiêu báo cáo A",
            dia_chi="Địa chỉ A",
            quan_ly_muc_tieu=self.commander_staff,
            quan_ly_vung=self.area_staff,
        )
        self.site_b = MucTieu.objects.create(
            hop_dong=self.contract,
            ten_muc_tieu="Mục tiêu báo cáo B",
            dia_chi="Địa chỉ B",
        )
        self.post_a = ViTriChot.objects.create(tenant_id=ORG_ID, ten_vi_tri="Chốt A", muc_tieu=self.site_a)
        self.post_b = ViTriChot.objects.create(tenant_id=ORG_ID, ten_vi_tri="Chốt B", muc_tieu=self.site_b)
        self.shift_type = CaLamViec.objects.create(
            tenant_id=ORG_ID,
            ten_ca="Ca báo cáo",
            gio_bat_dau=time(6, 0),
            gio_ket_thuc=time(18, 0),
        )

        self._assign_current_site(self.guard_a, self.site_a)
        self._assign_current_site(self.guard_b, self.site_b)
        self.shift_a = self._shift(self.guard_a, self.post_a)
        self.shift_b = self._shift(self.guard_b, self.post_b)
        self.attendance_a = self._attendance(self.shift_a)
        self.attendance_b = self._attendance(self.shift_b)
        self.incident_a = self._incident("Sự cố scope A", self.guard_a, self.site_a, self.shift_a)
        self.incident_b = self._incident("Sự cố scope B", self.guard_b, self.site_b, self.shift_b)

    def _delete_signal_profile(self, user):
        NhanVien.objects.filter(user=user).delete()
        getattr(user, "_state", None).fields_cache.pop("nhan_vien", None)

    def _staff(self, code, name, user):
        staff = user.nhan_vien
        staff.tenant_id = ORG_ID
        staff.ma_nhan_vien = code
        staff.ho_ten = name
        staff.email = f"{code.lower()}@scmdpro.test"
        staff.trang_thai_lam_viec = NhanVien.TrangThaiLamViec.CHINH_THUC
        staff.save()
        return staff

    def _assign_current_site(self, staff, site):
        return LichSuCongTac.objects.create(
            tenant_id=ORG_ID,
            nhan_vien=staff,
            muc_tieu=site,
            ngay_bat_dau=date(2026, 1, 1),
            ngay_ket_thuc=None,
        )

    def _shift(self, staff, post):
        return PhanCongCaTruc.objects.create(
            tenant_id=ORG_ID,
            nhan_vien=staff,
            vi_tri_chot=post,
            ca_lam_viec=self.shift_type,
            ngay_truc=self.today,
        )

    def _attendance(self, shift):
        check_in = timezone.make_aware(datetime.combine(self.today, time(6, 0)))
        check_out = timezone.make_aware(datetime.combine(self.today, time(18, 0)))
        return ChamCong.objects.create(
            tenant_id=ORG_ID,
            ca_truc=shift,
            thoi_gian_check_in=check_in,
            thoi_gian_check_out=check_out,
            thuc_lam_gio=12,
            vi_tri_hop_le=True,
        )

    def _incident(self, title, reporter, site, shift):
        return BaoCaoSuCo.objects.create(
            tenant_id=ORG_ID,
            tieu_de=title,
            nhan_vien_bao_cao=reporter,
            muc_tieu=site,
            ca_truc=shift,
            mo_ta_chi_tiet=title,
            muc_do="TB",
            trang_thai="CHO_XU_LY",
        )

    def test_board_report_role_without_staff_profile_still_sees_all_targets(self):
        context = GetTargetAttendanceReportUseCase.execute(
            self.month,
            self.year,
            None,
            ORG_ID,
            user=self.board_user,
        )

        target_ids = {target.pk for target in context["muc_tieu_list"]}
        self.assertIn(self.site_a.pk, target_ids)
        self.assertIn(self.site_b.pk, target_ids)

    def test_area_manager_report_scope_contains_only_managed_target_attendance_and_incidents(self):
        target_context = GetTargetAttendanceReportUseCase.execute(
            self.month,
            self.year,
            None,
            ORG_ID,
            user=self.area_user,
        )
        target_ids = {target.pk for target in target_context["muc_tieu_list"]}
        self.assertEqual(target_ids, {self.site_a.pk})

        attendance_context = GetMonthlyAttendanceMatrixUseCase.execute(
            self.month,
            self.year,
            ORG_ID,
            user=self.area_user,
        )
        visible_staff_ids = {row["nhan_vien"].pk for row in attendance_context["report_data"]}
        self.assertIn(self.guard_a.pk, visible_staff_ids)
        self.assertNotIn(self.guard_b.pk, visible_staff_ids)

        incident_qs = GetIncidentReportUseCase.execute(
            self.month,
            self.year,
            ORG_ID,
            paginate=False,
            user=self.area_user,
        )
        self.assertEqual(set(incident_qs.values_list("pk", flat=True)), {self.incident_a.pk})

    def test_site_commander_report_scope_does_not_include_other_site(self):
        target_context = GetTargetAttendanceReportUseCase.execute(
            self.month,
            self.year,
            None,
            ORG_ID,
            user=self.commander_user,
        )
        target_ids = {target.pk for target in target_context["muc_tieu_list"]}
        self.assertEqual(target_ids, {self.site_a.pk})
        self.assertNotIn(self.site_b.pk, target_ids)

    def test_attendance_export_for_scoped_area_manager_excludes_other_site(self):
        self.client.force_login(self.area_user)
        response = self.client.get(
            reverse("reports:export_attendance_excel"),
            {"month": self.month, "year": self.year},
        )

        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content)
        workbook = openpyxl.load_workbook(BytesIO(content))
        worksheet = workbook.active
        exported_values = "\n".join(
            " ".join(str(cell) for cell in row if cell is not None)
            for row in worksheet.iter_rows(values_only=True)
        )
        self.assertIn("Mục tiêu báo cáo A", exported_values)
        self.assertNotIn("Mục tiêu báo cáo B", exported_values)

    def test_incident_csv_export_for_scoped_area_manager_excludes_other_site(self):
        self.client.force_login(self.area_user)
        response = self.client.get(
            reverse("reports:su_co"),
            {"thang": self.month, "nam": self.year, "export": "csv"},
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8-sig")
        self.assertTrue(content.startswith("Thời gian,Mã,Tiêu đề,Mục tiêu,Người báo,Mức độ,Trạng thái,Thiệt hại"))
        self.assertIn("Sự cố scope A", content)
        self.assertNotIn("Sự cố scope B", content)
