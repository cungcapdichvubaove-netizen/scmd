# -*- coding: utf-8 -*-
from django.db import models, transaction
from django.conf import settings
from django.core.validators import MinValueValidator
from core.managers import TenantAwareManager, TenantScopedModel
from main.models import AuditLog

class DieuChinhTonKho(TenantScopedModel):
    """
    [F-011] Phiếu điều chỉnh tồn kho / Kiểm kê.
    Lưu trữ thông tin xác nhận sai lệch giữa kho hệ thống và thực tế.
    """
    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", "Bản nháp"
        POSTED = "POSTED", "Đã ghi sổ (Hoàn tất)"
        VOIDED = "VOIDED", "Đã hủy"

    ma_phieu = models.CharField("Mã phiếu", max_length=50, unique=True, db_index=True)
    ngay_dieu_chinh = models.DateTimeField("Ngày điều chỉnh", auto_now_add=True)
    nguoi_lap = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="cac_phieu_dieu_chinh_da_lap",
        verbose_name="Người lập"
    )
    nguoi_xac_nhan = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name="cac_phieu_dieu_chinh_da_duyet",
        verbose_name="Người xác nhận"
    )
    ly_do = models.TextField("Lý do điều chỉnh", help_text="Ví dụ: Kiểm kê định kỳ tháng 05, hàng hỏng...")
    trang_thai = models.CharField(
        "Trạng thái", 
        max_length=20, 
        choices=TrangThai.choices, 
        default=TrangThai.DRAFT
    )
    ghi_chu_audit = models.TextField("Ghi chú đối soát", blank=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Phiếu điều chỉnh tồn kho"
        verbose_name_plural = "6. Điều chỉnh tồn kho"
        ordering = ["-ngay_dieu_chinh"]

    def __str__(self):
        return f"{self.ma_phieu} ({self.get_trang_thai_display()})"

    @transaction.atomic
    def post_to_ledger(self, user):
        """Kích hoạt ghi sổ điều chỉnh tồn kho vào Ledger"""
        # SCMD Pro: Enforce organization scope guard for internal state verification.
        # Re-read state from DB so stale in-memory objects cannot bypass logic (WHITEPAPER 9).
        trang_thai_hien_tai = self.trang_thai
        if self.pk:
            trang_thai_hien_tai = (
                type(self).objects
                .select_for_update()
                .for_tenant(self.tenant_id)
                .filter(pk=self.pk)
                .values_list("trang_thai", flat=True)
                .first()
                or self.trang_thai
            )

        if trang_thai_hien_tai != self.TrangThai.DRAFT:
            return False, "Chỉ có thể ghi sổ phiếu ở trạng thái Nháp."

        for detail in self.chi_tiet.all():
            # Tạo bút toán Ledger cho từng dòng
            # Logic: Nếu chênh lệch > 0 -> Tăng tồn; < 0 -> Giảm tồn
            detail.vat_tu.create_ledger_entry(
                change_qty=detail.so_luong_chenh_lech,
                source_type="ADJUSTMENT",
                reference_id=self.id,
                note=f"Điều chỉnh theo phiếu {self.ma_phieu}"
            )
        
        self.trang_thai = self.TrangThai.POSTED
        self.nguoi_xac_nhan = user
        self.save()

        # [Rule 8.2] Ghi nhận Audit Log bắt buộc
        AuditLog.objects.create(
            user=user,
            tenant_id=self.tenant_id,
            action="POST",
            module="inventory",
            model_name="DieuChinhTonKho",
            object_id=self.id,
            note=f"Ghi sổ phiếu điều chỉnh {self.ma_phieu}. Lý do: {self.ly_do}"
        )
        return True, "Ghi sổ thành công."

class ChiTietDieuChinh(models.Model):
    """Chi tiết từng vật tư trong phiếu điều chỉnh"""
    phieu = models.ForeignKey(
        DieuChinhTonKho, 
        on_delete=models.CASCADE, 
        related_name="chi_tiet"
    )
    vat_tu = models.ForeignKey(
        "inventory.VatTu", 
        on_delete=models.PROTECT, 
        verbose_name="Vật tư"
    )
    so_luong_he_thong = models.IntegerField("Tồn hệ thống", help_text="Số lượng tồn tại thời điểm kiểm kê")
    so_luong_thuc_te = models.IntegerField("Tồn thực tế", validators=[MinValueValidator(0)])
    
    @property
    def so_luong_chenh_lech(self):
        return self.so_luong_thuc_te - self.so_luong_he_thong

    class Meta:
        verbose_name = "Chi tiết điều chỉnh"
