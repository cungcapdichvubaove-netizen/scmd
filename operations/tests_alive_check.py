# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
File: operations/tests_alive_check.py
Description: Unit Test cho các Use Cases của Alive Check.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User

from users.models import NhanVien
from operations.models import PhanCongCaTruc, ViTriChot, MucTieu, CaLamViec
from operations.application.alive_check_use_cases import CreateAliveCheckUseCase
from operations.models_alive_check import KiemTraQuanSo

class CreateAliveCheckUseCaseTest(TestCase):
    """
    Kiểm tra nghiệp vụ khởi tạo Alive Check.
    Trọng tâm: Verify Celery task scheduling logic.
    """

    def setUp(self):
        # Tạo dữ liệu cơ bản để làm tham chiếu FK (Infrastructure dependency)
        self.user_guv = User.objects.create(username="guard1")
        self.nv_guv = NhanVien.objects.create(user=self.user_guv, ho_ten="Bảo vệ A")
        
        self.user_mgr = User.objects.create(username="manager1")
        self.nv_mgr = NhanVien.objects.create(user=self.user_mgr, ho_ten="Đội trưởng B")
        
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
        self.assertEqual(check_req.trang_thai, 'CHO_XAC_NHAN')
        self.assertEqual(check_req.tenant_id, settings.SCMD_ORGANIZATION_ID)