# -*- coding: utf-8 -*-
"""Phase E customer payment and receivable settlement tests."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import SimpleTestCase, TestCase
from rolepermissions.roles import assign_role
from django.utils import timezone

from clients.admin import CongNoAdmin, ThanhToanKhachHangAdmin, PhanBoThanhToanHoaDonAdmin, PhanBoThanhToanHoaDonInline
from clients.application.customer_payment_use_cases import (
    AllocateCustomerPaymentUseCase,
    CancelCustomerPaymentUseCase,
    ReceiveCustomerPaymentUseCase,
)
from clients.application.receivable_report_use_cases import CustomerReceivableReportUseCase
from clients.models import (
    CongNo,
    HoaDon,
    HopDong,
    PhanBoThanhToanHoaDon,
    ThanhToanKhachHang,
)
from main.models import AuditLog


class PhaseECustomerPaymentTestMixin:
    def setUp(self):
        self.today = timezone.localdate()
        self.User = get_user_model()
        self.actor = self.User.objects.create_superuser(
            username="phase-e-admin",
            email="phase-e-admin@example.com",
            password="password",
        )
        self.contract = HopDong.objects.create(
            so_hop_dong="HD-E-001",
            ngay_ky=self.today - timedelta(days=30),
            ngay_hieu_luc=self.today - timedelta(days=30),
            ngay_het_han=self.today + timedelta(days=365),
            gia_tri=Decimal("12000000"),
        )
        self.invoice = HoaDon.objects.create(
            hop_dong=self.contract,
            so_hoa_don="INV-E-001",
            ngay_phat_hanh=self.today,
            ngay_den_han=self.today + timedelta(days=10),
            tong_tien=Decimal("1000000"),
            trang_thai=HoaDon.TrangThai.ISSUED,
        )
        self.debt = CongNo.objects.create(
            hoa_don=self.invoice,
            so_tham_chieu="DEBT-E-001",
            ngay_den_han=self.today + timedelta(days=10),
            so_tien_phai_thu=Decimal("1000000"),
            so_tien_da_thu=Decimal("0"),
            trang_thai=CongNo.TrangThai.OPEN,
        )

    def receive_payment(self, code="PAY-E-001", amount=Decimal("1000000")):
        return ReceiveCustomerPaymentUseCase.execute(
            ma_phieu=code,
            so_tien=amount,
            hop_dong=self.contract,
            actor=self.actor,
            tenant_id=self.contract.tenant_id,
        )


class PhaseECustomerPaymentWorkflowTests(PhaseECustomerPaymentTestMixin, TestCase):
    def test_received_unallocated_payment_does_not_mark_invoice_paid(self):
        payment = self.receive_payment(amount=Decimal("1000000"))
        self.invoice.refresh_from_db()
        self.debt.refresh_from_db()

        self.assertEqual(payment.trang_thai, ThanhToanKhachHang.TrangThai.RECEIVED)
        self.assertEqual(self.invoice.trang_thai, HoaDon.TrangThai.ISSUED)
        self.assertEqual(self.debt.trang_thai, CongNo.TrangThai.OPEN)
        self.assertEqual(self.debt.so_tien_da_thu, Decimal("0"))

    def test_partial_allocation_updates_receivable_and_invoice_to_partial(self):
        payment = self.receive_payment(amount=Decimal("1000000"))
        allocation = AllocateCustomerPaymentUseCase.execute(
            thanh_toan=payment,
            cong_no=self.debt,
            so_tien=Decimal("400000"),
            actor=self.actor,
        )
        self.invoice.refresh_from_db()
        self.debt.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(allocation.hoa_don_id, self.invoice.pk)
        self.assertEqual(payment.trang_thai, ThanhToanKhachHang.TrangThai.ALLOCATED)
        self.assertEqual(self.debt.so_tien_da_thu, Decimal("400000"))
        self.assertEqual(self.debt.trang_thai, CongNo.TrangThai.PARTIAL)
        self.assertEqual(self.invoice.trang_thai, HoaDon.TrangThai.PARTIALLY_PAID)

    def test_full_allocation_updates_receivable_and_invoice_to_paid(self):
        payment = self.receive_payment(amount=Decimal("1000000"))
        AllocateCustomerPaymentUseCase.execute(
            thanh_toan=payment,
            cong_no=self.debt,
            so_tien=Decimal("1000000"),
            actor=self.actor,
        )
        self.invoice.refresh_from_db()
        self.debt.refresh_from_db()

        self.assertEqual(self.debt.so_tien_da_thu, Decimal("1000000"))
        self.assertEqual(self.debt.trang_thai, CongNo.TrangThai.PAID)
        self.assertEqual(self.invoice.trang_thai, HoaDon.TrangThai.PAID)

    def test_allocation_cannot_exceed_payment_amount(self):
        payment = self.receive_payment(amount=Decimal("1000000"))
        AllocateCustomerPaymentUseCase.execute(
            thanh_toan=payment,
            cong_no=self.debt,
            so_tien=Decimal("600000"),
            actor=self.actor,
        )
        with self.assertRaises(ValidationError):
            AllocateCustomerPaymentUseCase.execute(
                thanh_toan=payment,
                cong_no=self.debt,
                so_tien=Decimal("500000"),
                actor=self.actor,
            )

    def test_allocation_cannot_exceed_receivable_remaining(self):
        payment = self.receive_payment(amount=Decimal("1500000"))
        with self.assertRaises(ValidationError):
            AllocateCustomerPaymentUseCase.execute(
                thanh_toan=payment,
                cong_no=self.debt,
                so_tien=Decimal("1200000"),
                actor=self.actor,
            )

    def test_cancel_unallocated_payment_allowed_but_allocated_payment_blocked(self):
        payment = self.receive_payment(code="PAY-E-CANCEL", amount=Decimal("1000000"))
        cancelled = CancelCustomerPaymentUseCase.execute(thanh_toan=payment, actor=self.actor)
        self.assertEqual(cancelled.trang_thai, ThanhToanKhachHang.TrangThai.CANCELLED)

        allocated_payment = self.receive_payment(code="PAY-E-BLOCK", amount=Decimal("1000000"))
        AllocateCustomerPaymentUseCase.execute(
            thanh_toan=allocated_payment,
            cong_no=self.debt,
            so_tien=Decimal("1000000"),
            actor=self.actor,
        )
        with self.assertRaises(ValidationError):
            CancelCustomerPaymentUseCase.execute(thanh_toan=allocated_payment, actor=self.actor)

    def test_direct_paid_transition_requires_sufficient_allocation(self):
        with self.assertRaises(ValidationError):
            self.invoice.transition_status(HoaDon.TrangThai.PAID, actor=self.actor)
        with self.assertRaises(ValidationError):
            self.debt.transition_status(CongNo.TrangThai.PAID, actor=self.actor)

    def test_invoice_only_allocation_is_rejected_to_keep_invoice_and_debt_in_sync(self):
        payment = self.receive_payment(amount=Decimal("1000000"))
        with self.assertRaises(ValidationError):
            AllocateCustomerPaymentUseCase.execute(
                thanh_toan=payment,
                hoa_don=self.invoice,
                so_tien=Decimal("100000"),
                actor=self.actor,
            )

        self.invoice.refresh_from_db()
        self.debt.refresh_from_db()
        self.assertEqual(self.invoice.trang_thai, HoaDon.TrangThai.ISSUED)
        self.assertEqual(self.debt.trang_thai, CongNo.TrangThai.OPEN)
        direct_allocation = PhanBoThanhToanHoaDon(
            thanh_toan=payment,
            hoa_don=self.invoice,
            so_tien=Decimal("100000"),
        )
        with self.assertRaises(ValidationError):
            direct_allocation.save()


    def test_allocated_payment_source_fields_are_immutable(self):
        payment = self.receive_payment(amount=Decimal("1000000"))
        AllocateCustomerPaymentUseCase.execute(
            thanh_toan=payment,
            cong_no=self.debt,
            so_tien=Decimal("100000"),
            actor=self.actor,
        )
        payment.refresh_from_db()
        payment.so_tien = Decimal("500000")
        with self.assertRaises(ValidationError):
            payment.save()

        payment.refresh_from_db()
        payment.ma_giao_dich = "EDITED-AFTER-ALLOCATION"
        with self.assertRaises(ValidationError):
            payment.save()

    def test_allocation_source_fields_are_immutable_after_create(self):
        payment = self.receive_payment(amount=Decimal("1000000"))
        allocation = AllocateCustomerPaymentUseCase.execute(
            thanh_toan=payment,
            cong_no=self.debt,
            so_tien=Decimal("100000"),
            actor=self.actor,
        )

        allocation.so_tien = Decimal("200000")
        with self.assertRaises(ValidationError):
            allocation.save()

        other_invoice = HoaDon.objects.create(
            hop_dong=self.contract,
            so_hoa_don="INV-E-IMMUTABLE",
            ngay_phat_hanh=self.today,
            ngay_den_han=self.today + timedelta(days=10),
            tong_tien=Decimal("500000"),
            trang_thai=HoaDon.TrangThai.ISSUED,
        )
        other_debt = CongNo.objects.create(
            hoa_don=other_invoice,
            so_tham_chieu="DEBT-E-IMMUTABLE",
            ngay_den_han=self.today + timedelta(days=10),
            so_tien_phai_thu=Decimal("500000"),
            trang_thai=CongNo.TrangThai.OPEN,
        )
        allocation.refresh_from_db()
        allocation.cong_no = other_debt
        allocation.hoa_don = other_invoice
        with self.assertRaises(ValidationError):
            allocation.save()

    def test_payment_allocation_creates_audit_logs(self):
        payment = self.receive_payment(amount=Decimal("1000000"))
        allocation = AllocateCustomerPaymentUseCase.execute(
            thanh_toan=payment,
            cong_no=self.debt,
            so_tien=Decimal("1000000"),
            actor=self.actor,
        )
        self.assertTrue(AuditLog.objects.filter(model_name="ThanhToanKhachHang", object_id=str(payment.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(model_name="PhanBoThanhToanHoaDon", object_id=str(allocation.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(model_name="CongNo", object_id=str(self.debt.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(model_name="HoaDon", object_id=str(self.invoice.pk)).exists())

    def test_receivable_report_context_contains_overdue_partial_and_totals(self):
        overdue_invoice = HoaDon.objects.create(
            hop_dong=self.contract,
            so_hoa_don="INV-E-OVERDUE",
            ngay_phat_hanh=self.today - timedelta(days=40),
            ngay_den_han=self.today - timedelta(days=5),
            tong_tien=Decimal("500000"),
            trang_thai=HoaDon.TrangThai.ISSUED,
        )
        CongNo.objects.create(
            hoa_don=overdue_invoice,
            so_tham_chieu="DEBT-E-OVERDUE",
            ngay_den_han=self.today - timedelta(days=5),
            so_tien_phai_thu=Decimal("500000"),
            trang_thai=CongNo.TrangThai.OPEN,
        )
        payment = self.receive_payment(amount=Decimal("1000000"))
        AllocateCustomerPaymentUseCase.execute(
            thanh_toan=payment,
            cong_no=self.debt,
            so_tien=Decimal("400000"),
            actor=self.actor,
        )

        report = CustomerReceivableReportUseCase.execute(tenant_id=self.contract.tenant_id, today=self.today, user=self.actor)

        self.assertGreaterEqual(report["overdue_receivables_count"], 1)
        self.assertGreaterEqual(report["partial_paid_invoices_count"], 1)
        self.assertIn("total_open_receivable", report["receivable_totals"])
        self.assertIn("total_collected_allocation", report["receivable_totals"])
        self.assertIn("total_remaining_open_receivable", report["receivable_totals"])
        # Compatibility aliases remain for existing dashboard templates.
        self.assertIn("total_receivable", report["receivable_totals"])
        self.assertIn("total_collected", report["receivable_totals"])
        self.assertIn("total_remaining", report["receivable_totals"])


class PhaseEAuthorizationAndHardeningTests(PhaseECustomerPaymentTestMixin, TestCase):
    def test_regular_user_cannot_receive_allocate_or_cancel_customer_payment(self):
        regular = self.User.objects.create_user(
            username="phase-e-regular",
            email="phase-e-regular@example.com",
            password="password",
        )
        with self.assertRaises(PermissionDenied):
            ReceiveCustomerPaymentUseCase.execute(
                ma_phieu="PAY-E-DENY",
                so_tien=Decimal("1000000"),
                hop_dong=self.contract,
                actor=regular,
                tenant_id=self.contract.tenant_id,
            )

        payment = self.receive_payment(code="PAY-E-AUTHZ", amount=Decimal("1000000"))
        with self.assertRaises(PermissionDenied):
            AllocateCustomerPaymentUseCase.execute(
                thanh_toan=payment,
                cong_no=self.debt,
                so_tien=Decimal("100000"),
                actor=regular,
            )
        with self.assertRaises(PermissionDenied):
            CancelCustomerPaymentUseCase.execute(thanh_toan=payment, actor=regular)

    def test_accounting_role_can_receive_and_allocate_customer_payment(self):
        accountant = self.User.objects.create_user(
            username="phase-e-accountant",
            email="phase-e-accountant@example.com",
            password="password",
        )
        assign_role(accountant, "ke_toan")

        payment = ReceiveCustomerPaymentUseCase.execute(
            ma_phieu="PAY-E-ACCOUNTING",
            so_tien=Decimal("1000000"),
            hop_dong=self.contract,
            actor=accountant,
            tenant_id=self.contract.tenant_id,
        )
        allocation = AllocateCustomerPaymentUseCase.execute(
            thanh_toan=payment,
            cong_no=self.debt,
            so_tien=Decimal("100000"),
            actor=accountant,
        )

        self.assertEqual(payment.trang_thai, ThanhToanKhachHang.TrangThai.RECEIVED)
        self.assertEqual(allocation.nguoi_phan_bo_id, accountant.pk)

    def test_allocation_rejects_cross_contract_target(self):
        other_contract = HopDong.objects.create(
            so_hop_dong="HD-E-OTHER",
            ngay_ky=self.today - timedelta(days=30),
            ngay_hieu_luc=self.today - timedelta(days=30),
            ngay_het_han=self.today + timedelta(days=365),
            gia_tri=Decimal("9000000"),
        )
        other_invoice = HoaDon.objects.create(
            hop_dong=other_contract,
            so_hoa_don="INV-E-OTHER",
            ngay_phat_hanh=self.today,
            ngay_den_han=self.today + timedelta(days=10),
            tong_tien=Decimal("700000"),
            trang_thai=HoaDon.TrangThai.ISSUED,
        )
        other_debt = CongNo.objects.create(
            hoa_don=other_invoice,
            so_tham_chieu="DEBT-E-OTHER",
            ngay_den_han=self.today + timedelta(days=10),
            so_tien_phai_thu=Decimal("700000"),
            trang_thai=CongNo.TrangThai.OPEN,
        )
        payment = self.receive_payment(code="PAY-E-CONTRACT-GUARD", amount=Decimal("1000000"))

        with self.assertRaises(ValidationError):
            AllocateCustomerPaymentUseCase.execute(
                thanh_toan=payment,
                cong_no=other_debt,
                so_tien=Decimal("100000"),
                actor=self.actor,
            )

    def test_receivable_report_requires_authorized_role(self):
        regular = self.User.objects.create_user(
            username="phase-e-report-regular",
            email="phase-e-report-regular@example.com",
            password="password",
        )
        with self.assertRaises(PermissionDenied):
            CustomerReceivableReportUseCase.execute(tenant_id=self.contract.tenant_id, today=self.today, user=regular)

        sales_user = self.User.objects.create_user(
            username="phase-e-report-sales",
            email="phase-e-report-sales@example.com",
            password="password",
        )
        assign_role(sales_user, "nhan_vien_kinh_doanh")
        report = CustomerReceivableReportUseCase.execute(tenant_id=self.contract.tenant_id, today=self.today, user=sales_user)
        self.assertIn("receivable_totals", report)



class PhaseEAdminContractTests(PhaseECustomerPaymentTestMixin, TestCase):
    def test_congno_admin_does_not_allow_direct_edit_of_collected_amount(self):
        model_admin = CongNoAdmin(CongNo, admin.site)
        readonly = model_admin.get_readonly_fields(request=None, obj=self.debt)
        self.assertIn("so_tien_da_thu", readonly)
        self.assertIn("so_tien_con_lai", readonly)

    def test_payment_allocation_admin_delete_is_disabled(self):
        allocation_admin = PhanBoThanhToanHoaDonAdmin(PhanBoThanhToanHoaDon, admin.site)
        self.assertFalse(allocation_admin.has_delete_permission(request=None, obj=None))
        inline = PhanBoThanhToanHoaDonInline(ThanhToanKhachHang, admin.site)
        self.assertFalse(inline.has_delete_permission(request=None, obj=None))
        self.assertFalse(inline.can_delete)


    def test_payment_admin_makes_allocated_source_fields_readonly(self):
        payment = self.receive_payment(code="PAY-E-ADMIN-READONLY", amount=Decimal("1000000"))
        AllocateCustomerPaymentUseCase.execute(
            thanh_toan=payment,
            cong_no=self.debt,
            so_tien=Decimal("100000"),
            actor=self.actor,
        )
        payment.refresh_from_db()
        model_admin = ThanhToanKhachHangAdmin(ThanhToanKhachHang, admin.site)
        readonly = model_admin.get_readonly_fields(request=None, obj=payment)
        for field_name in ("ma_phieu", "so_tien", "khach_hang", "hop_dong", "ngay_thanh_toan", "hinh_thuc", "ma_giao_dich", "file_chung_tu"):
            self.assertIn(field_name, readonly)

    def test_allocation_admin_makes_existing_source_fields_readonly(self):
        payment = self.receive_payment(code="PAY-E-ALLOC-READONLY", amount=Decimal("1000000"))
        allocation = AllocateCustomerPaymentUseCase.execute(
            thanh_toan=payment,
            cong_no=self.debt,
            so_tien=Decimal("100000"),
            actor=self.actor,
        )
        allocation_admin = PhanBoThanhToanHoaDonAdmin(PhanBoThanhToanHoaDon, admin.site)
        readonly = allocation_admin.get_readonly_fields(request=None, obj=allocation)
        for field_name in ("thanh_toan", "hoa_don", "cong_no", "so_tien", "ghi_chu", "nguoi_phan_bo"):
            self.assertIn(field_name, readonly)


class PhaseEStaticDecisionTests(SimpleTestCase):
    def test_phase_e_decision_record_documents_clients_receivable_ownership(self):
        body = open("docs/BUSINESS_DOMAIN_DECISION_RECORD.md", encoding="utf-8").read()
        self.assertIn("clients.ThanhToanKhachHang", body)
        self.assertIn("clients.PhanBoThanhToanHoaDon", body)
        self.assertIn("accounting will consume", body)
        self.assertIn("CongNo.so_tien_da_thu", body)
        self.assertIn("append-only", body)
        self.assertIn("invoice-only allocation", body)
