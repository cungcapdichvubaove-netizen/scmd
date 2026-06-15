# -*- coding: utf-8 -*-
"""Application use cases for Phase F asset recovery and offboarding inventory."""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounting.models import KhoanKhauTruNhanVien
from inventory.application.asset_recovery_permission_policy import AssetRecoveryPermissionPolicy
from inventory.models import (
    BienBanMatHongVatTu,
    ChiTietPhieuThuHoi,
    ChiTietPhieuXuat,
    PhieuThuHoi,
    PhieuXuat,
    VatTu,
)
from inventory.models_ledger import InventoryLedgerEntry
from main.models import AuditLog


class AssetRecoveryError(ValueError):
    """Raised when asset recovery business rules are violated."""


def _tenant_id_from(obj=None):
    return getattr(obj, "tenant_id", None) or settings.SCMD_ORGANIZATION_ID


def _sum_or_zero(queryset, field):
    value = queryset.aggregate(total=Sum(field))["total"]
    return value or 0


class GetEmployeeOutstandingAssetsUseCase:
    """Return issued employee assets that are not yet recovered or resolved."""

    @staticmethod
    def outstanding_for_issue_line(issue_line, *, tenant_id=None):
        tenant_id = tenant_id or _tenant_id_from(issue_line)
        recovered = _sum_or_zero(
            ChiTietPhieuThuHoi.objects.for_tenant(tenant_id).filter(
                chi_tiet_phieu_xuat=issue_line,
                phieu_thu_hoi__trang_thai=PhieuThuHoi.TrangThai.POSTED,
            ),
            "so_luong_thu_hoi",
        )
        return max((issue_line.so_luong or 0) - recovered, 0)

    @staticmethod
    def execute(*, nhan_vien, tenant_id=None, include_zero=False, user=None):
        if user is not None:
            AssetRecoveryPermissionPolicy.require(
                AssetRecoveryPermissionPolicy.can_view(user),
                "Không có quyền xem tài sản còn phải thu hồi.",
            )
        tenant_id = tenant_id or _tenant_id_from(nhan_vien)
        issued_lines = (
            ChiTietPhieuXuat.objects.for_tenant(tenant_id)
            .select_related("phieu_xuat", "vat_tu")
            .filter(
                phieu_xuat__nhan_vien_nhan=nhan_vien,
                phieu_xuat__trang_thai=PhieuXuat.TrangThai.POSTED,
                phieu_xuat__loai_xuat__in=["CAP_PHAT", "BAN_TRU_LUONG"],
            )
            .order_by("phieu_xuat__ngay_xuat", "pk")
        )
        rows = []
        for line in issued_lines:
            outstanding = GetEmployeeOutstandingAssetsUseCase.outstanding_for_issue_line(line, tenant_id=tenant_id)
            if include_zero or outstanding > 0:
                rows.append({
                    "chi_tiet_phieu_xuat": line,
                    "phieu_xuat": line.phieu_xuat,
                    "vat_tu": line.vat_tu,
                    "issued_quantity": line.so_luong,
                    "outstanding_quantity": outstanding,
                })
        return rows

    @staticmethod
    def has_unresolved_damage_reports(*, nhan_vien, tenant_id=None):
        tenant_id = tenant_id or _tenant_id_from(nhan_vien)
        return BienBanMatHongVatTu.objects.for_tenant(tenant_id).filter(
            nhan_vien=nhan_vien,
            trang_thai__in=[BienBanMatHongVatTu.TrangThai.DRAFT, BienBanMatHongVatTu.TrangThai.PENDING_APPROVAL],
        ).exists()

    @staticmethod
    def can_complete_offboarding(*, nhan_vien, tenant_id=None):
        return (
            not GetEmployeeOutstandingAssetsUseCase.execute(nhan_vien=nhan_vien, tenant_id=tenant_id)
            and not GetEmployeeOutstandingAssetsUseCase.has_unresolved_damage_reports(nhan_vien=nhan_vien, tenant_id=tenant_id)
        )


