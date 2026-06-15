# -*- coding: utf-8 -*-
"""Governance tests for append-only payroll adjustments."""

from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from accounting.admin import PayrollAdjustmentAdmin
from accounting.application.payroll_adjustment_use_case import CreatePayrollAdjustmentUseCase
from accounting.models import BangLuongThang, ChiTietLuong, PayrollAdjustment
from main.models import AuditLog
from users.models import NhanVien
from django.conf import settings


class PayrollAdjustmentGovernanceTest(TestCase):
    """Minimum payroll governance contract for locked/paid retroactive adjustments."""

    def setUp(self):
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.actor = User.objects.create_user(
            username="payroll_adjustment_actor",
            password="password",
            email="payroll_adjustment_actor@scmd.vn",
        )
        self.employee = NhanVien.objects.create(
            ma_nhan_vien="PAY-ADJ-001",
            ho_ten="Nhân sự điều chỉnh lương",
            trang_thai_lam_viec="CHINHTHUC",
            tenant_id=self.tenant_id,
            email=None,
        )
        self.other_employee = NhanVien.objects.create(
            ma_nhan_vien="PAY-ADJ-002",
            ho_ten="Nhân sự khác",
            trang_thai_lam_viec="CHINHTHUC",
            tenant_id=self.tenant_id,
            email=None,
        )
        self._month_counter = 1

    def _create_payroll(self, *, status=BangLuongThang.TrangThai.CALCULATED):
        payroll = BangLuongThang.objects.create(
            ten_bang_luong=f"Payroll adjustment test {self._month_counter}/2026",
            thang=self._month_counter,
            nam=2026,
            trang_thai=status,
            tenant_id=self.tenant_id,
        )
        self._month_counter += 1
        return payroll

    def _create_payslip(self, payroll, *, employee=None, thuc_lanh=Decimal("5000000")):
        return ChiTietLuong.objects.create(
            bang_luong=payroll,
            nhan_vien=employee or self.employee,
            thuc_lanh=thuc_lanh,
            nguon_du_lieu_snapshot={"source": "payroll-adjustment-governance-test"},
            tenant_id=self.tenant_id,
        )

    def _locked_payroll_with_payslip(self, *, status=BangLuongThang.TrangThai.LOCKED, employee=None):
        payroll = self._create_payroll(status=BangLuongThang.TrangThai.CALCULATED)
        payslip = self._create_payslip(payroll, employee=employee)
        BangLuongThang.objects.filter(pk=payroll.pk).update(trang_thai=status)
        payroll.refresh_from_db()
        payslip.refresh_from_db()
        return payroll, payslip

    def _execute_adjustment(
        self,
        *,
        payroll,
        employee=None,
        payslip=None,
        amount=Decimal("250000"),
        reason="Điều chỉnh truy lĩnh sau đối soát kỳ đã khóa",
    ):
        return CreatePayrollAdjustmentUseCase.execute(
            bang_luong_id=payroll.pk,
            nhan_vien_id=(employee or self.employee).pk,
            chi_tiet_luong_id=payslip.pk if payslip else None,
            so_tien_dieu_chinh=amount,
            ly_do=reason,
            actor_user=self.actor,
            tenant_id=self.tenant_id,
            metadata={"test_case": self._testMethodName},
        )

    def test_rejects_adjustment_when_payroll_is_not_locked_or_paid(self):
        payroll = self._create_payroll(status=BangLuongThang.TrangThai.CALCULATED)
        payslip = self._create_payslip(payroll)

        with self.assertRaisesMessage(ValidationError, "LOCKED/PAID"):
            self._execute_adjustment(payroll=payroll, payslip=payslip)

    def test_allows_adjustment_when_payroll_is_locked(self):
        payroll, payslip = self._locked_payroll_with_payslip(status=BangLuongThang.TrangThai.LOCKED)

        adjustment = self._execute_adjustment(payroll=payroll, payslip=payslip)

        self.assertEqual(adjustment.bang_luong_id, payroll.pk)
        self.assertEqual(adjustment.chi_tiet_luong_id, payslip.pk)
        self.assertEqual(adjustment.so_tien_dieu_chinh, Decimal("250000"))

    def test_allows_adjustment_when_payroll_is_paid(self):
        payroll, payslip = self._locked_payroll_with_payslip(status=BangLuongThang.TrangThai.PAID)

        adjustment = self._execute_adjustment(payroll=payroll, payslip=payslip)

        self.assertEqual(adjustment.bang_luong_id, payroll.pk)
        self.assertEqual(adjustment.chi_tiet_luong_id, payslip.pk)

    def test_rejects_zero_adjustment_amount(self):
        payroll, payslip = self._locked_payroll_with_payslip(status=BangLuongThang.TrangThai.LOCKED)

        with self.assertRaisesMessage(ValidationError, "khác 0"):
            self._execute_adjustment(payroll=payroll, payslip=payslip, amount=Decimal("0"))

    def test_rejects_blank_reason(self):
        payroll, payslip = self._locked_payroll_with_payslip(status=BangLuongThang.TrangThai.LOCKED)

        with self.assertRaisesMessage(ValidationError, "Lý do"):
            self._execute_adjustment(payroll=payroll, payslip=payslip, reason="   ")

    def test_rejects_payslip_from_different_payroll_period(self):
        payroll, _ = self._locked_payroll_with_payslip(status=BangLuongThang.TrangThai.LOCKED)
        other_payroll = self._create_payroll(status=BangLuongThang.TrangThai.CALCULATED)
        other_payslip = self._create_payslip(other_payroll)

        with self.assertRaisesMessage(ValidationError, "cùng kỳ lương"):
            self._execute_adjustment(payroll=payroll, payslip=other_payslip)

    def test_rejects_payslip_from_different_employee(self):
        payroll, other_employee_payslip = self._locked_payroll_with_payslip(
            status=BangLuongThang.TrangThai.LOCKED,
            employee=self.other_employee,
        )

        with self.assertRaisesMessage(ValidationError, "cùng nhân sự"):
            self._execute_adjustment(
                payroll=payroll,
                employee=self.employee,
                payslip=other_employee_payslip,
            )

    def test_adjustment_does_not_mutate_payslip_net_pay(self):
        payroll, payslip = self._locked_payroll_with_payslip(status=BangLuongThang.TrangThai.LOCKED)
        original_net_pay = payslip.thuc_lanh

        self._execute_adjustment(payroll=payroll, payslip=payslip, amount=Decimal("-125000"))

        payslip.refresh_from_db()
        self.assertEqual(payslip.thuc_lanh, original_net_pay)

    def test_adjustment_writes_audit_log(self):
        payroll, payslip = self._locked_payroll_with_payslip(status=BangLuongThang.TrangThai.LOCKED)

        adjustment = self._execute_adjustment(payroll=payroll, payslip=payslip)

        audit = AuditLog.objects.get(model_name="PayrollAdjustment", object_id=str(adjustment.pk))
        self.assertEqual(audit.action, AuditLog.Action.CREATE)
        self.assertEqual(audit.user_id, self.actor.pk)
        self.assertEqual(audit.changes["bang_luong_id"], payroll.pk)
        self.assertEqual(audit.changes["chi_tiet_luong_id"], payslip.pk)
        self.assertEqual(audit.changes["nhan_vien_id"], self.employee.pk)
        self.assertEqual(audit.changes["so_tien_dieu_chinh"], "250000")

    def test_admin_is_append_only_for_existing_adjustment(self):
        payroll, payslip = self._locked_payroll_with_payslip(status=BangLuongThang.TrangThai.LOCKED)
        adjustment = self._execute_adjustment(payroll=payroll, payslip=payslip)
        request = RequestFactory().post("/admin/accounting/payrolladjustment/")
        request.user = self.actor
        model_admin = PayrollAdjustmentAdmin(PayrollAdjustment, admin.site)

        self.assertFalse(model_admin.has_delete_permission(request, adjustment))
        readonly_fields = set(model_admin.get_readonly_fields(request, adjustment))
        self.assertTrue(
            {
                "bang_luong",
                "chi_tiet_luong",
                "nhan_vien",
                "so_tien_dieu_chinh",
                "ly_do",
                "metadata",
                "created_by",
                "created_at",
            }.issubset(readonly_fields)
        )
        with self.assertRaisesMessage(ValidationError, "append-only"):
            model_admin.save_model(request, adjustment, form=None, change=True)
