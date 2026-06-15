# -*- coding: utf-8 -*-
"""
SCMD Pro - Operations Regression Tests
--------------------------------------
Kiểm thử P0: Bảo vệ logic xóa ca trực (Shift Deletion).
Tuân thủ WHITEPAPER v3.5.0 về Operational Truth và Audit Governance.
"""

from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from rolepermissions.roles import assign_role

from main.models import AuditLog
from operations.models import PhanCongCaTruc, ViTriChot, CaLamViec
from clients.models import MucTieu, HopDong
from users.models import LichSuCongTac, NhanVien
from operations.application.shift_management_use_cases import DeleteShiftUseCase


class ShiftDeletionRegressionTest(TestCase):
    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        
        # 1. Tạo Users phục vụ test phân quyền
        self.user_no_perm = User.objects.create_user(username="guard_no_perm", password="password")
        self.user_manager = User.objects.create_user(username="manager_with_perm", password="password")
        
        # Gán role có quyền 'giao_ca_truc' (Ví dụ DoiTruong theo roles.py)
        assign_role(self.user_manager, 'doi_truong')

        # 2. Thiết lập dữ liệu vận hành mẫu
        self.hd = HopDong.objects.create(so_hop_dong="HD-REG-DELETION", tenant_id=self.tenant_id)
        self.manager_staff = self.user_manager.nhan_vien
        self.manager_staff.ho_ten = "Đội trưởng mục tiêu"
        self.manager_staff.ma_nhan_vien = "NV-MGR-001"
        self.manager_staff.tenant_id = self.tenant_id
        self.manager_staff.save()
        self.mt = MucTieu.objects.create(
            hop_dong=self.hd,
            ten_muc_tieu="Mục tiêu Alpha",
            quan_ly_muc_tieu=self.manager_staff,
        )
        self.vt = ViTriChot.objects.create(muc_tieu=self.mt, ten_vi_tri="Cổng chính")
        self.ca = CaLamViec.objects.create(ten_ca="Ca Hành Chính", gio_bat_dau="08:00", gio_ket_thuc="17:00")
        
        self.nv = NhanVien.objects.create(ho_ten="Nhân viên A", ma_nhan_vien="NV001", tenant_id=self.tenant_id)
        LichSuCongTac.objects.create(
            nhan_vien=self.nv,
            muc_tieu=self.mt,
            ngay_bat_dau=date(2026, 1, 1),
            ngay_ket_thuc=None,
        )
        self._grant_shift_permissions(self.user_manager)
        
        # Tạo ca trực mục tiêu để xóa
        self.shift = PhanCongCaTruc.objects.create(
            nhan_vien=self.nv,
            vi_tri_chot=self.vt,
            ca_lam_viec=self.ca,
            ngay_truc=date.today(),
            tenant_id=self.tenant_id
        )
        self.delete_url = reverse('operations:xoa_ca', kwargs={'phan_cong_id': self.shift.pk})

    def _grant_shift_permissions(self, user):
        content_type = ContentType.objects.get_for_model(PhanCongCaTruc)
        permissions = Permission.objects.filter(
            content_type=content_type,
            codename__in=["add_phancongcatruc", "change_phancongcatruc", "delete_phancongcatruc"],
        )
        user.user_permissions.add(*permissions)

    def test_xoa_ca_denied_for_unauthorized_user(self):
        """Bảo mật P0: User không có quyền 'giao_ca_truc' phải bị chặn xóa ca (403)."""
        self.client.login(username="guard_no_perm", password="password")
        
        response = self.client.post(self.delete_url)
        
        # Xác nhận bị chặn và dữ liệu không mất
        self.assertEqual(response.status_code, 403)
        self.assertTrue(PhanCongCaTruc.objects.filter(pk=self.shift.pk).exists())

    def test_xoa_ca_rejects_get_request(self):
        """GET không được phép đi qua mutation path; current decorator chain chặn bằng 403 trước require_POST."""
        self.client.force_login(self.user_manager)
        
        response = self.client.get(self.delete_url)
        
        self.assertEqual(response.status_code, 403)
        self.assertTrue(PhanCongCaTruc.objects.filter(pk=self.shift.pk).exists())

    def test_delete_via_use_case_creates_audit_log(self):
        """Kiến trúc: Xóa ca trực phải thông qua Use Case và tạo AuditLog (Rule 8.2)."""
        # Thực thi logic xóa qua Application Layer
        reason = "Điều chỉnh quân số mục tiêu"
        DeleteShiftUseCase.execute(
            shift_id=self.shift.pk,
            actor_user=self.user_manager,
            reason=reason
        )
        
        # 1. Xác nhận ca đã bị xóa khỏi DB
        self.assertFalse(PhanCongCaTruc.objects.filter(pk=self.shift.pk).exists())
        
        # 2. Xác nhận vết Audit Log được tạo đúng chuẩn
        audit = AuditLog.objects.filter(
            model_name="PhanCongCaTruc",
            object_id=str(self.shift.pk),
            action=AuditLog.Action.DELETE
        ).first()
        
        self.assertIsNotNone(audit, "Lỗi Rule 8.2: Xóa dữ liệu vận hành nhạy cảm mà không tạo AuditLog.")
        self.assertEqual(audit.user, self.user_manager)
        self.assertIn(reason, audit.note)
        self.assertEqual(audit.tenant_id, self.tenant_id)
