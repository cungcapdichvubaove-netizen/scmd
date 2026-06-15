# -*- coding: utf-8 -*-
"""Receivable report context for CRM/customer dashboard."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from clients.application.customer_payment_permission_policy import CustomerPaymentPermissionPolicy
from clients.models import CongNo, HoaDon, PhanBoThanhToanHoaDon


def _money(value) -> Decimal:
    return Decimal(str(value or 0))


class CustomerReceivableReportUseCase:
    """Build Phase E receivable dashboard/report context without mutating records."""

    @classmethod
    def execute(cls, *, tenant_id=None, today=None, user=None, system_context: bool = False):
        if not system_context:
            CustomerPaymentPermissionPolicy.enforce_report(user)
        today = today or timezone.localdate()
        if tenant_id:
            debts = CongNo.objects.for_tenant(tenant_id)
            invoices = HoaDon.objects.for_tenant(tenant_id)
            allocations = PhanBoThanhToanHoaDon.objects.for_tenant(tenant_id)
        else:
            debts = CongNo.objects.all()
            invoices = HoaDon.objects.all()
            allocations = PhanBoThanhToanHoaDon.objects.all()

        open_debts = debts.exclude(trang_thai__in=[CongNo.TrangThai.PAID, CongNo.TrangThai.WRITTEN_OFF])
        overdue_debts = open_debts.filter(ngay_den_han__lt=today).select_related("hoa_don", "hoa_don__hop_dong")
        partial_invoices = invoices.filter(trang_thai=HoaDon.TrangThai.PARTIALLY_PAID).select_related("hop_dong")

        total_open_receivable = _money(open_debts.aggregate(total=Sum("so_tien_phai_thu"))["total"])
        total_collected_allocation = _money(allocations.aggregate(total=Sum("so_tien"))["total"])
        total_open_collected = _money(open_debts.aggregate(total=Sum("so_tien_da_thu"))["total"])
        total_remaining_open_receivable = max(total_open_receivable - total_open_collected, Decimal("0"))

        return {
            "overdue_receivables": overdue_debts.order_by("ngay_den_han")[:10],
            "overdue_receivables_count": overdue_debts.count(),
            "partial_paid_invoices": partial_invoices.order_by("ngay_den_han", "ngay_phat_hanh")[:10],
            "partial_paid_invoices_count": partial_invoices.count(),
            "receivable_totals": {
                "total_open_receivable": total_open_receivable,
                "total_collected_allocation": total_collected_allocation,
                "total_remaining_open_receivable": total_remaining_open_receivable,
                # Legacy aliases kept for dashboard/template compatibility.
                "total_receivable": total_open_receivable,
                "total_collected": total_collected_allocation,
                "total_remaining": total_remaining_open_receivable,
            },
        }
