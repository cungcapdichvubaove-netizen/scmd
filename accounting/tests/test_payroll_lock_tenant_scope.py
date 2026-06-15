# -*- coding: utf-8 -*-
"""Regression tests for payroll lock tenant isolation."""

from __future__ import annotations

from uuid import UUID

from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone

from accounting.models import BangLuongThang
from accounting.services.payroll import PayrollService
from inspection.models import BienBanViPham
from inventory.models import PhieuXuat
from users.models import NhanVien


ORG_ID = UUID("00000000-0000-0000-0000-000000000845")
OTHER_ORG_ID = UUID("00000000-0000-0000-0000-000000000846")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class PayrollLockTenantScopeTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.employee = NhanVien.objects.create(
            tenant_id=ORG_ID,
            ma_nhan_vien="PAY-SCOPE-001",
            ho_ten="Nhân viên payroll scope",
            email="pay-scope-001@scmdpro.test",
        )
        self.payroll = BangLuongThang.objects.create(
            tenant_id=ORG_ID,
            ten_bang_luong="Payroll scope guard",
            thang=self.now.month,
            nam=self.now.year,
        )

    def _move_record_to_other_tenant(self, table_name, pk):
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE {table_name} SET tenant_id = %s WHERE id = %s",
                [str(OTHER_ORG_ID), pk],
            )

    def _fetch_field(self, table_name, field_name, pk):
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {field_name} FROM {table_name} WHERE id = %s",
                [pk],
            )
            return cursor.fetchone()[0]

    def test_payroll_lock_related_records_does_not_update_other_tenant_rows(self):
        current_export = PhieuXuat.objects.create(
            tenant_id=ORG_ID,
            ma_phieu="PX-PAY-SCOPE-CURRENT",
            loai_xuat="BAN_TRU_LUONG",
            trang_thai_thanh_toan="CHUA_TRU",
            ngay_xuat=self.now,
            nhan_vien_nhan=self.employee,
        )
        other_export = PhieuXuat.objects.create(
            tenant_id=ORG_ID,
            ma_phieu="PX-PAY-SCOPE-OTHER",
            loai_xuat="BAN_TRU_LUONG",
            trang_thai_thanh_toan="CHUA_TRU",
            ngay_xuat=self.now,
            nhan_vien_nhan=self.employee,
        )
        current_violation = BienBanViPham.objects.create(
            tenant_id=ORG_ID,
            doi_tuong_vi_pham=self.employee,
            ngay_vi_pham=self.now,
            trang_thai="DA_DUYET",
            so_tien_phat=100000,
        )
        other_violation = BienBanViPham.objects.create(
            tenant_id=ORG_ID,
            doi_tuong_vi_pham=self.employee,
            ngay_vi_pham=self.now,
            trang_thai="DA_DUYET",
            so_tien_phat=100000,
        )
        self._move_record_to_other_tenant("inventory_phieuxuat", other_export.pk)
        self._move_record_to_other_tenant("inspection_bienbanvipham", other_violation.pk)

        ok, message = PayrollService.lock_related_records(self.payroll)

        self.assertTrue(ok, message)
        self.assertEqual(
            self._fetch_field("inventory_phieuxuat", "trang_thai_thanh_toan", current_export.pk),
            "DA_TRU",
        )
        self.assertEqual(
            self._fetch_field("inspection_bienbanvipham", "trang_thai", current_violation.pk),
            "DA_KHAU_TRU",
        )
        self.assertEqual(
            self._fetch_field("inventory_phieuxuat", "trang_thai_thanh_toan", other_export.pk),
            "CHUA_TRU",
        )
        self.assertEqual(
            self._fetch_field("inspection_bienbanvipham", "trang_thai", other_violation.pk),
            "DA_DUYET",
        )
