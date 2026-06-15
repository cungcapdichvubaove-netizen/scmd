# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro
=======
Security Command (SCMD) System
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
------------------------------
File: operations/tests_alive_check.py
Description: Unit Test cho các Use Cases của Alive Check.
"""

from unittest.mock import patch, MagicMock
<<<<<<< HEAD
from django.test import TestCase, override_settings
=======
from django.test import TestCase
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User

<<<<<<< HEAD
from main.models import AuditLog
from users.models import NhanVien
from operations.models import PhanCongCaTruc, ViTriChot, MucTieu, CaLamViec
from operations.application.alive_check_use_cases import (
    CreateAliveCheckUseCase,
    ProcessAliveCheckResponseUseCase,
)
from operations.models import KiemTraQuanSo
from operations.tasks import operations_auto_expire_alive_check
=======
from users.models import NhanVien
from operations.models import PhanCongCaTruc, ViTriChot, MucTieu, CaLamViec
from operations.application.alive_check_use_cases import CreateAliveCheckUseCase
from operations.models_alive_check import KiemTraQuanSo
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

class CreateAliveCheckUseCaseTest(TestCase):
    """
    Kiểm tra nghiệp vụ khởi tạo Alive Check.
    Trọng tâm: Verify Celery task scheduling logic.
    """

    def setUp(self):
        # Tạo dữ liệu cơ bản để làm tham chiếu FK (Infrastructure dependency)
<<<<<<< HEAD
        self.user_guv = User.objects.create(username="guard1", email="guard1@scmd.vn")
        # Rule: Tận dụng profile do signal tạo hoặc dùng update_or_create để tránh duplicate user_id (P1)
        self.nv_guv, _ = NhanVien.objects.update_or_create(
            user=self.user_guv,
            defaults={
                "ho_ten": "Bảo vệ A", 
                "ma_nhan_vien": "BV_A_001",
                "tenant_id": settings.SCMD_ORGANIZATION_ID,
                "email": "guard1@scmd.vn"
            }
        )
        
        self.user_mgr = User.objects.create(username="manager1", email="manager1@scmd.vn")
        self.nv_mgr, _ = NhanVien.objects.update_or_create(
            user=self.user_mgr,
            defaults={
                "ho_ten": "Đội trưởng B", 
                "ma_nhan_vien": "DT_B_002",
                "tenant_id": settings.SCMD_ORGANIZATION_ID,
                "email": "manager1@scmd.vn"
            }
        )
=======
        self.user_guv = User.objects.create(username="guard1")
        self.nv_guv = NhanVien.objects.create(user=self.user_guv, ho_ten="Bảo vệ A")
        
        self.user_mgr = User.objects.create(username="manager1")
        self.nv_mgr = NhanVien.objects.create(user=self.user_mgr, ho_ten="Đội trưởng B")
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        
        # Tạo context ca trực giả lập
        self.mt = MucTieu.objects.create(ten_muc_tieu="Mục tiêu Test", vi_do=10.0, kinh_do=106.0)
        self.vt = ViTriChot.objects.create(muc_tieu=self.mt, ten_vi_tri="Cổng")
        self.ca = CaLamViec.objects.create(ten_ca="Ca Sáng", gio_bat_dau="06:00", gio_ket_thuc="14:00")
        
        self.ca_truc = PhanCongCaTruc.objects.create(
            nhan_vien=self.nv_guv,
            vi_tri_chot=self.vt,
            ca_lam_viec=self.ca,
            ngay_truc=timezone.now().date(),
            tenant_id=settings.SCMD_ORGANIZATION_ID
        )

    @patch('django.db.transaction.on_commit')
    @patch('operations.tasks.operations_auto_expire_alive_check.apply_async')
    @patch('operations.application.alive_check_use_cases.get_channel_layer')
    def test_execute_schedules_celery_task_with_correct_countdown(self, mock_get_channel, mock_apply_async, mock_on_commit):
        """
        Đảm bảo task tự động hết hạn được lên lịch chính xác 600 giây (10 phút).
        """
        # 1. Thực thi Use Case
        giay_cho_phep = 600
        check_req = CreateAliveCheckUseCase.execute(
            ca_truc=self.ca_truc,
            nguoi_kiem_tra=self.nv_mgr,
            giay_cho_phep=giay_cho_phep
        )

        # 2. Kiểm tra xem transaction.on_commit có được gọi không
        self.assertTrue(mock_on_commit.called, "Phải sử dụng transaction.on_commit để bảo vệ SSOT.")

        # 3. Kích hoạt hàm lambda bên trong on_commit (Vì Django TestCase sẽ rollback transaction)
        # Chúng ta lấy tham số đầu tiên của lệnh gọi on_commit
        callback = mock_on_commit.call_args[0][0]
        callback()

        # 4. Assert: Kiểm tra Celery task được gọi với đúng tham số
        mock_apply_async.assert_called_once_with(
            args=[str(check_req.id)],
            countdown=giay_cho_phep
        )
        
        # 5. Kiểm tra dữ liệu bản ghi
<<<<<<< HEAD
        self.assertEqual(check_req.trang_thai, 'PENDING')
        self.assertEqual(check_req.tenant_id, settings.SCMD_ORGANIZATION_ID)

    def test_process_alive_check_requires_matching_authenticated_user(self):
        check_req = KiemTraQuanSo.objects.create(
            ca_truc=self.ca_truc,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            trang_thai="PENDING",
        )

        success, message = ProcessAliveCheckResponseUseCase.execute(
            check_id=str(check_req.id),
            lat=10.0,
            lon=106.0,
            device_id="device-01",
            user=self.user_mgr,
        )

        self.assertFalse(success)
        self.assertIn("khong duoc phan hoi", message.lower())
        check_req.refresh_from_db()
        self.assertEqual(check_req.trang_thai, "PENDING")
        self.assertIsNone(check_req.thoi_gian_phan_hoi)
        self.assertFalse(
            AuditLog.objects.filter(
                model_name="KiemTraQuanSo",
                object_id=str(check_req.id),
            ).exists()
        )

    def test_process_alive_check_persists_device_id_in_dedicated_field(self):
        check_req = KiemTraQuanSo.objects.create(
            ca_truc=self.ca_truc,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            trang_thai="PENDING",
        )

        success, message = ProcessAliveCheckResponseUseCase.execute(
            check_id=str(check_req.id),
            lat=10.0,
            lon=106.0,
            device_id="device-02",
            user=self.user_guv,
        )

        self.assertTrue(success)
        self.assertIn("thanh cong", message.lower())
        check_req.refresh_from_db()
        self.assertEqual(check_req.device_id_xac_thuc, "device-02")
        self.assertIn("distance=", check_req.toa_do_xac_thuc)
        self.assertNotIn("device=", check_req.toa_do_xac_thuc)

    @override_settings(ALIVE_CHECK_REQUIRE_SELFIE=True)
    def test_process_alive_check_requires_selfie_when_policy_enabled(self):
        check_req = KiemTraQuanSo.objects.create(
            ca_truc=self.ca_truc,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            trang_thai="PENDING",
        )

        success, message = ProcessAliveCheckResponseUseCase.execute(
            check_id=str(check_req.id),
            lat=10.0,
            lon=106.0,
            device_id="device-03",
            user=self.user_guv,
            anh_selfie=None,
        )

        self.assertFalse(success)
        self.assertIn("bat buoc anh selfie", message.lower())
        check_req.refresh_from_db()
        self.assertEqual(check_req.trang_thai, "PENDING")
        self.assertIsNone(check_req.device_id_xac_thuc)

    def test_auto_expire_alive_check_is_idempotent(self):
        """
        Task auto-expire phải chỉ tạo một hiệu ứng nghiệp vụ cho cùng một check.
        Lần gọi lặp sau đó chỉ được no-op để bảo vệ operational truth và audit trail.
        """
        check_req = KiemTraQuanSo.objects.create(
            ca_truc=self.ca_truc,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            trang_thai="PENDING",
        )

        first_result = operations_auto_expire_alive_check.run(str(check_req.id))
        second_result = operations_auto_expire_alive_check.run(str(check_req.id))

        check_req.refresh_from_db()
        self.assertEqual(check_req.trang_thai, "LATE")
        self.assertIn("marked as EXPIRED", first_result)
        self.assertIn("already processed", second_result)
        self.assertEqual(
            AuditLog.objects.filter(
                model_name="KiemTraQuanSo",
                object_id=str(check_req.id),
                note__icontains="quá hạn sau thời gian chờ",
            ).count(),
            1,
        )
=======
        self.assertEqual(check_req.trang_thai, 'CHO_XAC_NHAN')
        self.assertEqual(check_req.tenant_id, settings.SCMD_ORGANIZATION_ID)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
