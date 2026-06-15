# -*- coding: utf-8 -*-
"""
SCMD Pro - Payroll Lock Use Case Tests
--------------------------------------
Kiểm tra toàn diện nghiệp vụ khóa bảng lương: Permission, Idempotency, Audit và Data Integrity.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.models import User
from django.conf import settings
from accounting.models import BangLuongThang, ChiTietLuong
from accounting.application.payroll_lock_use_case import LockPayrollUseCase
from main.models import AuditLog
from users.models import NhanVien

class LockPayrollUseCaseTest(TestCase):
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        # Rule: Cung cấp email duy nhất để tránh clashing email="" trong NhanVien profile (P1)
        self.user_admin = User.objects.create_superuser(
            username="admin_lock", 
            password="password",
            email="admin_lock@scmd.vn"
        )
        self.user_staff = User.objects.create_user(
            username="staff_lock", 
            password="password",
            email="staff_lock@scmd.vn"
        )
        
        # Rule 9: Cưỡng chế organization scope cho profile người dùng (Hệ quả của Single-org Hardening)
        # Tránh trigger SECURITY ALERT trong manager khi signals/policies truy cập profile.
        for user in [self.user_admin, self.user_staff]:
            if hasattr(user, 'nhan_vien'):
                NhanVien.objects.filter(pk=user.nhan_vien.pk).update(tenant_id=self.tenant_id)

        # Tạo nhân sự mẫu
        self.nv, _ = NhanVien.objects.update_or_create(
            ma_nhan_vien="PAY_TEST_01",
            defaults={
                "ho_ten": "Nhân viên đối soát",
                "trang_thai_lam_viec": "CHINHTHUC",
                "tenant_id": self.tenant_id,
                "email": None # Đảm bảo dùng NULL thay vì "" cho trường unique (P1)
            }
        )
        
        # Tạo bảng lương trạng thái CALCULATED
        self.payroll = BangLuongThang.objects.create(
            ten_bang_luong="Bảng lương test locking",
            thang=1,
            nam=2026,
            trang_thai=BangLuongThang.TrangThai.CALCULATED,
            tenant_id=self.tenant_id
        )

    @patch('accounting.application.payroll_lock_use_case.has_role')
    @patch('accounting.application.payroll_lock_use_case.PayrollService.lock_related_records')
    def test_lock_payroll_success_with_audit_trail(self, mock_lock_service, mock_has_role):
        """Happy path: Khóa thành công và ghi Audit Log đầy đủ."""
        mock_has_role.return_value = True
        mock_lock_service.return_value = (True, "OK")
        
        # Rule 6.2: Tạo dữ liệu chi tiết kèm snapshot đối soát
        ChiTietLuong.objects.create(
            bang_luong=self.payroll,
            nhan_vien=self.nv,
            thuc_lanh=5000000,
            nguon_du_lieu_snapshot={"rate_baseline": "7.2M/12h"},
            tenant_id=self.tenant_id
        )
        
        reason = "Chốt lương tháng để phát hành PWA"
        updated_payroll, changed = LockPayrollUseCase.execute(
            payroll_id=self.payroll.id,
            actor_user=self.user_staff,
            tenant_id=self.tenant_id,
            reason=reason
        )
        
        self.assertTrue(changed)
        self.assertEqual(updated_payroll.trang_thai, BangLuongThang.TrangThai.LOCKED)
        
        # Kiểm tra Audit Log (Rule 8.3)
        audit = AuditLog.objects.filter(
            model_name="BangLuongThang",
            object_id=str(self.payroll.id)
        ).latest('timestamp')
        
        self.assertEqual(audit.action, AuditLog.Action.EXECUTE)
        self.assertEqual(audit.changes["after"], BangLuongThang.TrangThai.LOCKED)
        self.assertEqual(audit.changes["reason"], reason)
        self.assertIn(reason, audit.note)

    @patch('accounting.application.payroll_lock_use_case.has_role')
    def test_lock_payroll_permission_denied_for_regular_user(self, mock_has_role):
        """Đảm bảo nhân viên không có role BGĐ/Kế toán bị chặn."""
        mock_has_role.return_value = False
        
        with self.assertRaises(PermissionDenied):
            LockPayrollUseCase.execute(
                payroll_id=self.payroll.id,
                actor_user=self.user_staff,
                tenant_id=self.tenant_id
            )

    def test_lock_payroll_idempotency(self):
        """Đảm bảo gọi khóa trên bảng đã khóa không tạo thay đổi hoặc lỗi."""
        self.payroll.trang_thai = BangLuongThang.TrangThai.LOCKED
        self.payroll.save()
        
        # Superuser mặc định có quyền
        updated_payroll, changed = LockPayrollUseCase.execute(
            payroll_id=self.payroll.id,
            actor_user=self.user_admin,
            tenant_id=self.tenant_id
        )
        
        self.assertFalse(changed)
        self.assertEqual(updated_payroll.trang_thai, BangLuongThang.TrangThai.LOCKED)

    def test_lock_payroll_fails_if_missing_snapshot_integrity(self):
        """Kiểm tra ràng buộc Rule 6.2: Không lock nếu thiếu snapshot đối soát."""
        ChiTietLuong.objects.create(
            bang_luong=self.payroll,
            nhan_vien=self.nv,
            tenant_id=self.tenant_id
            # Không có nguon_du_lieu_snapshot
        )
        
        with self.assertRaisesMessage(ValidationError, "thiếu dữ liệu snapshot đối soát"):
            LockPayrollUseCase.execute(
                payroll_id=self.payroll.id,
                actor_user=self.user_admin,
                tenant_id=self.tenant_id
            )