class PostAssetRecoveryUseCase:
    """Post a recovery document, returning good items to stock and recording loss/damage."""

    @staticmethod
    def _create_ledger_entry(*, phieu_thu_hoi, detail, vat_tu, stock_before, stock_after, quantity_delta, direction, movement_type, reason):
        InventoryLedgerEntry.objects.for_tenant(_tenant_id_from(phieu_thu_hoi)).create(
            phieu_thu_hoi=phieu_thu_hoi,
            chi_tiet_phieu_thu_hoi=detail,
            vat_tu=vat_tu,
            document_type=InventoryLedgerEntry.DocumentType.RECOVERY,
            movement_type=movement_type,
            direction=direction,
            quantity_delta=quantity_delta,
            stock_before=stock_before,
            stock_after=stock_after,
            reason=reason,
        )

    @staticmethod
    def execute(*, phieu_thu_hoi, actor=None):
        AssetRecoveryPermissionPolicy.require(
            AssetRecoveryPermissionPolicy.can_post(actor),
            "Không có quyền ghi sổ phiếu thu hồi tài sản.",
        )
        tenant_id = _tenant_id_from(phieu_thu_hoi)
        with transaction.atomic():
            document = PhieuThuHoi.objects.for_tenant(tenant_id).select_for_update().get(pk=phieu_thu_hoi.pk)
            if document.trang_thai == PhieuThuHoi.TrangThai.POSTED:
                return document
            if document.trang_thai != PhieuThuHoi.TrangThai.DRAFT:
                raise AssetRecoveryError("Chỉ phiếu thu hồi DRAFT mới được ghi sổ.")
            details = list(
                document.chi_tiet.select_related("chi_tiet_phieu_xuat__phieu_xuat", "vat_tu").order_by("pk")
            )
            if not details:
                raise AssetRecoveryError("Phiếu thu hồi không có chi tiết vật tư.")
            for detail in details:
                issue_line = ChiTietPhieuXuat.objects.for_tenant(tenant_id).select_for_update().select_related("phieu_xuat", "vat_tu").get(pk=detail.chi_tiet_phieu_xuat_id)
                if issue_line.phieu_xuat.nhan_vien_nhan_id != document.nhan_vien_id:
                    raise AssetRecoveryError("Dòng phiếu xuất gốc không thuộc nhân viên trên phiếu thu hồi.")
                outstanding = GetEmployeeOutstandingAssetsUseCase.outstanding_for_issue_line(issue_line, tenant_id=tenant_id)
                if detail.so_luong_thu_hoi > outstanding:
                    raise AssetRecoveryError("Số lượng thu hồi vượt số lượng còn phải thu hồi từ phiếu xuất gốc.")
                if detail.so_luong_nhap_lai_kho:
                    vat_tu = VatTu.objects.for_tenant(tenant_id).select_for_update().get(pk=detail.vat_tu_id)
                    stock_before = vat_tu.so_luong_ton or 0
                    stock_after = stock_before + detail.so_luong_nhap_lai_kho
                    VatTu.objects.for_tenant(tenant_id).filter(pk=vat_tu.pk).update(so_luong_ton=stock_after)
                    PostAssetRecoveryUseCase._create_ledger_entry(
                        phieu_thu_hoi=document,
                        detail=detail,
                        vat_tu=vat_tu,
                        stock_before=stock_before,
                        stock_after=stock_after,
                        quantity_delta=detail.so_luong_nhap_lai_kho,
                        direction=InventoryLedgerEntry.Direction.IN,
                        movement_type=InventoryLedgerEntry.MovementType.POSTING,
                        reason="Posting phiếu thu hồi tài sản: nhập lại kho hàng tốt.",
                    )
                if detail.so_luong_mat_hong:
                    BienBanMatHongVatTu.objects.for_tenant(tenant_id).get_or_create(
                        phieu_thu_hoi=document,
                        chi_tiet_thu_hoi=detail,
                        defaults={
                            "nhan_vien": document.nhan_vien,
                            "vat_tu": detail.vat_tu,
                            "so_luong": detail.so_luong_mat_hong,
                            "don_gia_khau_tru": detail.vat_tu.gia_ban or Decimal("0"),
                            "ly_do": f"{detail.get_tinh_trang_display()} khi thu hồi {document.ma_phieu}",
                            "trang_thai": BienBanMatHongVatTu.TrangThai.DRAFT,
                        },
                    )
            document.trang_thai = PhieuThuHoi.TrangThai.POSTED
            document.posted_at = timezone.now()
            document.save(update_fields=["trang_thai", "posted_at", "updated_at"])
            AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="inventory",
                model_name="PhieuThuHoi",
                object_id=str(document.pk),
                tenant_id=document.tenant_id,
                note="Ghi sổ phiếu thu hồi tài sản.",
                changes={"trang_thai": document.trang_thai, "detail_count": len(details)},
            )
            return document


