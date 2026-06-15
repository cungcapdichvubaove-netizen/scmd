# -*- coding: utf-8 -*-
"""
Application-layer inventory posting and voiding use cases.
"""

from decimal import Decimal

from django.conf import settings
from django.db import transaction

from inventory.models import CongCuTaiMucTieu, PhieuNhap, PhieuXuat, VatTu
from inventory.access_policies import InventoryDocumentPolicy
from inventory.models_ledger import InventoryLedgerEntry
from main.models import AuditLog


class InventoryDocumentPostingError(ValueError):
    """Raised when an inventory document violates posting rules."""


class InventoryDocumentUseCase:
    @staticmethod
    def _create_ledger_entry(
        *,
        vat_tu,
        stock_before,
        stock_after,
        quantity_delta,
        direction,
        movement_type,
        reason,
        phieu_nhap=None,
        phieu_xuat=None,
        chi_tiet_phieu_nhap=None,
        chi_tiet_phieu_xuat=None,
    ):
        InventoryLedgerEntry.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).create(
            phieu_nhap=phieu_nhap,
            phieu_xuat=phieu_xuat,
            chi_tiet_phieu_nhap=chi_tiet_phieu_nhap,
            chi_tiet_phieu_xuat=chi_tiet_phieu_xuat,
            vat_tu=vat_tu,
            document_type=(
                InventoryLedgerEntry.DocumentType.RECEIPT
                if phieu_nhap is not None
                else InventoryLedgerEntry.DocumentType.ISSUE
            ),
            movement_type=movement_type,
            direction=direction,
            quantity_delta=quantity_delta,
            stock_before=stock_before,
            stock_after=stock_after,
            reason=reason,
        )

    @staticmethod
    def post_inventory_document(document, user=None):
        policy = InventoryDocumentPolicy.can_post_document(user, document)
        if not policy.allowed:
            raise InventoryDocumentPostingError(policy.message)
        if isinstance(document, PhieuNhap):
            return InventoryDocumentUseCase._post_receipt(document, user=user)
        if isinstance(document, PhieuXuat):
            return InventoryDocumentUseCase._post_issue(document, user=user)
        raise InventoryDocumentPostingError("Loại chứng từ kho không được hỗ trợ.")

    @staticmethod
    def void_inventory_document(document, reason, user=None):
        if not reason or not reason.strip():
            raise InventoryDocumentPostingError("Phải nhập lý do khi hủy chứng từ kho.")
        reason = reason.strip()

        if isinstance(document, PhieuNhap):
            model_cls = PhieuNhap
            void_handler = InventoryDocumentUseCase._void_receipt
        elif isinstance(document, PhieuXuat):
            model_cls = PhieuXuat
            void_handler = InventoryDocumentUseCase._void_issue
        else:
            raise InventoryDocumentPostingError("Loại chứng từ kho không được hỗ trợ.")

        with transaction.atomic():
            # ``document`` may be a stale in-memory instance right after posting.
            # Reload and lock the authoritative DB row before policy/status checks
            # so reversal does not fail merely because caller still holds a DRAFT
            # object. The lower-level void handlers keep their own row/stock locks.
            locked_document = model_cls.objects.for_tenant(
                settings.SCMD_ORGANIZATION_ID
            ).select_for_update().get(pk=document.pk)
            policy = InventoryDocumentPolicy.can_void_document(user, locked_document)
            if not policy.allowed:
                raise InventoryDocumentPostingError(policy.message)
            return void_handler(locked_document, reason=reason, user=user)

    @staticmethod
    def recalculate_issue_total(phieu_xuat):
        total = sum(
            (item.so_luong or 0) * (item.don_gia_ban or 0)
            for item in phieu_xuat.chi_tiet.all()
        )
        PhieuXuat.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(pk=phieu_xuat.pk).update(
            tong_tien_phai_thu=total if phieu_xuat.loai_xuat == "BAN_TRU_LUONG" else Decimal("0")
        )
        phieu_xuat.tong_tien_phai_thu = total if phieu_xuat.loai_xuat == "BAN_TRU_LUONG" else Decimal("0")
        return phieu_xuat.tong_tien_phai_thu

    @staticmethod
    def _post_receipt(document, user=None):
        if document.trang_thai != PhieuNhap.TrangThai.DRAFT:
            raise InventoryDocumentPostingError("Chỉ phiếu nhập ở trạng thái DRAFT mới được ghi sổ.")

        with transaction.atomic():
            phieu_nhap = PhieuNhap.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_for_update().get(pk=document.pk)
            if phieu_nhap.trang_thai != PhieuNhap.TrangThai.DRAFT:
                raise InventoryDocumentPostingError("Phiếu nhập không còn ở trạng thái DRAFT để ghi sổ.")
            details = list(
                phieu_nhap.chi_tiet.select_related("vat_tu").order_by("pk")
            )
            if not details:
                raise InventoryDocumentPostingError("Phiếu nhập không có chi tiết vật tư.")

            for detail in details:
                vat_tu = VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_for_update().get(pk=detail.vat_tu_id)
                stock_before = vat_tu.so_luong_ton or 0
                stock_after = stock_before + detail.so_luong
                VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(pk=vat_tu.pk).update(
                    so_luong_ton=stock_after
                )
                InventoryDocumentUseCase._create_ledger_entry(
                    phieu_nhap=phieu_nhap,
                    chi_tiet_phieu_nhap=detail,
                    vat_tu=vat_tu,
                    stock_before=stock_before,
                    stock_after=stock_after,
                    quantity_delta=detail.so_luong,
                    direction=InventoryLedgerEntry.Direction.IN,
                    movement_type=InventoryLedgerEntry.MovementType.POSTING,
                    reason="Posting phiếu nhập kho.",
                )

            phieu_nhap.trang_thai = PhieuNhap.TrangThai.POSTED
            phieu_nhap.save(update_fields=["trang_thai"])

            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.UPDATE,
                module="inventory",
                model_name="PhieuNhap",
                object_id=str(phieu_nhap.pk),
                note="Ghi sổ phiếu nhập kho.",
                changes={
                    "trang_thai": phieu_nhap.trang_thai,
                    "detail_count": len(details),
                },
            )
            return phieu_nhap

    @staticmethod
    def _void_receipt(document, reason, user=None):
        with transaction.atomic():
            phieu_nhap = PhieuNhap.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_for_update().get(pk=document.pk)
            if phieu_nhap.trang_thai != PhieuNhap.TrangThai.POSTED:
                raise InventoryDocumentPostingError("Phiếu nhập không còn ở trạng thái POSTED để hủy.")
            details = list(
                phieu_nhap.chi_tiet.select_related("vat_tu").order_by("pk")
            )
            for detail in details:
                vat_tu = VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_for_update().get(pk=detail.vat_tu_id)
                current_stock = vat_tu.so_luong_ton or 0
                if current_stock < detail.so_luong:
                    raise InventoryDocumentPostingError(
                        f"Không thể hủy phiếu nhập vì vật tư {vat_tu.ten_vat_tu} không còn đủ tồn để reverse."
                    )
                VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(pk=vat_tu.pk).update(
                    so_luong_ton=current_stock - detail.so_luong
                )
                InventoryDocumentUseCase._create_ledger_entry(
                    phieu_nhap=phieu_nhap,
                    chi_tiet_phieu_nhap=detail,
                    vat_tu=vat_tu,
                    stock_before=current_stock,
                    stock_after=current_stock - detail.so_luong,
                    quantity_delta=-detail.so_luong,
                    direction=InventoryLedgerEntry.Direction.OUT,
                    movement_type=InventoryLedgerEntry.MovementType.REVERSAL,
                    reason=reason,
                )

            phieu_nhap.trang_thai = PhieuNhap.TrangThai.VOIDED
            phieu_nhap.save(update_fields=["trang_thai"])

            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.UPDATE,
                module="inventory",
                model_name="PhieuNhap",
                object_id=str(phieu_nhap.pk),
                note=f"Hủy phiếu nhập kho: {reason}",
                changes={"trang_thai": phieu_nhap.trang_thai},
            )
            return phieu_nhap

    @staticmethod
    def _post_issue(document, user=None):
        if document.trang_thai != PhieuXuat.TrangThai.DRAFT:
            raise InventoryDocumentPostingError("Chỉ phiếu xuất ở trạng thái DRAFT mới được ghi sổ.")

        with transaction.atomic():
            phieu_xuat = PhieuXuat.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_for_update().get(pk=document.pk)
            if phieu_xuat.trang_thai != PhieuXuat.TrangThai.DRAFT:
                raise InventoryDocumentPostingError("Phiếu xuất không còn ở trạng thái DRAFT để ghi sổ.")
            details = list(
                phieu_xuat.chi_tiet.select_related("vat_tu").order_by("pk")
            )
            if not details:
                raise InventoryDocumentPostingError("Phiếu xuất không có chi tiết vật tư.")

            total_receivable = Decimal("0")
            for detail in details:
                vat_tu = VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_for_update().get(pk=detail.vat_tu_id)
                current_stock = vat_tu.so_luong_ton or 0
                if current_stock < detail.so_luong:
                    raise InventoryDocumentPostingError(
                        f"Vật tư {vat_tu.ten_vat_tu} không đủ tồn để xuất."
                    )
                VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(pk=vat_tu.pk).update(
                    so_luong_ton=current_stock - detail.so_luong
                )
                InventoryDocumentUseCase._create_ledger_entry(
                    phieu_xuat=phieu_xuat,
                    chi_tiet_phieu_xuat=detail,
                    vat_tu=vat_tu,
                    stock_before=current_stock,
                    stock_after=current_stock - detail.so_luong,
                    quantity_delta=-detail.so_luong,
                    direction=InventoryLedgerEntry.Direction.OUT,
                    movement_type=InventoryLedgerEntry.MovementType.POSTING,
                    reason="Posting phiếu xuất kho.",
                )
                total_receivable += Decimal(detail.so_luong or 0) * Decimal(detail.don_gia_ban or 0)

                if phieu_xuat.loai_xuat == "CONG_CU" and phieu_xuat.muc_tieu_nhan_id:
                    cong_cu, _ = CongCuTaiMucTieu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_for_update().get_or_create(
                        muc_tieu_id=phieu_xuat.muc_tieu_nhan_id,
                        vat_tu_id=detail.vat_tu_id,
                        defaults={"so_luong_dang_giu": 0},
                    )
                    CongCuTaiMucTieu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(pk=cong_cu.pk).update(
                        so_luong_dang_giu=(cong_cu.so_luong_dang_giu or 0) + detail.so_luong
                    )

            phieu_xuat.tong_tien_phai_thu = (
                total_receivable if phieu_xuat.loai_xuat == "BAN_TRU_LUONG" else Decimal("0")
            )
            phieu_xuat.trang_thai = PhieuXuat.TrangThai.POSTED
            phieu_xuat.save(update_fields=["tong_tien_phai_thu", "trang_thai"])

            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.UPDATE,
                module="inventory",
                model_name="PhieuXuat",
                object_id=str(phieu_xuat.pk),
                note="Ghi sổ phiếu xuất kho.",
                changes={
                    "trang_thai": phieu_xuat.trang_thai,
                    "tong_tien_phai_thu": str(phieu_xuat.tong_tien_phai_thu),
                    "detail_count": len(details),
                },
            )
            return phieu_xuat

    @staticmethod
    def _void_issue(document, reason, user=None):
        with transaction.atomic():
            phieu_xuat = PhieuXuat.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_for_update().get(pk=document.pk)
            if phieu_xuat.trang_thai != PhieuXuat.TrangThai.POSTED:
                raise InventoryDocumentPostingError("Phiếu xuất không còn ở trạng thái POSTED để hủy.")
            if phieu_xuat.trang_thai_thanh_toan == "DA_TRU":
                raise InventoryDocumentPostingError("Phiếu xuất đã khấu trừ lương không được hủy trực tiếp.")
            details = list(
                phieu_xuat.chi_tiet.select_related("vat_tu").order_by("pk")
            )
            for detail in details:
                vat_tu = VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_for_update().get(pk=detail.vat_tu_id)
                current_stock = vat_tu.so_luong_ton or 0
                VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(pk=vat_tu.pk).update(
                    so_luong_ton=current_stock + detail.so_luong
                )
                InventoryDocumentUseCase._create_ledger_entry(
                    phieu_xuat=phieu_xuat,
                    chi_tiet_phieu_xuat=detail,
                    vat_tu=vat_tu,
                    stock_before=current_stock,
                    stock_after=current_stock + detail.so_luong,
                    quantity_delta=detail.so_luong,
                    direction=InventoryLedgerEntry.Direction.IN,
                    movement_type=InventoryLedgerEntry.MovementType.REVERSAL,
                    reason=reason,
                )

                if phieu_xuat.loai_xuat == "CONG_CU" and phieu_xuat.muc_tieu_nhan_id:
                    cong_cu = CongCuTaiMucTieu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_for_update().filter(
                        muc_tieu_id=phieu_xuat.muc_tieu_nhan_id,
                        vat_tu_id=detail.vat_tu_id,
                    ).first()
                    if cong_cu:
                        current_qty = cong_cu.so_luong_dang_giu or 0
                        if current_qty < detail.so_luong:
                            raise InventoryDocumentPostingError(
                                f"Không thể hủy phiếu xuất công cụ vì mục tiêu không còn đủ số lượng {detail.vat_tu.ten_vat_tu}."
                            )
                        CongCuTaiMucTieu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(pk=cong_cu.pk).update(
                            so_luong_dang_giu=current_qty - detail.so_luong
                        )

            phieu_xuat.tong_tien_phai_thu = Decimal("0")
            phieu_xuat.trang_thai = PhieuXuat.TrangThai.VOIDED
            phieu_xuat.save(update_fields=["tong_tien_phai_thu", "trang_thai"])

            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.UPDATE,
                module="inventory",
                model_name="PhieuXuat",
                object_id=str(phieu_xuat.pk),
                note=f"Hủy phiếu xuất kho: {reason}",
                changes={"trang_thai": phieu_xuat.trang_thai},
            )
            return phieu_xuat
