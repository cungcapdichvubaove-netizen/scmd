# -*- coding: utf-8 -*-

from datetime import datetime
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from clients.models import HopDong, MucTieu
from main.models import AuditLog
from operations.application.attendance_use_cases import (
    CalculateWorkHoursUseCase,
    CheckInUseCase,
    CheckOutUseCase,
)
from operations.models import CaLamViec, ChamCong, PhanCongCaTruc, ViTriChot


class AttendanceUseCasesTest(TestCase):
    def setUp(self):
        today = timezone.now().date()
        self.today = today
        self.user = User.objects.create_user(
            username="attendance-user",
            email="attendance@example.com",
            password="password",
        )
        self.nhan_vien = self.user.nhan_vien
        self.nhan_vien.ho_ten = "Nhân viên chấm công"
        self.nhan_vien.ngay_sinh = "1990-01-01"
        self.nhan_vien.gioi_tinh = "M"
        self.nhan_vien.sdt_chinh = "0912345678"
        self.nhan_vien.save()

        self.hop_dong = HopDong.objects.create(
            so_hop_dong="HD-ATT-001",
            ngay_ky=today,
            ngay_hieu_luc=today,
            ngay_het_han=today,
            gia_tri=1000000,
        )
        self.muc_tieu = MucTieu.objects.create(
            hop_dong=self.hop_dong,
            ten_muc_tieu="Mục tiêu chấm công",
            dia_chi="Địa chỉ test",
            sdt_lien_he="0123",
            vi_do=10.762622,
            kinh_do=106.660172,
            ban_kinh_cho_phep=100,
        )
        self.vi_tri = ViTriChot.objects.create(
            muc_tieu=self.muc_tieu,
            ten_vi_tri="Cổng chính",
        )
        self.ca_lam = CaLamViec.objects.create(
            ten_ca="Ca sáng",
            gio_bat_dau="06:00",
            gio_ket_thuc="14:00",
        )
        self.phan_cong = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=self.nhan_vien,
            ca_lam_viec=self.ca_lam,
            ngay_truc=today,
        )

    @patch("operations.application.attendance_use_cases.validate_geofence")
    def test_checkin_creates_attendance_and_audit_log(self, mock_validate_geofence):
        mock_validate_geofence.return_value = (True, 12.5)

        success, message, payload, error_code = CheckInUseCase.execute(
            phan_cong=self.phan_cong,
            lat="10.762622",
            lng="106.660172",
            image=None,
            ip="127.0.0.1",
            device_info="test-device",
            note="Ca đầu ngày",
            user=self.user,
        )

        self.assertTrue(success)
        self.assertEqual(error_code, None)
        self.assertEqual(message, "Check-in thành công.")
        self.assertIsNotNone(payload["id"])

        cham_cong = ChamCong.objects.get(ca_truc=self.phan_cong)
        self.assertTrue(cham_cong.vi_tri_hop_le)
        self.assertEqual(cham_cong.khoang_cach_check_in, 12.5)
        self.assertEqual(
            AuditLog.objects.filter(model_name="ChamCong", object_id=str(cham_cong.id)).count(),
            1,
        )

    def test_checkin_rejects_duplicate_checkin(self):
        ChamCong.objects.create(
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.now(),
        )

        success, _, payload, error_code = CheckInUseCase.execute(
            phan_cong=self.phan_cong,
            lat=None,
            lng=None,
            image=None,
            ip="127.0.0.1",
            device_info="test-device",
            user=self.user,
        )

        self.assertFalse(success)
        self.assertEqual(error_code, "ALREADY_CHECKED_IN")
        self.assertIsNotNone(payload["time"])

    def test_checkout_requires_existing_checkin(self):
        success, message, payload, error_code = CheckOutUseCase.execute(
            phan_cong=self.phan_cong,
            lat=None,
            lng=None,
            image=None,
            ip="127.0.0.1",
            device_info="test-device",
            user=self.user,
        )

        self.assertFalse(success)
        self.assertEqual(error_code, "CHECKIN_DATA_NOT_FOUND")
        self.assertEqual(message, "Chưa tìm thấy dữ liệu Check-in.")
        self.assertIsNone(payload)

    @patch("operations.application.attendance_use_cases.process_timesheet_async.delay")
    def test_checkout_updates_shift_and_enqueues_timesheet_processing(self, mock_delay):
        ChamCong.objects.create(
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.now(),
            ghi_chu="Đã vào ca",
        )

        with self.captureOnCommitCallbacks(execute=True):
            success, message, payload, error_code = CheckOutUseCase.execute(
                phan_cong=self.phan_cong,
                lat="10.762622",
                lng="106.660172",
                image=None,
                ip="127.0.0.1",
                device_info="test-device",
                note="Kết thúc ca",
                user=self.user,
            )

        self.assertTrue(success)
        self.assertEqual(error_code, None)
        self.assertEqual(message, "Check-out thành công.")
        self.assertIsNotNone(payload["time"])

        cham_cong = ChamCong.objects.get(ca_truc=self.phan_cong)
        self.assertIsNotNone(cham_cong.thoi_gian_check_out)
        self.assertIn("Kết thúc ca", cham_cong.ghi_chu)
        mock_delay.assert_called_once_with(cham_cong.id)

    def test_calculate_work_hours_returns_zero_for_negative_duration(self):
        cham_cong = ChamCong(
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.make_aware(
                datetime.combine(self.today, datetime.strptime("14:00", "%H:%M").time())
            ),
            thoi_gian_check_out=timezone.make_aware(
                datetime.combine(self.today, datetime.strptime("06:00", "%H:%M").time())
            ),
        )

        self.assertEqual(CalculateWorkHoursUseCase.execute(cham_cong), 0.0)