class VoidAssetRecoveryUseCase:
    """Void a posted recovery document and reverse returned-stock ledger entries."""

    @staticmethod
    def execute(*, phieu_thu_hoi, reason, actor=None):
        AssetRecoveryPermissionPolicy.require(
            AssetRecoveryPermissionPolicy.can_void(actor),
            "Không có quyền hủy phiếu thu hồi tài sản.",
        )
        if not reason or not str(reason).strip():
            raise AssetRecoveryError("Phải nhập lý do khi hủy phiếu thu hồi.")
        tenant_id = _tenant_id_from(phieu_thu_hoi)
        with transaction.atomic():
            document = PhieuThuHoi.objects.for_tenant(tenant_id).select_for_update().get(pk=phieu_thu_hoi.pk)
            if document.trang_thai == PhieuThuHoi.TrangThai.VOIDED:
                return document
            if document.trang_thai != PhieuThuHoi.TrangThai.POSTED:
                raise AssetRecoveryError("Chỉ phiếu thu hồi POSTED mới được hủy.")
            related_damage_reports = BienBanMatHongVatTu.objects.for_tenant(tenant_id).select_for_update().filter(
                phieu_thu_hoi=document
            )
            active_damage_reports = related_damage_reports.exclude(
                trang_thai=BienBanMatHongVatTu.TrangThai.CANCELLED
            )
            if active_damage_reports.exists():
                raise AssetRecoveryError(
                    "Không được hủy phiếu thu hồi khi còn biên bản mất/hỏng chưa hủy. "
                    "Hãy hủy/khóa biên bản mất/hỏng trước khi void phiếu thu hồi."
                )

            linked_deduction_reports = related_damage_reports.exclude(khoan_khau_tru_id__isnull=True).select_related(
                "khoan_khau_tru"
            )
            terminal_deduction_statuses = set()
            for status_name in ("CANCELLED", "REJECTED"):
                status_value = getattr(KhoanKhauTruNhanVien.TrangThai, status_name, None)
                if status_value:
                    terminal_deduction_statuses.add(status_value)
            if not terminal_deduction_statuses and linked_deduction_reports.exists():
                raise AssetRecoveryError(
                    "Không được hủy phiếu thu hồi vì đã phát sinh khoản khấu trừ liên quan."
                )
            if terminal_deduction_statuses and linked_deduction_reports.exclude(
                khoan_khau_tru__trang_thai__in=terminal_deduction_statuses
            ).exists():
                raise AssetRecoveryError(
                    "Không được hủy phiếu thu hồi vì khoản khấu trừ liên quan chưa bị hủy/từ chối."
                )

            details = list(document.chi_tiet.select_related("vat_tu").order_by("pk"))
            for detail in details:
                if not detail.so_luong_nhap_lai_kho:
                    continue
                vat_tu = VatTu.objects.for_tenant(tenant_id).select_for_update().get(pk=detail.vat_tu_id)
                stock_before = vat_tu.so_luong_ton or 0
                if stock_before < detail.so_luong_nhap_lai_kho:
                    raise AssetRecoveryError(f"Không đủ tồn để reversal phiếu thu hồi cho {vat_tu.ten_vat_tu}.")
                stock_after = stock_before - detail.so_luong_nhap_lai_kho
                VatTu.objects.for_tenant(tenant_id).filter(pk=vat_tu.pk).update(so_luong_ton=stock_after)
                PostAssetRecoveryUseCase._create_ledger_entry(
                    phieu_thu_hoi=document,
                    detail=detail,
                    vat_tu=vat_tu,
                    stock_before=stock_before,
                    stock_after=stock_after,
                    quantity_delta=-detail.so_luong_nhap_lai_kho,
                    direction=InventoryLedgerEntry.Direction.OUT,
                    movement_type=InventoryLedgerEntry.MovementType.REVERSAL,
                    reason=str(reason).strip(),
                )
            document.trang_thai = PhieuThuHoi.TrangThai.VOIDED
            document.voided_at = timezone.now()
            document.save(update_fields=["trang_thai", "voided_at", "updated_at"])
            AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="inventory",
                model_name="PhieuThuHoi",
                object_id=str(document.pk),
                tenant_id=document.tenant_id,
                note=(
                    f"Hủy phiếu thu hồi tài sản: {reason}. "
                    "Đã xác nhận không còn biên bản mất/hỏng hoặc khoản khấu trừ còn hiệu lực."
                ),
                changes={
                    "trang_thai": document.trang_thai,
                    "void_guard": {
                        "active_damage_reports": 0,
                        "active_deductions": 0,
                    },
                },
            )
            return document


