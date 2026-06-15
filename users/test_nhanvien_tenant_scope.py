# -*- coding: utf-8 -*-
"""Regression tests for SCMD_ORGANIZATION_ID enforcement on NhanVien."""

from __future__ import annotations

from uuid import UUID, uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings

from users.models import NhanVien


ORG_ID = UUID("00000000-0000-0000-0000-000000000321")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class NhanVienTenantScopeTests(TestCase):
    def _staff(self, code="NV-SCOPE-001", user=None, **kwargs):
        if user is not None:
            try:
                staff = user.nhan_vien
            except NhanVien.DoesNotExist:
                staff = None
            if staff is not None:
                staff.ma_nhan_vien = code
                staff.ho_ten = kwargs.pop("ho_ten", "Nhân viên scope")
                for field, value in kwargs.items():
                    setattr(staff, field, value)
                staff.save()
                return staff
        return NhanVien.objects.create(ma_nhan_vien=code, ho_ten="Nhân viên scope", user=user, **kwargs)

    def test_save_enforces_configured_organization_id(self):
        staff = NhanVien(ma_nhan_vien="NV-SCOPE-SAVE", ho_ten="Sai tenant", tenant_id=uuid4())
        staff.save()
        self.assertEqual(str(staff.tenant_id), str(ORG_ID))

    def test_bulk_create_enforces_configured_organization_id(self):
        NhanVien.objects.bulk_create([
            NhanVien(ma_nhan_vien="NV-SCOPE-BULK", ho_ten="Bulk tenant", tenant_id=uuid4())
        ])
        staff = NhanVien.objects.get(ma_nhan_vien="NV-SCOPE-BULK")
        self.assertEqual(str(staff.tenant_id), str(ORG_ID))

    def test_default_manager_hides_cross_organization_residue(self):
        staff = NhanVien.objects.create(ma_nhan_vien="NV-SCOPE-RAW", ho_ten="Residue")
        rogue_tenant_id = uuid4()
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users_nhanvien SET tenant_id = %s WHERE id = %s",
                [str(rogue_tenant_id), staff.pk],
            )

        self.assertFalse(NhanVien.objects.filter(pk=staff.pk).exists())
        self.assertFalse(NhanVien.objects.for_tenant(rogue_tenant_id).filter(pk=staff.pk).exists())

    def test_signal_created_profile_uses_configured_organization_id(self):
        user = get_user_model().objects.create_user(username="scope-signal-user")
        self.assertEqual(str(user.nhan_vien.tenant_id), str(ORG_ID))

    def test_signal_allows_multiple_users_without_email(self):
        User = get_user_model()
        user_a = User.objects.create_user(username="scope-no-email-a")
        user_b = User.objects.create_user(username="scope-no-email-b")

        user_a.nhan_vien.refresh_from_db()
        user_b.nhan_vien.refresh_from_db()

        self.assertIsNone(user_a.nhan_vien.email)
        self.assertIsNone(user_b.nhan_vien.email)
        self.assertEqual(str(user_a.nhan_vien.tenant_id), str(ORG_ID))
        self.assertEqual(str(user_b.nhan_vien.tenant_id), str(ORG_ID))


    def test_bulk_create_normalizes_blank_email_to_none(self):
        NhanVien.objects.bulk_create([
            NhanVien(ma_nhan_vien="NV-EMAIL-BULK-1", ho_ten="Blank email 1", email=""),
            NhanVien(ma_nhan_vien="NV-EMAIL-BULK-2", ho_ten="Blank email 2", email=""),
        ])

        self.assertIsNone(NhanVien.objects.get(ma_nhan_vien="NV-EMAIL-BULK-1").email)
        self.assertIsNone(NhanVien.objects.get(ma_nhan_vien="NV-EMAIL-BULK-2").email)
