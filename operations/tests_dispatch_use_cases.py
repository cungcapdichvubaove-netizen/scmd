# -*- coding: utf-8 -*-
from datetime import timedelta
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.utils import timezone

from clients.models import HopDong, MucTieu
from main.models import AuditLog
from operations.application.dispatch_use_cases import TransferStaffUseCase
from users.models import LichSuCongTac, NhanVien

ORG_ID = UUID("00000000-0000-0000-0000-000000000811")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class TransferStaffUseCaseTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager_user = User.objects.create_user(username="dispatch-manager")
        self.manager = self.manager_user.nhan_vien
        self.manager.ma_nhan_vien = "NV-DISPATCH-MGR"
        self.manager.ho_ten = "Quản lý điều động"
        self.manager.tenant_id = ORG_ID
        self.manager.save()
        self.manager_user.user_permissions.add(Permission.objects.get(codename="change_nhanvien"))

        self.staff_user = User.objects.create_user(username="dispatch-staff")
        self.staff = self.staff_user.nhan_vien
        self.staff.ma_nhan_vien = "NV-DISPATCH-STF"
        self.staff.ho_ten = "Nhân viên điều động"
        self.staff.tenant_id = ORG_ID
        self.staff.save()

        today = timezone.localdate()
        self.contract = HopDong.objects.create(
            so_hop_dong="HD-DISPATCH",
            ngay_ky=today,
            ngay_hieu_luc=today,
            ngay_het_han=today,
            gia_tri=0,
        )
        self.site_a = MucTieu.objects.create(
            hop_dong=self.contract,
            ten_muc_tieu="Site điều động A",
            dia_chi="A",
            quan_ly_muc_tieu=self.manager,
        )
        self.site_b = MucTieu.objects.create(
            hop_dong=self.contract,
            ten_muc_tieu="Site điều động B",
            dia_chi="B",
            quan_ly_muc_tieu=self.manager,
        )
        self.current = LichSuCongTac.objects.create(
            nhan_vien=self.staff,
            muc_tieu=self.site_a,
            ngay_bat_dau=today,
            ngay_ket_thuc=None,
        )

    def test_transfer_closes_current_assignment_creates_new_assignment_and_audit(self):
        effective_date = timezone.localdate() + timedelta(days=1)
        new_assignment = TransferStaffUseCase.execute(
            user=self.manager_user,
            staff=self.staff,
            from_site=self.site_a,
            to_site=self.site_b,
            effective_date=effective_date,
            reason="Tăng cường mục tiêu B",
        )

        self.current.refresh_from_db()
        self.assertEqual(self.current.ngay_ket_thuc, effective_date - timedelta(days=1))
        self.assertEqual(new_assignment.muc_tieu, self.site_b)
        self.assertEqual(new_assignment.ngay_bat_dau, effective_date)
        self.assertTrue(AuditLog.objects.filter(model_name="LichSuCongTac", object_id=str(new_assignment.pk)).exists())

    def test_transfer_requires_active_assignment_at_from_site(self):
        self.current.ngay_ket_thuc = timezone.localdate()
        self.current.save(update_fields=["ngay_ket_thuc"])
        # Keep the employee inside the manager's visible staff scope while making
        # the requested from_site assignment missing. Otherwise the object-scope
        # policy correctly denies access before the use case reaches the
        # "missing current assignment" business validation.
        LichSuCongTac.objects.create(
            nhan_vien=self.staff,
            muc_tieu=self.site_b,
            ngay_bat_dau=timezone.localdate(),
            ngay_ket_thuc=None,
        )

        with self.assertRaisesMessage(Exception, "Không tìm thấy bản ghi công tác hiện tại"):
            TransferStaffUseCase.execute(
                user=self.manager_user,
                staff=self.staff,
                from_site=self.site_a,
                to_site=self.site_b,
                effective_date=timezone.localdate() + timedelta(days=1),
            )

    def test_transfer_rejects_effective_date_before_current_assignment_start(self):
        with self.assertRaisesMessage(Exception, "Ngày hiệu lực điều động không được trước"):
            TransferStaffUseCase.execute(
                user=self.manager_user,
                staff=self.staff,
                from_site=self.site_a,
                to_site=self.site_b,
                effective_date=self.current.ngay_bat_dau - timedelta(days=1),
            )