class ApproveAssetDamageReportUseCase:
    """Approve a damage report and create a pending employee deduction source record."""

    @staticmethod
    def execute(*, bien_ban, actor=None):
        AssetRecoveryPermissionPolicy.require(
            AssetRecoveryPermissionPolicy.can_approve_damage_report(actor),
            "Không có quyền duyệt biên bản mất/hỏng tài sản.",
        )
        tenant_id = _tenant_id_from(bien_ban)
        with transaction.atomic():
            report = BienBanMatHongVatTu.objects.for_tenant(tenant_id).select_for_update().get(pk=bien_ban.pk)
            if report.trang_thai == BienBanMatHongVatTu.TrangThai.APPLIED and report.khoan_khau_tru_id:
                return report.khoan_khau_tru
            if report.trang_thai == BienBanMatHongVatTu.TrangThai.DRAFT:
                report.transition_status(BienBanMatHongVatTu.TrangThai.PENDING_APPROVAL, actor=actor, note="Submit asset damage report for approval")
                report.refresh_from_db()
            if report.trang_thai == BienBanMatHongVatTu.TrangThai.PENDING_APPROVAL:
                report.transition_status(BienBanMatHongVatTu.TrangThai.APPROVED, actor=actor, note="Approve asset damage report")
                report.refresh_from_db()
            if report.trang_thai != BienBanMatHongVatTu.TrangThai.APPROVED:
                raise AssetRecoveryError("Chỉ biên bản đã APPROVED mới được tạo khoản khấu trừ.")
            if not report.khoan_khau_tru_id:
                deduction = KhoanKhauTruNhanVien.objects.for_tenant(tenant_id).create(
                    nhan_vien=report.nhan_vien,
                    so_chung_tu=f"BBMH-{report.pk}",
                    loai_khau_tru=KhoanKhauTruNhanVien.LoaiKhauTru.DEN_BU,
                    ngay_ap_dung=timezone.localdate(),
                    so_tien=report.tong_tien,
                    trang_thai=KhoanKhauTruNhanVien.TrangThai.PENDING_APPROVAL,
                    ly_do=report.ly_do or f"Đền bù {report.vat_tu.ten_vat_tu} theo biên bản {report.pk}",
                    file_minh_chung=report.file_minh_chung,
                    ghi_chu="Tạo từ biên bản mất/hỏng vật tư Phase F. Payroll sẽ xử lý ở quy trình khấu trừ riêng.",
                )
                report.khoan_khau_tru = deduction
                report.trang_thai = BienBanMatHongVatTu.TrangThai.APPLIED
                report.save(update_fields=["khoan_khau_tru", "trang_thai", "updated_at"])
                report.record_status_transition(actor=actor, old_status=BienBanMatHongVatTu.TrangThai.APPROVED, new_status=BienBanMatHongVatTu.TrangThai.APPLIED, note="Create payroll deduction source from asset damage report")
                AuditLog.objects.create(
                    user=actor if getattr(actor, "is_authenticated", False) else None,
                    action=AuditLog.Action.CREATE,
                    module="accounting",
                    model_name="KhoanKhauTruNhanVien",
                    object_id=str(deduction.pk),
                    tenant_id=tenant_id,
                    note="Tạo khoản khấu trừ từ biên bản mất/hỏng vật tư.",
                    changes={"bien_ban_mat_hong_id": report.pk, "so_tien": str(report.tong_tien)},
                )
            return report.khoan_khau_tru


CreateAssetDamageDeductionUseCase = ApproveAssetDamageReportUseCase


__all__ = [
    "AssetRecoveryError",
    "GetEmployeeOutstandingAssetsUseCase",
    "PostAssetRecoveryUseCase",
    "VoidAssetRecoveryUseCase",
    "ApproveAssetDamageReportUseCase",
    "CreateAssetDamageDeductionUseCase",
]
