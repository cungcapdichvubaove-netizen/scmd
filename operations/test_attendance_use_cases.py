# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import RequestFactory
from django.test import TestCase
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounting.models import BangLuongThang
from clients.models import HopDong, MucTieu
from main.models import AuditLog
from users.models import NhanVien
from operations.api_serializers import CheckInCheckOutSerializer
from operations.admin import ChamCongAdmin
from operations.application.attendance_correction_use_cases import CorrectAttendanceUseCase
from operations.application.attendance_policies import AttendanceWindowPolicy
from operations.application.attendance_use_cases import (
    CalculateWorkHoursUseCase,
    CheckInUseCase,
    CheckOutUseCase,
    TriggerSOSUseCase,
)
from operations.models import CaLamViec, ChamCong, ChamCongAdjustment, PhanCongCaTruc, ViTriChot


class AttendanceUseCasesTest(TestCase):
    def setUp(self):
        today = timezone.now().date()
        self.today = today
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.user = User.objects.create_user(
            username="attendance-user",
            email="attendance@example.com",
            password="password",
        )
        # Refactor (P1): Sử dụng update_or_create để tránh duplicate user_id/email từ signal
        self.nhan_vien, _ = NhanVien.objects.update_or_create(
            user=self.user,
            defaults={
                "ho_ten": "Nhân viên chấm công",
                "ma_nhan_vien": "NV_ATT_001",
                "sdt_chinh": "0912345678",
                "tenant_id": self.tenant_id,
                "email": None # Enforce NULL for unique empty fields (P1)
            }
        )

        self.hop_dong = HopDong.objects.create(
            so_hop_dong="HD-ATT-001",
            ngay_ky=today,
            ngay_hieu_luc=today,
            ngay_het_han=today,
            gia_tri=1000000,
            tenant_id=self.tenant_id,
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
            tenant_id=self.tenant_id,
        )
        self.ca_lam = CaLamViec.objects.create(
            ten_ca="Ca sáng",
            gio_bat_dau="06:00",
            gio_ket_thuc="14:00",
            tenant_id=self.tenant_id,
        )
        self.phan_cong = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.vi_tri,
            nhan_vien=self.nhan_vien,
            ca_lam_viec=self.ca_lam,
            ngay_truc=today,
            tenant_id=self.tenant_id,
        )
        self.admin_site = AdminSite()
        self.request_factory = RequestFactory()

    @patch("operations.application.attendance_use_cases.GeofenceEvaluator.validate")
    def test_checkin_creates_attendance_and_audit_log(self, mock_validate_geofence):
        mock_validate_geofence.return_value.is_within_radius = True
        mock_validate_geofence.return_value.distance_meters = 12.5

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

        cham_cong = ChamCong.objects.for_tenant(self.tenant_id).get(ca_truc=self.phan_cong)
        self.assertTrue(cham_cong.vi_tri_hop_le)
        self.assertEqual(cham_cong.khoang_cach_check_in, 12.5)
        self.assertEqual(
            AuditLog.objects.filter(model_name="ChamCong", object_id=str(cham_cong.id)).count(),
            1,
        )


    @patch("operations.application.attendance_use_cases.GeofenceEvaluator.validate")
    def test_checkin_accepts_zero_coordinates_as_present_gps(self, mock_validate_geofence):
        self.muc_tieu.vi_do = 0
        self.muc_tieu.kinh_do = 0
        self.muc_tieu.save(update_fields=["vi_do", "kinh_do"])
        mock_validate_geofence.return_value.is_within_radius = True
        mock_validate_geofence.return_value.distance_meters = 0

        success, _, payload, error_code = CheckInUseCase.execute(
            phan_cong=self.phan_cong,
            lat=0.0,
            lng=0.0,
            image=None,
            ip="127.0.0.1",
            device_info="test-device",
            user=self.user,
        )

        self.assertTrue(success)
        self.assertIsNone(error_code)
        self.assertIsNotNone(payload)
        mock_validate_geofence.assert_called_once()
        cham_cong = ChamCong.objects.get(ca_truc=self.phan_cong)
        self.assertTrue(cham_cong.vi_tri_hop_le)
        self.assertIsNotNone(cham_cong.location_check_in)

    def test_checkin_rejects_duplicate_checkin(self):
        ChamCong.objects.create(
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.now(),
            tenant_id=self.tenant_id,
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

    @override_settings(ATTENDANCE_REQUIRE_IMAGE_CHECKIN=True)
    def test_checkin_rejects_missing_image_when_policy_requires_photo(self):
        success, message, payload, error_code = CheckInUseCase.execute(
            phan_cong=self.phan_cong,
            lat="10.762622",
            lng="106.660172",
            image=None,
            ip="127.0.0.1",
            device_info="test-device",
            user=self.user,
        )

        self.assertFalse(success)
        self.assertEqual(error_code, "MISSING_REQUIRED_IMAGE")
        self.assertEqual(message, "Ca truc nay bat buoc anh check-in.")
        self.assertIsNone(payload)

    def test_checkin_rejects_demo_gps_marker_note(self):
        success, message, payload, error_code = CheckInUseCase.execute(
            phan_cong=self.phan_cong,
            lat="10.762622",
            lng="106.660172",
            image=None,
            ip="127.0.0.1",
            device_info="test-device",
            note="[DEMO] Fake GPS Used",
            user=self.user,
        )

        self.assertFalse(success)
        self.assertEqual(error_code, "DEMO_GPS_FORBIDDEN")
        self.assertEqual(message, "Khong chap nhan GPS gia lap trong luong check-in.")
        self.assertIsNone(payload)

    @override_settings(
        ATTENDANCE_CHECKIN_EARLY_MINUTES=15,
        ATTENDANCE_CHECKIN_LATE_MINUTES=0,
    )
    def test_checkin_rejects_outside_shift_window(self):
        self.phan_cong.ngay_truc = timezone.now().date() + timedelta(days=1)
        self.phan_cong.save()

        success, _, payload, error_code = CheckInUseCase.execute(
            phan_cong=self.phan_cong,
            lat="10.762622",
            lng="106.660172",
            image=None,
            ip="127.0.0.1",
            device_info="test-device",
            user=self.user,
        )

        self.assertFalse(success)
        self.assertEqual(error_code, "OUTSIDE_CHECKIN_WINDOW")
        self.assertIsNone(payload)

    @override_settings(
        ATTENDANCE_CHECKIN_EARLY_MINUTES=15,
        ATTENDANCE_CHECKIN_LATE_MINUTES=0,
    )
    def test_checkin_policy_allows_late_checkin_until_shift_end(self):
        current_time = timezone.make_aware(
            datetime.combine(self.today, datetime.strptime("13:59", "%H:%M").time())
        )

        is_valid, error = AttendanceWindowPolicy.validate(
            phan_cong=self.phan_cong,
            action=AttendanceWindowPolicy.CHECKIN,
            current_time=current_time,
        )

        self.assertTrue(is_valid)
        self.assertIsNone(error)

    @override_settings(
        ATTENDANCE_CHECKIN_EARLY_MINUTES=15,
        ATTENDANCE_CHECKIN_LATE_MINUTES=10,
    )
    def test_checkin_policy_allows_grace_minutes_after_shift_end(self):
        current_time = timezone.make_aware(
            datetime.combine(self.today, datetime.strptime("14:05", "%H:%M").time())
        )

        is_valid, error = AttendanceWindowPolicy.validate(
            phan_cong=self.phan_cong,
            action=AttendanceWindowPolicy.CHECKIN,
            current_time=current_time,
        )

        self.assertTrue(is_valid)
        self.assertIsNone(error)

    @override_settings(
        ATTENDANCE_CHECKIN_EARLY_MINUTES=15,
        ATTENDANCE_CHECKIN_LATE_MINUTES=10,
    )
    def test_checkin_policy_rejects_after_grace_window(self):
        current_time = timezone.make_aware(
            datetime.combine(self.today, datetime.strptime("14:11", "%H:%M").time())
        )

        is_valid, error = AttendanceWindowPolicy.validate(
            phan_cong=self.phan_cong,
            action=AttendanceWindowPolicy.CHECKIN,
            current_time=current_time,
        )

        self.assertFalse(is_valid)
        self.assertEqual(error, "Chua den khung gio check-in hop le cho ca truc nay.")

    @patch("operations.application.attendance_use_cases.ChamCong.objects.select_for_update")
    @patch("operations.application.attendance_use_cases.ChamCong.objects.get_or_create")
    def test_checkin_maps_integrity_race_to_already_checked_in(
        self,
        mock_get_or_create,
        mock_select_for_update,
    ):
        existing_cham_cong = ChamCong.objects.create(
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.now(),
            tenant_id=self.tenant_id,
        )
        mock_get_or_create.side_effect = IntegrityError("duplicate key")
        mock_select_for_update.return_value.get.return_value = existing_cham_cong

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
        self.assertEqual(payload["time"], existing_cham_cong.thoi_gian_check_in)

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

    @override_settings(ATTENDANCE_REQUIRE_IMAGE_CHECKOUT=True)
    def test_checkout_rejects_missing_image_when_policy_requires_photo(self):
        ChamCong.objects.create(
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.now(),
            tenant_id=self.tenant_id,
        )

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
        self.assertEqual(error_code, "MISSING_REQUIRED_IMAGE")
        self.assertEqual(message, "Ca truc nay bat buoc anh check-out.")
        self.assertIsNone(payload)

    def test_checkout_rejects_demo_gps_marker_note(self):
        ChamCong.objects.create(
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.now(),
            tenant_id=self.tenant_id,
        )

        success, message, payload, error_code = CheckOutUseCase.execute(
            phan_cong=self.phan_cong,
            lat="10.762622",
            lng="106.660172",
            image=None,
            ip="127.0.0.1",
            device_info="test-device",
            note="[DEMO] Fake GPS Used",
            user=self.user,
        )

        self.assertFalse(success)
        self.assertEqual(error_code, "DEMO_GPS_FORBIDDEN")
        self.assertEqual(message, "Khong chap nhan GPS gia lap trong luong check-out.")
        self.assertIsNone(payload)

    @patch("operations.application.attendance_use_cases.process_timesheet_async.delay")
    def test_checkout_updates_shift_and_enqueues_timesheet_processing(self, mock_delay):
        ChamCong.objects.create(
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.now(),
            ghi_chu="Đã vào ca",
            tenant_id=self.tenant_id,
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

        cham_cong = ChamCong.objects.for_tenant(self.tenant_id).get(ca_truc=self.phan_cong)
        self.assertIsNotNone(cham_cong.thoi_gian_check_out)
        self.assertIn("Kết thúc ca", cham_cong.ghi_chu)
        mock_delay.assert_called_once_with(cham_cong.id)

    def test_trigger_sos_requires_real_gps_coordinates(self):
        success, message, payload, error_code = TriggerSOSUseCase.execute(
            self.nhan_vien,
            lat=None,
            lng=None,
        )

        self.assertFalse(success)
        self.assertEqual(error_code, "MISSING_REQUIRED_GPS")
        self.assertEqual(
            message,
            "Khong the gui SOS khi thieu GPS thuc. Vui long bat dinh vi va thu lai.",
        )
        self.assertIsNone(payload)

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

    def test_admin_blocks_direct_attendance_edit_when_payroll_locked(self):
        cham_cong = ChamCong.objects.create(
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.now(),
            tenant_id=self.tenant_id,
        )
        BangLuongThang.objects.create(
            ten_bang_luong=f"Bang luong {self.today.month}/{self.today.year}",
            thang=self.today.month,
            nam=self.today.year,
            trang_thai=BangLuongThang.TrangThai.LOCKED,
            tenant_id=self.tenant_id,
        )
        request = self.request_factory.get("/admin/operations/chamcong/")
        request.user = self.user
        model_admin = ChamCongAdmin(ChamCong, self.admin_site)

        self.assertFalse(model_admin.has_change_permission(request, cham_cong))


    def test_direct_sensitive_attendance_edit_is_blocked_without_audit_context(self):
        cham_cong = ChamCong.objects.create(
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.now(),
            ghi_chu="Ban dau",
            tenant_id=self.tenant_id,
        )

        cham_cong.ghi_chu = "Sua truc tiep khong audit"

        with self.assertRaisesMessage(ValidationError, "application use case có audit trail"):
            cham_cong.save(update_fields=["ghi_chu"])

        self.assertFalse(
            ChamCongAdjustment.objects.for_tenant(self.tenant_id).filter(cham_cong=cham_cong).exists()
        )

    def test_attendance_correction_use_case_creates_adjustment_and_audit(self):
        cham_cong = ChamCong.objects.create(
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.now(),
            ghi_chu="Ban dau",
            tenant_id=self.tenant_id,
        )
        cham_cong_candidate = ChamCong.objects.get(pk=cham_cong.pk)
        cham_cong_candidate.ghi_chu = "Da dieu chinh"

        corrected = CorrectAttendanceUseCase.execute(
            cham_cong_id=cham_cong.pk,
            candidate=cham_cong_candidate,
            changed_fields=["ghi_chu"],
            reason="Cap nhat ghi chu doi soat",
            actor_user=self.user,
        )

        self.assertEqual(corrected.ghi_chu, "Da dieu chinh")
        self.assertEqual(cham_cong.adjustments.filter(tenant_id=self.tenant_id).count(), 1)
        self.assertTrue(
            AuditLog.objects.filter(
                model_name="ChamCong",
                object_id=str(cham_cong.pk),
                action=AuditLog.Action.UPDATE,
            ).exists()
        )

    def test_locked_payroll_blocks_assignment_mutation(self):
        BangLuongThang.objects.create(
            ten_bang_luong="Kỳ đã khóa",
            thang=self.today.month,
            nam=self.today.year,
            trang_thai=BangLuongThang.TrangThai.LOCKED,
            tenant_id=self.tenant_id,
        )

        self.phan_cong.ghi_chu_test_runtime = "ignored"
        with self.assertRaises(ValidationError):
            self.phan_cong.save()

    def test_locked_payroll_blocks_new_attendance_and_correction(self):
        BangLuongThang.objects.create(
            ten_bang_luong="Kỳ đã khóa",
            thang=self.today.month,
            nam=self.today.year,
            trang_thai=BangLuongThang.TrangThai.LOCKED,
            tenant_id=self.tenant_id,
        )

        with self.assertRaises(ValidationError):
            ChamCong.objects.create(
                ca_truc=self.phan_cong,
                thoi_gian_check_in=timezone.now(),
                tenant_id=self.tenant_id,
            )

    def test_manual_correction_audit_contains_reason_and_before_after(self):
        cham_cong = ChamCong.objects.create(
            ca_truc=self.phan_cong,
            thoi_gian_check_in=timezone.now(),
            thuc_lam_gio=1,
            ghi_chu="before",
            tenant_id=self.tenant_id,
        )
        candidate = ChamCong.objects.get(pk=cham_cong.pk)
        candidate.ghi_chu = "after"

        CorrectAttendanceUseCase.execute(
            cham_cong_id=cham_cong.pk,
            candidate=candidate,
            changed_fields=["ghi_chu"],
            reason="Đối soát phiếu trực giấy",
            actor_user=self.user,
        )

        audit = AuditLog.objects.filter(
            model_name="ChamCong",
            object_id=str(cham_cong.pk),
            changes__correction_type="MANUAL_ATTENDANCE_CORRECTION",
        ).latest("created_at")
        self.assertEqual(audit.status, "SUCCESS")
        self.assertEqual(audit.changes["reason"], "Đối soát phiếu trực giấy")
        self.assertEqual(audit.changes["before"]["ghi_chu"], "before")
        self.assertEqual(audit.changes["after"]["ghi_chu"], "after")


class AttendanceApiAccessPolicyTest(TestCase):
    def setUp(self):
        today = timezone.now().date()
        self.api_client = APIClient()

        self.owner_user = User.objects.create_user(
            username="owner-user",
            email="owner@example.com",
            password="password",
        )
        self.other_user = User.objects.create_user(
            username="other-user",
            email="other@example.com",
            password="password",
        )

        # Rule: Luôn chỉ định ma_nhan_vien và sdt_chinh duy nhất để tránh clash trong môi trường test (P1)
        self.owner_nhan_vien, _ = NhanVien.objects.update_or_create(
            user=self.owner_user,
            defaults={
                "ho_ten": "Nhan vien A",
                "ma_nhan_vien": "NV_OWNER_001",
                "sdt_chinh": "0911111111",
                "tenant_id": settings.SCMD_ORGANIZATION_ID,
                "email": "owner@scmd.vn"
            }
        )

        self.other_nhan_vien, _ = NhanVien.objects.update_or_create(
            user=self.other_user,
            defaults={
                "ho_ten": "Nhan vien B",
                "ma_nhan_vien": "NV_OTHER_002",
                "sdt_chinh": "0922222222",
                "tenant_id": settings.SCMD_ORGANIZATION_ID,
                "email": "other@scmd.vn"
            }
        )

        hop_dong = HopDong.objects.create(
            so_hop_dong="HD-API-001",
            ngay_ky=today,
            ngay_hieu_luc=today,
            ngay_het_han=today,
            gia_tri=1000000,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )
        muc_tieu = MucTieu.objects.create(
            hop_dong=hop_dong,
            ten_muc_tieu="Muc tieu API",
            dia_chi="Dia chi API",
            sdt_lien_he="0123",
            vi_do=10.762622,
            kinh_do=106.660172,
            ban_kinh_cho_phep=100,
        )
        vi_tri = ViTriChot.objects.create(
            muc_tieu=muc_tieu,
            ten_vi_tri="Cong phu",
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )
        ca_lam = CaLamViec.objects.create(
            ten_ca="Ca API",
            gio_bat_dau="06:00",
            gio_ket_thuc="14:00",
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )
        self.phan_cong = PhanCongCaTruc.objects.create(
            vi_tri_chot=vi_tri,
            nhan_vien=self.owner_nhan_vien,
            ca_lam_viec=ca_lam,
            ngay_truc=today,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )

    def test_checkin_api_blocks_checkin_for_other_employee_shift(self):
        self.api_client.force_authenticate(self.other_user)

        response = self.api_client.post(
            "/operations/api/v1/mobile/checkin/",
            {
                "ca_truc_id": self.phan_cong.id,
                "lat": "10.762622",
                "lng": "106.660172",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error_code"], "SHIFT_ACCESS_DENIED")
        self.assertFalse(ChamCong.objects.filter(ca_truc=self.phan_cong).exists())


class CheckInCheckOutSerializerTest(TestCase):
    """
    Kiểm thử CheckInCheckOutSerializer (Interface Layer) 
    để đảm bảo scoping dữ liệu đầu vào (Rule 9).
    """
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        
        self.user_a = User.objects.create_user(username="user_a_srl", password="password")
        self.nv_a, _ = NhanVien.objects.update_or_create(
            user=self.user_a,
            defaults={
                "ho_ten": "Nhân viên A",
                "ma_nhan_vien": "NV_A_SRL",
                "tenant_id": self.tenant_id,
            }
        )
        
        self.user_b = User.objects.create_user(username="user_b_srl", password="password")
        self.nv_b, _ = NhanVien.objects.update_or_create(
            user=self.user_b,
            defaults={
                "ho_ten": "Nhân viên B",
                "ma_nhan_vien": "NV_B_SRL",
                "tenant_id": self.tenant_id,
            }
        )
        
        # Setup hạ tầng mẫu
        self.hd = HopDong.objects.create(so_hop_dong="HD-SRL-TEST", tenant_id=self.tenant_id)
        self.mt = MucTieu.objects.create(hop_dong=self.hd, ten_muc_tieu="Mục tiêu Serializer")
        self.vt = ViTriChot.objects.create(muc_tieu=self.mt, ten_vi_tri="Chốt A")
        self.ca = CaLamViec.objects.create(ten_ca="Ca 8h", gio_bat_dau="08:00", gio_ket_thuc="16:00")
        
        # Ca trực thuộc về nhân viên A
        self.shift_a = PhanCongCaTruc.objects.create(
            nhan_vien=self.nv_a,
            vi_tri_chot=self.vt,
            ca_lam_viec=self.ca,
            ngay_truc=timezone.now().date(),
            tenant_id=self.tenant_id
        )

    def test_serializer_blocks_ca_truc_id_not_owned_by_user(self):
        """Xác nhận Serializer chặn ca trực của nhân viên khác thông qua validate_ca_truc_id."""
        factory = RequestFactory()
        # Giả lập request từ nhân viên B
        request = factory.post('/')
        request.user = self.user_b
        
        data = {
            'ca_truc_id': self.shift_a.id,
            'lat': '10.762622',
            'lng': '106.660172'
        }
        
        # Khởi tạo serializer với context request của nhân viên B
        serializer = CheckInCheckOutSerializer(data=data, context={'request': request})
        
        # Phải trả về False và có lỗi tại field ca_truc_id
        self.assertFalse(serializer.is_valid())
        self.assertIn('ca_truc_id', serializer.errors)
        self.assertEqual(
            str(serializer.errors['ca_truc_id'][0]),
            "Ca trực không hợp lệ hoặc bạn không có quyền thao tác."
        )
