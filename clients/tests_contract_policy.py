# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from clients.models import HopDong
from main.models import AuditLog


class ContractTransitionPolicyTest(TestCase):
    def test_closed_contract_cannot_be_reopened_directly(self):
        today = timezone.localdate()
        contract = HopDong.objects.create(
            so_hop_dong="HD-STATE-001",
            ngay_ky=today,
            ngay_hieu_luc=today,
            ngay_het_han=today,
            gia_tri=1000000,
            trang_thai="HIEU_LUC",
        )
        contract.trang_thai = "DA_THANH_LY"
        contract.save(update_fields=["trang_thai"])

        contract.trang_thai = "HIEU_LUC"
        with self.assertRaises(ValidationError):
            contract.save(update_fields=["trang_thai"])

    def test_contract_status_change_writes_audit_log(self):
        today = timezone.localdate()
        user = User.objects.create_user(username="contract-admin", password="password")
        contract = HopDong.objects.create(
            so_hop_dong="HD-STATE-002",
            ngay_ky=today,
            ngay_hieu_luc=today,
            ngay_het_han=today,
            gia_tri=1000000,
            trang_thai="HIEU_LUC",
        )
        contract._audit_user = user
        contract.trang_thai = "SAP_HET_HAN"
        contract.save(update_fields=["trang_thai"])

        log = AuditLog.objects.filter(model_name="HopDong", object_id=str(contract.pk)).latest("timestamp")
        self.assertEqual(log.user, user)
        self.assertEqual(log.changes["trang_thai"]["before"], "HIEU_LUC")
        self.assertEqual(log.changes["trang_thai"]["after"], "SAP_HET_HAN")

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from clients.admin import HopDongAdmin


class ContractAdminBulkActionPolicyTest(TestCase):
    def test_bulk_close_uses_save_policy_and_writes_audit(self):
        today = timezone.localdate()
        user = User.objects.create_user(username="contract-bulk-admin", password="password")
        contract = HopDong.objects.create(
            so_hop_dong="HD-BULK-001",
            ngay_ky=today,
            ngay_hieu_luc=today,
            ngay_het_han=today,
            gia_tri=1000000,
            trang_thai="HIEU_LUC",
        )
        admin_obj = HopDongAdmin(HopDong, AdminSite())
        admin_obj.message_user = lambda *args, **kwargs: None
        request = RequestFactory().post("/admin/clients/hopdong/")
        request.user = user

        admin_obj.mark_as_closed(request, HopDong.objects.filter(pk=contract.pk))

        contract.refresh_from_db()
        self.assertEqual(contract.trang_thai, "DA_THANH_LY")
        self.assertTrue(
            AuditLog.objects.filter(
                model_name="HopDong",
                object_id=str(contract.pk),
                changes__trang_thai__after="DA_THANH_LY",
            ).exists()
        )

    def test_bulk_reopen_closed_contract_is_blocked_by_policy(self):
        today = timezone.localdate()
        user = User.objects.create_user(username="contract-bulk-denied", password="password")
        contract = HopDong.objects.create(
            so_hop_dong="HD-BULK-002",
            ngay_ky=today,
            ngay_hieu_luc=today,
            ngay_het_han=today,
            gia_tri=1000000,
            trang_thai="HIEU_LUC",
        )
        contract.trang_thai = "DA_THANH_LY"
        contract.save(update_fields=["trang_thai"])

        admin_obj = HopDongAdmin(HopDong, AdminSite())
        admin_obj.message_user = lambda *args, **kwargs: None
        request = RequestFactory().post("/admin/clients/hopdong/")
        request.user = user

        admin_obj.mark_as_active(request, HopDong.objects.filter(pk=contract.pk))

        contract.refresh_from_db()
        self.assertEqual(contract.trang_thai, "DA_THANH_LY")
