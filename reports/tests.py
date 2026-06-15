# -*- coding: utf-8 -*-

from datetime import datetime
from io import BytesIO
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.test import TestCase
from django.utils import timezone

from main.models import AuditLog
from clients.models import HopDong, MucTieu
from reports.views import export_attendance_excel, tong_hop_cham_cong_thang_view
from operations.models import CaLamViec, ChamCong, PhanCongCaTruc, ViTriChot
from reports.application.report_use_cases import GetMonthlyAttendanceMatrixUseCase
from users.models import ACTIVE_EMPLOYEE_STATUSES, NhanVien


class MonthlyAttendanceMatrixUseCaseTest(TestCase):
    def setUp(self):
        self.today = timezone.now().date()
        self.tenant_id = settings.SCMD_ORGANIZATION_ID

        self.hop_dong = HopDong.objects.create(
            so_hop_dong="HD-RPT-001",
            ngay_ky=self.today,
            ngay_hieu_luc=self.today,
            ngay_het_han=self.today,
            gia_tri=1000000,
        )
        self.muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Muc tieu report",
            dia_chi="Dia chi report",
            sdt_lien_he="0123",
            luong_khoan_bao_ve=7200000,
            so_gio_mot_ngay=8,
        )
        self.vi_tri = ViTriChot.objects.create(
            muc_tieu=self.muc_tieu,
            ten_vi_tri="Cong chinh",
        )
        self.ca_lam = CaLamViec.objects.create(
            ten_ca="Ca ngay",
            gio_bat_dau="06:00",
            gio_ket_thuc="14:00",
        )

    def _create_employee(self, code, name):
        return NhanVien.objects.create(
            ma_nhan_vien=code,
            ho_ten=name,
            ngay_sinh="1990-01-01",
            trang_thai_lam_viec=NhanVien.TrangThaiLamViec.CHINH_THUC,
            sdt_chinh=f"0{code[-9:]}",
        )

    def _create_attendance(self, nhan_vien, day, checked_out=True):
        ngay_truc = self.today.replace(day=day)
        phan_cong = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=nhan_vien,
            ca_lam_viec=self.ca_lam,
            ngay_truc=ngay_truc,
        )
        check_in = timezone.make_aware(
            datetime.combine(ngay_truc, datetime.strptime("06:00", "%H:%M").time())
        )
        check_out = (
            timezone.make_aware(
                datetime.combine(ngay_truc, datetime.strptime("14:00", "%H:%M").time())
            )
            if checked_out
            else None
        )
        return ChamCong.objects.create(
            ca_truc=phan_cong,
            thoi_gian_check_in=check_in,
            thoi_gian_check_out=check_out,
            thuc_lam_gio=8,
        )

    def test_monthly_matrix_groups_attendance_with_single_month_scan(self):
        nv_a = self._create_employee("NV900001", "Nhan vien A")
        nv_b = self._create_employee("NV900002", "Nhan vien B")

        self._create_attendance(nv_a, self.today.day, checked_out=True)
        second_day = 1 if self.today.day != 1 else 2
        self._create_attendance(nv_b, second_day, checked_out=False)

        context = GetMonthlyAttendanceMatrixUseCase.execute(
            self.today.month,
            self.today.year,
            self.tenant_id,
        )

        rows = {row["nhan_vien"].id: row for row in context["report_data"]}
        self.assertEqual(rows[nv_a.id]["days"][self.today.day], "X")
        self.assertEqual(rows[nv_a.id]["total_cong"], 1)
        self.assertEqual(rows[nv_b.id]["days"][second_day], "NoOut")
        self.assertEqual(rows[nv_b.id]["total_cong"], 0)

    def test_monthly_matrix_uses_employee_status_ssot(self):
        active_nv = self._create_employee("NV900003", "Nhan vien active")
        probation_nv = NhanVien.objects.create(
            ma_nhan_vien="NV900005",
            ho_ten="Nhan vien thu viec",
            ngay_sinh="1990-01-01",
            trang_thai_lam_viec=NhanVien.TrangThaiLamViec.THU_VIEC,
            sdt_chinh="0900000005",
        )
        inactive_nv = NhanVien.objects.create(
            ma_nhan_vien="NV900004",
            ho_ten="Nhan vien nghi viec",
            ngay_sinh="1990-01-01",
            trang_thai_lam_viec=NhanVien.TrangThaiLamViec.NGHI_VIEC,
            sdt_chinh="0900000004",
        )

        self._create_attendance(active_nv, self.today.day, checked_out=True)
        self._create_attendance(probation_nv, self.today.day, checked_out=True)
        self._create_attendance(inactive_nv, self.today.day, checked_out=True)

        context = GetMonthlyAttendanceMatrixUseCase.execute(
            self.today.month,
            self.today.year,
            self.tenant_id,
        )

        employee_ids = {row["nhan_vien"].id for row in context["report_data"]}
        self.assertEqual(
            ACTIVE_EMPLOYEE_STATUSES,
            [
                NhanVien.TrangThaiLamViec.CHINH_THUC,
                NhanVien.TrangThaiLamViec.THU_VIEC,
            ],
        )
        self.assertIn(active_nv.id, employee_ids)
        self.assertIn(probation_nv.id, employee_ids)
        self.assertNotIn(inactive_nv.id, employee_ids)


class ReportExportAuditTest(TestCase):
    def setUp(self):
        self.request_factory = RequestFactory()
        self.user = User.objects.create_superuser(
            username="report-admin",
            email="report-admin@example.com",
            password="password",
        )

    @patch("reports.views.ReportService.generate_attendance_excel")
    def test_attendance_export_records_audit_log(self, mock_generate_attendance_excel):
        mock_generate_attendance_excel.return_value = (
            BytesIO(b"fake-excel"),
            "attendance.xlsx",
        )

        request = self.request_factory.get(
            "/reports/export/attendance/excel/?month=6&year=2026"
        )
        request.user = self.user
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        request.META["HTTP_USER_AGENT"] = "test-suite"

        response = export_attendance_excel(request)

        self.assertEqual(response.status_code, 200)
        audit_log = AuditLog.objects.filter(
            user=self.user,
            module="reports",
            model_name="ChamCong",
            note="Export Excel bang cong",
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.ip_address, "127.0.0.1")
        self.assertEqual(audit_log.user_id, self.user.id)
        self.assertEqual(
            audit_log.changes["query_params"],
            {"month": "6", "year": "2026"},
        )
        self.assertIsNotNone(audit_log.timestamp)


class ReportAccessPolicyTest(TestCase):
    def setUp(self):
        self.request_factory = RequestFactory()
        self.user = User.objects.create_user(
            username="report-user",
            email="report-user@example.com",
            password="password",
        )

    def test_attendance_report_requires_privileged_access(self):
        request = self.request_factory.get("/reports/cham-cong/tong-hop/?thang=6&nam=2026")
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            tong_hop_cham_cong_thang_view(request)
