# -*- coding: utf-8 -*-
"""
Inventory ledger models for immutable stock reconciliation.
"""

from typing import TYPE_CHECKING, Optional
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.managers import TenantAwareManager, TenantScopedModel


class InventoryLedgerEntry(TenantScopedModel):
    """Ledger bất biến cho mọi biến động tồn kho phát sinh từ posting/reversal."""

    objects = TenantAwareManager()

    if TYPE_CHECKING:
        # Type hints cho các trường ID tự sinh từ ForeignKey
        phieu_nhap_id: Optional[int]
        phieu_xuat_id: Optional[int]
        chi_tiet_phieu_nhap_id: Optional[int]
        chi_tiet_phieu_xuat_id: Optional[int]
        phieu_thu_hoi_id: Optional[int]
        chi_tiet_phieu_thu_hoi_id: Optional[int]

    class DocumentType(models.TextChoices):
        RECEIPT = "RECEIPT", _("Phiếu nhập")
        ISSUE = "ISSUE", _("Phiếu xuất")
        RECOVERY = "RECOVERY", _("Phiếu thu hồi")

    class MovementType(models.TextChoices):
        POSTING = "POSTING", _("Ghi sổ")
        REVERSAL = "REVERSAL", _("Đảo bút toán")

    class Direction(models.TextChoices):
        IN = "IN", _("Tăng tồn")
        OUT = "OUT", _("Giảm tồn")

    phieu_nhap = models.ForeignKey(
        "inventory.PhieuNhap",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
        verbose_name=_("Phiếu nhập liên quan"),
    )
    phieu_xuat = models.ForeignKey(
        "inventory.PhieuXuat",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
        verbose_name=_("Phiếu xuất liên quan"),
    )
    phieu_thu_hoi = models.ForeignKey(
        "inventory.PhieuThuHoi",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
        verbose_name=_("Phiếu thu hồi liên quan"),
    )
    chi_tiet_phieu_nhap = models.ForeignKey(
        "inventory.ChiTietPhieuNhap",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
        verbose_name=_("Chi tiết phiếu nhập liên quan"),
    )
    chi_tiet_phieu_xuat = models.ForeignKey(
        "inventory.ChiTietPhieuXuat",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
        verbose_name=_("Chi tiết phiếu xuất liên quan"),
    )
    chi_tiet_phieu_thu_hoi = models.ForeignKey(
        "inventory.ChiTietPhieuThuHoi",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
        verbose_name=_("Chi tiết phiếu thu hồi liên quan"),
    )
    vat_tu = models.ForeignKey("inventory.VatTu", on_delete=models.PROTECT, related_name="ledger_entries")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    direction = models.CharField(max_length=10, choices=Direction.choices)
    quantity_delta = models.IntegerField(_("Biến động số lượng"))
    stock_before = models.IntegerField(_("Tồn trước giao dịch"))
    stock_after = models.IntegerField(_("Tồn sau giao dịch"))
    reason = models.TextField(_("Diễn giải đối soát"), blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Ledger tồn kho")
        verbose_name_plural = _("6. Ledger tồn kho")
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["vat_tu", "-created_at"],
                name="inv_led_vt_cr_idx",
            ),
            models.Index(
                fields=["tenant_id", "vat_tu", "-created_at"],
                name="inv_led_tenant_vt_cr_idx",
            ),
            models.Index(
                fields=["phieu_nhap", "-created_at"],
                name="inv_led_pn_cr_idx",
            ),
            models.Index(
                fields=["phieu_xuat", "-created_at"],
                name="inv_led_px_cr_idx",
            ),
            models.Index(
                fields=["phieu_thu_hoi", "-created_at"],
                name="inv_led_rec_cr_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["chi_tiet_phieu_nhap", "movement_type"],
                condition=models.Q(chi_tiet_phieu_nhap__isnull=False),
                name="inventory_ledger_unique_receipt_detail_movement",
            ),
            models.UniqueConstraint(
                fields=["chi_tiet_phieu_xuat", "movement_type"],
                condition=models.Q(chi_tiet_phieu_xuat__isnull=False),
                name="inventory_ledger_unique_issue_detail_movement",
            ),
            models.UniqueConstraint(
                fields=["chi_tiet_phieu_thu_hoi", "movement_type"],
                condition=models.Q(chi_tiet_phieu_thu_hoi__isnull=False),
                name="inventory_ledger_unique_recovery_detail_movement",
            ),
        ]

    def clean(self):
        super().clean()
        document_ids = [self.phieu_nhap_id, self.phieu_xuat_id, self.phieu_thu_hoi_id]
        if sum(1 for value in document_ids if value) != 1:
            raise ValidationError(_("Ledger tồn kho phải gắn với đúng một chứng từ kho."))
        detail_ids = [self.chi_tiet_phieu_nhap_id, self.chi_tiet_phieu_xuat_id, self.chi_tiet_phieu_thu_hoi_id]
        if sum(1 for value in detail_ids if value) > 1:
            raise ValidationError(_("Ledger tồn kho chỉ được gắn với một dòng chi tiết kho."))
        if self.phieu_nhap_id and (self.chi_tiet_phieu_xuat_id or self.chi_tiet_phieu_thu_hoi_id):
            raise ValidationError(_("Ledger phiếu nhập không được gắn với chi tiết phiếu xuất/thu hồi."))
        if self.phieu_xuat_id and (self.chi_tiet_phieu_nhap_id or self.chi_tiet_phieu_thu_hoi_id):
            raise ValidationError(_("Ledger phiếu xuất không được gắn với chi tiết phiếu nhập/thu hồi."))
        if self.phieu_thu_hoi_id and (self.chi_tiet_phieu_nhap_id or self.chi_tiet_phieu_xuat_id):
            raise ValidationError(_("Ledger phiếu thu hồi không được gắn với chi tiết phiếu nhập/xuất."))

    def __str__(self):
        # SCMD Pro: Sử dụng logic truy cập an toàn để tránh lỗi 'None' attribute access (Pylance)
        document_code = "N/A"
        if self.phieu_nhap_id and self.phieu_nhap:
            document_code = self.phieu_nhap.ma_phieu
        elif self.phieu_xuat_id and self.phieu_xuat:
            document_code = self.phieu_xuat.ma_phieu
        elif self.phieu_thu_hoi_id and self.phieu_thu_hoi:
            document_code = self.phieu_thu_hoi.ma_phieu

        return f"{document_code} - {self.vat_tu.ten_vat_tu} ({self.quantity_delta:+d})"
