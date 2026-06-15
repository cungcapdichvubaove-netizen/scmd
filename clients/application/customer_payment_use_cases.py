# -*- coding: utf-8 -*-
"""Customer payment and receivable settlement use cases for Phase E.

Phase E keeps the contract receivable lifecycle in ``clients``. These use cases
are the only production path that should create payment allocations and sync
invoice/receivable paid amounts. They intentionally do not move records into
``accounting`` yet; accounting will consume the report context in a later phase.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from clients.application.customer_payment_permission_policy import CustomerPaymentPermissionPolicy
from clients.models import (
    CongNo,
    HoaDon,
    HopDong,
    KhachHangTiemNang,
    PhanBoThanhToanHoaDon,
    ThanhToanKhachHang,
)
from main.models import AuditLog


def _decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _audit(*, actor=None, model_name: str, object_id, tenant_id=None, note: str = "", changes=None):
    return AuditLog.objects.create(
        user=actor if getattr(actor, "is_authenticated", False) else None,
        action=AuditLog.Action.EXECUTE,
        module="clients",
        model_name=model_name,
        object_id=str(object_id) if object_id is not None else None,
        tenant_id=tenant_id,
        note=note,
        changes=changes or {},
    )


def _enforce_or_system(enforcer, actor, *, system_context: bool = False) -> None:
    if system_context:
        return
    enforcer(actor)


def _tenant_id_of(obj):
    return getattr(obj, "tenant_id", None)


def _validate_same_tenant(*objects) -> None:
    tenant_ids = {tenant_id for tenant_id in (_tenant_id_of(obj) for obj in objects if obj is not None) if tenant_id is not None}
    if len(tenant_ids) > 1:
        raise ValidationError("Thanh toán, hóa đơn và công nợ phải thuộc cùng tenant.")


def _contract_customer_id(contract: HopDong | None):
    return getattr(contract, "khach_hang_cu_id", None) if contract is not None else None


def _validate_payment_target_consistency(payment: ThanhToanKhachHang, invoice: HoaDon | None, debt: CongNo | None) -> None:
    _validate_same_tenant(payment, invoice, debt)
    if debt is None:
        raise ValidationError("Phase E v3 yêu cầu phân bổ thanh toán phải gắn với công nợ cụ thể; không cho phân bổ chỉ theo hóa đơn.")
    if invoice is not None and debt.hoa_don_id != invoice.pk:
        raise ValidationError("Công nợ phải thuộc cùng hóa đơn được phân bổ.")
    target_invoice = invoice or getattr(debt, "hoa_don", None)
    if target_invoice is None:
        return
    if payment.hop_dong_id and target_invoice.hop_dong_id != payment.hop_dong_id:
        raise ValidationError("Thanh toán chỉ được phân bổ vào hóa đơn/công nợ cùng hợp đồng.")
    payment_customer_id = payment.khach_hang_id or _contract_customer_id(getattr(payment, "hop_dong", None))
    target_customer_id = _contract_customer_id(getattr(target_invoice, "hop_dong", None))
    if payment_customer_id and target_customer_id and payment_customer_id != target_customer_id:
        raise ValidationError("Thanh toán chỉ được phân bổ vào hóa đơn/công nợ cùng khách hàng.")


class ReceiveCustomerPaymentUseCase:
    """Create or idempotently return a customer payment source record."""

    @classmethod
    @transaction.atomic
    def execute(
        cls,
        *,
        ma_phieu: str,
        so_tien,
        ngay_thanh_toan=None,
        hinh_thuc=None,
        khach_hang: Optional[KhachHangTiemNang] = None,
        hop_dong: Optional[HopDong] = None,
        ma_giao_dich: str = "",
        ghi_chu: str = "",
        actor=None,
        tenant_id=None,
        system_context: bool = False,
    ) -> ThanhToanKhachHang:
        _enforce_or_system(CustomerPaymentPermissionPolicy.enforce_receive, actor, system_context=system_context)
        amount = _decimal(so_tien)
        if amount <= 0:
            raise ValidationError("Số tiền thanh toán phải lớn hơn 0.")

        qs = (
            ThanhToanKhachHang.objects.for_tenant(tenant_id).select_for_update()
            if tenant_id
            else ThanhToanKhachHang.objects.select_for_update()
        )
        existing = qs.filter(ma_phieu=ma_phieu).first()
        if existing:
            if existing.so_tien != amount:
                raise ValidationError("Mã phiếu thanh toán đã tồn tại với số tiền khác.")
            if existing.trang_thai == ThanhToanKhachHang.TrangThai.CANCELLED:
                raise ValidationError("Không được tái sử dụng mã phiếu thanh toán đã hủy.")
            if existing.trang_thai == ThanhToanKhachHang.TrangThai.DRAFT:
                existing.transition_status(ThanhToanKhachHang.TrangThai.RECEIVED, actor=actor, note="Phase E receive existing draft payment")
            return existing

        payment = ThanhToanKhachHang(
            ma_phieu=ma_phieu,
            so_tien=amount,
            ngay_thanh_toan=ngay_thanh_toan or timezone.localdate(),
            hinh_thuc=hinh_thuc or ThanhToanKhachHang.HinhThucThanhToan.CHUYEN_KHOAN,
            khach_hang=khach_hang,
            hop_dong=hop_dong,
            ma_giao_dich=ma_giao_dich or "",
            ghi_chu=ghi_chu or "",
            nguoi_ghi_nhan=actor if getattr(actor, "is_authenticated", False) else None,
        )
        payment.full_clean()
        payment.save()
        payment.transition_status(ThanhToanKhachHang.TrangThai.RECEIVED, actor=actor, note="Phase E receive customer payment")
        payment.record_event(
            actor=actor,
            note="Phase E customer payment source created",
            changes={"ma_phieu": payment.ma_phieu, "so_tien": str(payment.so_tien), "status": payment.trang_thai},
        )
        return payment


class RecalculateReceivableStatusUseCase:
    """Synchronize derived paid amounts and statuses from payment allocations."""

    @classmethod
    @transaction.atomic
    def execute(cls, *, hoa_don: Optional[HoaDon] = None, cong_no: Optional[CongNo] = None, actor=None, system_context: bool = False):
        _enforce_or_system(CustomerPaymentPermissionPolicy.enforce_recalculate, actor, system_context=system_context)
        invoices_to_recalculate = {}
        debts_to_recalculate = {}
        if cong_no is not None:
            locked_debt = CongNo.objects.select_for_update().select_related("hoa_don").get(pk=cong_no.pk)
            debts_to_recalculate[locked_debt.pk] = locked_debt
            invoices_to_recalculate[locked_debt.hoa_don_id] = locked_debt.hoa_don
        if hoa_don is not None:
            locked_invoice = HoaDon.objects.select_for_update().get(pk=hoa_don.pk)
            invoices_to_recalculate[locked_invoice.pk] = locked_invoice
            for debt in CongNo.objects.select_for_update().filter(hoa_don=locked_invoice):
                debts_to_recalculate[debt.pk] = debt

        changed = {"cong_no": [], "hoa_don": []}
        today = timezone.localdate()

        for debt in debts_to_recalculate.values():
            if debt.trang_thai == CongNo.TrangThai.WRITTEN_OFF:
                continue
            paid = PhanBoThanhToanHoaDon.objects.filter(cong_no=debt).aggregate(total=Sum("so_tien"))["total"] or Decimal("0")
            old_paid = debt.so_tien_da_thu
            old_status = debt.trang_thai
            debt.so_tien_da_thu = min(paid, debt.so_tien_phai_thu)
            if debt.so_tien_da_thu >= debt.so_tien_phai_thu:
                new_status = CongNo.TrangThai.PAID
            elif debt.so_tien_da_thu > 0:
                new_status = CongNo.TrangThai.PARTIAL
            elif debt.ngay_den_han < today:
                new_status = CongNo.TrangThai.OVERDUE
            else:
                new_status = CongNo.TrangThai.OPEN
            debt.save(update_fields=["so_tien_da_thu", "updated_at"])
            if old_paid != debt.so_tien_da_thu:
                _audit(
                    actor=actor,
                    model_name="CongNo",
                    object_id=debt.pk,
                    tenant_id=debt.tenant_id,
                    note="Phase E receivable paid amount synchronized from allocations",
                    changes={"so_tien_da_thu": {"old": str(old_paid), "new": str(debt.so_tien_da_thu)}},
                )
            if old_status != new_status:
                debt.transition_status(new_status, actor=actor, note="Phase E receivable status synchronized from allocations")
            changed["cong_no"].append(debt.pk)

        for invoice in invoices_to_recalculate.values():
            if invoice.trang_thai == HoaDon.TrangThai.CANCELLED:
                continue
            paid = PhanBoThanhToanHoaDon.objects.filter(cong_no__hoa_don=invoice).aggregate(total=Sum("so_tien"))["total"] or Decimal("0")
            old_status = invoice.trang_thai
            if paid >= invoice.tong_tien:
                new_status = HoaDon.TrangThai.PAID
            elif paid > 0:
                new_status = HoaDon.TrangThai.PARTIALLY_PAID
            elif invoice.ngay_den_han and invoice.ngay_den_han < today:
                new_status = HoaDon.TrangThai.OVERDUE
            else:
                new_status = HoaDon.TrangThai.ISSUED
            if old_status != new_status:
                invoice.transition_status(new_status, actor=actor, note="Phase E invoice status synchronized from allocations")
            changed["hoa_don"].append(invoice.pk)

        return changed


class AllocateCustomerPaymentUseCase:
    """Allocate received customer payment into invoice/receivable records."""

    @classmethod
    @transaction.atomic
    def execute(
        cls,
        *,
        thanh_toan: ThanhToanKhachHang,
        so_tien,
        hoa_don: Optional[HoaDon] = None,
        cong_no: Optional[CongNo] = None,
        actor=None,
        ghi_chu: str = "",
        system_context: bool = False,
    ) -> PhanBoThanhToanHoaDon:
        _enforce_or_system(CustomerPaymentPermissionPolicy.enforce_allocate, actor, system_context=system_context)
        if cong_no is None:
            raise ValidationError("Phase E v3 yêu cầu phân bổ phải gắn với công nợ cụ thể; invoice-only allocation bị chặn để giữ nhất quán hóa đơn/công nợ.")
        payment = ThanhToanKhachHang.objects.select_for_update().select_related("hop_dong", "khach_hang").get(pk=thanh_toan.pk)
        invoice = HoaDon.objects.select_for_update().select_related("hop_dong", "hop_dong__khach_hang_cu").get(pk=hoa_don.pk) if hoa_don else None
        debt = CongNo.objects.select_for_update().select_related("hoa_don", "hoa_don__hop_dong", "hoa_don__hop_dong__khach_hang_cu").get(pk=cong_no.pk) if cong_no else None
        if debt and invoice is None:
            invoice = debt.hoa_don
        _validate_payment_target_consistency(payment, invoice, debt)

        amount = _decimal(so_tien)
        existing = PhanBoThanhToanHoaDon.objects.filter(
            thanh_toan=payment,
            hoa_don=invoice,
            cong_no=debt,
            so_tien=amount,
        ).first()
        if existing:
            return existing

        allocation = PhanBoThanhToanHoaDon(
            thanh_toan=payment,
            hoa_don=invoice,
            cong_no=debt,
            so_tien=amount,
            nguoi_phan_bo=actor if getattr(actor, "is_authenticated", False) else None,
            ghi_chu=ghi_chu or "",
        )
        allocation.full_clean()
        allocation.save()
        allocation.record_event(
            actor=actor,
            note="Phase E customer payment allocated",
            changes={
                "thanh_toan_id": payment.pk,
                "hoa_don_id": invoice.pk if invoice else None,
                "cong_no_id": debt.pk if debt else None,
                "so_tien": str(amount),
            },
        )
        if payment.trang_thai == ThanhToanKhachHang.TrangThai.RECEIVED:
            payment.transition_status(ThanhToanKhachHang.TrangThai.ALLOCATED, actor=actor, note="Phase E payment has at least one allocation")
        RecalculateReceivableStatusUseCase.execute(hoa_don=invoice, cong_no=debt, actor=actor, system_context=system_context)
        return allocation


class CancelCustomerPaymentUseCase:
    """Cancel unallocated customer payment records only.

    Allocated payments are intentionally blocked in Phase E. A later recovery path
    can add reversal records without deleting audit history.
    """

    @classmethod
    @transaction.atomic
    def execute(cls, *, thanh_toan: ThanhToanKhachHang, actor=None, reason: str = "", system_context: bool = False) -> ThanhToanKhachHang:
        _enforce_or_system(CustomerPaymentPermissionPolicy.enforce_cancel, actor, system_context=system_context)
        payment = ThanhToanKhachHang.objects.select_for_update().get(pk=thanh_toan.pk)
        if payment.cac_phan_bo.exists():
            raise ValidationError("Không được hủy thanh toán đã phân bổ. Cần chứng từ đảo/thu hồi ở recovery phase.")
        if payment.trang_thai == ThanhToanKhachHang.TrangThai.CANCELLED:
            return payment
        payment.transition_status(ThanhToanKhachHang.TrangThai.CANCELLED, actor=actor, note=reason or "Phase E cancel unallocated customer payment")
        return payment
