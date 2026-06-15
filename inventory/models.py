# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: inventory/models.py
Author: Mr. Anh
Created Date: 2025-11-30
Description: Model quản lý Kho & Vật tư.
             Đã nâng cấp: Phân biệt Cấp phát (Free) và Bán (Trừ lương) theo đặc thù ngành Bảo vệ.
             Nâng cấp chuyên sâu: Tối ưu hóa logic tính toán tiền tệ, PEP8 và Error Handling.

NOTICE: This file is part of a proprietary system. 
Unauthorized copying of this file, via any medium is strictly prohibited.
"""

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from users.models import NhanVien
from clients.models import MucTieu
from inventory.models_ledger import InventoryLedgerEntry
from core.managers import TenantAwareManager, TenantScopedModel


# --- 1. DANH MỤC VẬT TƯ ---

class LoaiVatTu(TenantScopedModel):
    """Phân loại vật tư: Đồng phục, CCHT, Thiết bị an ninh..."""
    ten_loai = models.CharField(_("Tên loại vật tư"), max_length=100)
    mo_ta = models.TextField(_("Mô tả danh mục"), blank=True, default="")

    def __str__(self):
        return str(self.ten_loai)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = _("1. Loại vật tư")
        verbose_name_plural = _("1. Loại vật tư")
        indexes = [models.Index(fields=["tenant_id", "ten_loai"], name="inv_lvt_tenant_name_idx")]


class VatTu(TenantScopedModel):
    """Danh mục vật tư và Công cụ hỗ trợ (CCHT) chi tiết"""
    loai_vat_tu = models.ForeignKey(
        LoaiVatTu, 
        on_delete=models.SET_NULL, 
        verbose_name=_("Nhóm vật tư"), 
        null=True, 
        blank=True
    )
    ten_vat_tu = models.CharField(_("Tên vật tư/CCHT"), max_length=200)
    don_vi_tinh = models.CharField(_("Đơn vị tính"), max_length=50, default="Cái")
    
    # Giá vốn và Giá bán cho nhân viên
    gia_nhap = models.DecimalField(_("Giá vốn (Nhập)"), max_digits=12, decimal_places=0, default=0)
    gia_ban = models.DecimalField(
        _("Giá bán/Trừ lương"), 
        max_digits=12, 
        decimal_places=0, 
        default=0, 
        help_text=_("Giá áp dụng khi nhân viên mua thêm hoặc làm mất/hư hỏng")
    )
    
    so_luong_ton = models.IntegerField(_("Tồn kho hiện tại"), default=0)
    hinh_anh = models.ImageField(_("Ảnh minh họa"), upload_to="vattu/", null=True, blank=True)
    muc_canh_bao = models.IntegerField(_("Mức cảnh báo tồn tối thiểu"), default=10)

    objects = TenantAwareManager()
    
    def __str__(self):
        return f"{self.ten_vat_tu} (Tồn: {self.so_luong_ton})"

    class Meta:
        verbose_name = _("2. Vật tư & CCHT")
        verbose_name_plural = _("2. Kho Tổng")
        indexes = [models.Index(fields=["tenant_id", "so_luong_ton"])]


# --- 2. QUẢN LÝ CÔNG CỤ TẠI MỤC TIÊU ---

class CongCuTaiMucTieu(TenantScopedModel):
    """Theo dõi số lượng CCHT thực tế đang bàn giao cho từng Mục tiêu bảo vệ"""
    # Rule 6.4: Chống xóa cascade để bảo vệ dữ liệu kiểm toán tồn kho tại mục tiêu.
    muc_tieu = models.ForeignKey(
        MucTieu, on_delete=models.PROTECT, verbose_name=_("Mục tiêu bảo vệ")
    )
    vat_tu = models.ForeignKey(
        VatTu, on_delete=models.PROTECT, verbose_name=_("Tên công cụ")
    )
    so_luong_dang_giu = models.PositiveIntegerField(_("Số lượng thực tế tại MT"), default=0)
    ngay_cap_gan_nhat = models.DateField(_("Ngày cập nhật gần nhất"), auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        unique_together = ('muc_tieu', 'vat_tu')
        verbose_name = _("3. Công cụ tại Mục tiêu")
        verbose_name_plural = _("3. Công cụ tại Mục tiêu")
        indexes = [models.Index(fields=["tenant_id", "muc_tieu"], name="inv_cctmt_tenant_mt_idx")]
    
    def __str__(self):
        return f"{self.muc_tieu} - {self.vat_tu} (SL: {self.so_luong_dang_giu})"


# --- 3. PHIẾU NHẬP KHO ---

class PhieuNhap(TenantScopedModel):
    """Hồ sơ nhập kho vật tư từ nhà cung cấp hoặc thu hồi"""
    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", _("Nháp")
        POSTED = "POSTED", _("Đã ghi sổ")
        VOIDED = "VOIDED", _("Đã hủy")

    ma_phieu = models.CharField(_("Mã số phiếu nhập"), max_length=50, unique=True)
    nguoi_nhap = models.ForeignKey(
        NhanVien, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name=_("Thủ kho thực hiện")
    )
    ngay_nhap = models.DateTimeField(_("Ngày giờ nhập kho"), default=timezone.now)
    trang_thai = models.CharField(
        _("Trạng thái chứng từ"),
        max_length=20,
        choices=TrangThai.choices,
        default=TrangThai.DRAFT,
        db_index=True,
    )
    ghi_chu = models.TextField(_("Ghi chú nhập"), blank=True)

    objects = TenantAwareManager()

    def __str__(self):
        time_str = self.ngay_nhap.astimezone().strftime('%d/%m/%Y')
        return f"Nhập: {self.ma_phieu} ({time_str})"

    class Meta:
        verbose_name = _("4. Phiếu Nhập kho")
        verbose_name_plural = _("4. Quản lý Nhập kho")
        indexes = [models.Index(fields=["tenant_id", "trang_thai", "ngay_nhap"], name="inv_pn_tenant_state_dt_idx")]

    @property
    def is_posted(self):
        return self.trang_thai == self.TrangThai.POSTED

    @property
    def is_voided(self):
        return self.trang_thai == self.TrangThai.VOIDED

    @transaction.atomic
    def delete(self, *args, **kwargs):
        # Chỉ cho phép hard delete chứng từ kho còn ở trạng thái nháp.
        # Re-read state from DB so stale in-memory objects cannot bypass the
        # inventory audit guard after an application use case posts/voids them.
        trang_thai_hien_tai = self.trang_thai
        if self.pk:
            trang_thai_hien_tai = (
                type(self).objects
                .for_tenant(self.tenant_id)
                .select_for_update()
                .filter(pk=self.pk)
                .values_list("trang_thai", flat=True)
                .first()
                or self.trang_thai
            )
        if trang_thai_hien_tai != self.TrangThai.DRAFT:
            raise ValidationError(_("Không được xóa cứng phiếu nhập đã ghi sổ hoặc đã hủy."))
        return super().delete(*args, **kwargs)


class ChiTietPhieuNhap(TenantScopedModel):
    """Chi tiết danh sách vật tư trong một phiếu nhập"""
    phieu_nhap = models.ForeignKey(PhieuNhap, related_name='chi_tiet', on_delete=models.CASCADE)
    # Rule 6.4: Bảo vệ Audit Trail - không được xóa Vật tư nếu đã phát sinh phiếu nhập.
    vat_tu = models.ForeignKey(
        VatTu, on_delete=models.PROTECT, verbose_name=_("Vật tư")
    )
    so_luong = models.PositiveIntegerField(_("Số lượng nhập"))
    don_gia = models.DecimalField(_("Đơn giá nhập thực tế"), max_digits=12, decimal_places=0, default=0)

    objects = TenantAwareManager()

    @property
    def thanh_tien(self): 
        sl = self.so_luong if self.so_luong else 0
        dg = self.don_gia if self.don_gia else 0
        return sl * dg

    class Meta:
        verbose_name = _("Chi tiết phiếu nhập")
        verbose_name_plural = _("Chi tiết phiếu nhập")

    def clean(self):
        super().clean()
        if self.phieu_nhap_id and self.phieu_nhap.trang_thai != PhieuNhap.TrangThai.DRAFT:
            raise ValidationError(_("Không được sửa chi tiết khi phiếu nhập đã ghi sổ hoặc đã hủy."))

    def save(self, *args, **kwargs):
        # Rule 6.4: Chốt chặn cuối cùng ngăn sửa đổi dữ liệu đã ghi sổ
        if self.phieu_nhap_id and self.phieu_nhap.trang_thai != PhieuNhap.TrangThai.DRAFT:
            raise ValidationError(_("Không được sửa dòng vật tư khi phiếu nhập đã ghi sổ hoặc đã hủy."))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Rule 6.4: Ngăn chặn xóa liên đới hoặc xóa trực tiếp dòng vật tư đã chốt
        if self.phieu_nhap_id and self.phieu_nhap.trang_thai != PhieuNhap.TrangThai.DRAFT:
            raise ValidationError(_("Không được xóa dòng vật tư khi phiếu nhập đã ghi sổ hoặc đã hủy."))
        return super().delete(*args, **kwargs)


# --- 4. PHIẾU XUẤT KHO ---

class PhieuXuat(TenantScopedModel):
    """Hồ sơ xuất kho: Cấp phát định mức, bán trừ lương hoặc cấp cho mục tiêu"""
    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", _("Nháp")
        POSTED = "POSTED", _("Đã ghi sổ")
        VOIDED = "VOIDED", _("Đã hủy")

    LOAI_XUAT = [
        ('CAP_PHAT', _('Cấp phát (Miễn phí/Định mức)')),
        ('BAN_TRU_LUONG', _('Bán (Khấu trừ vào lương tháng)')),
        ('CONG_CU', _('Cấp CCHT cho Mục tiêu (Không thu tiền)')),
        ('HUY', _('Xuất hủy/Thanh lý tài sản')),
    ]
    
    TRANG_THAI_TT = [
        ('KHONG_AP_DUNG', _('Không áp dụng')),
        ('CHUA_TRU', _('Chờ khấu trừ lương')),
        ('DA_TRU', _('Đã hoàn tất trừ lương')),
    ]
    
    ma_phieu = models.CharField(_("Mã số phiếu xuất"), max_length=50, unique=True)
    loai_xuat = models.CharField(_("Hình thức xuất"), max_length=20, choices=LOAI_XUAT, default='CAP_PHAT')
    trang_thai_thanh_toan = models.CharField(
        _("Trạng thái thanh toán"), 
        max_length=20, 
        choices=TRANG_THAI_TT, 
        default='KHONG_AP_DUNG'
    )
    
    ngay_xuat = models.DateTimeField(_("Ngày giờ xuất kho"), default=timezone.now)
    nhan_vien_nhan = models.ForeignKey(
        NhanVien, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_("Nhân viên tiếp nhận")
    )
    muc_tieu_nhan = models.ForeignKey(
        MucTieu, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_("Mục tiêu tiếp nhận (CCHT)")
    )
    
    ghi_chu = models.TextField(_("Ghi chú xuất"), blank=True)
    tong_tien_phai_thu = models.DecimalField(
        _("Tổng tiền khấu trừ"), 
        max_digits=15, 
        decimal_places=0, 
        default=0, 
        editable=False
    )
    trang_thai = models.CharField(
        _("Trạng thái chứng từ"),
        max_length=20,
        choices=TrangThai.choices,
        default=TrangThai.DRAFT,
        db_index=True,
    )

    objects = TenantAwareManager()

    def clean(self):
        """Kiểm tra logic nghiệp vụ khi lập phiếu xuất"""
        if self.loai_xuat in ['CAP_PHAT', 'BAN_TRU_LUONG'] and not self.nhan_vien_nhan:
            raise ValidationError(_("Lỗi: Xuất cho Cá nhân bắt buộc phải chọn Nhân viên nhận."))
        if self.loai_xuat == 'CONG_CU' and not self.muc_tieu_nhan:
            raise ValidationError(_("Lỗi: Cấp CCHT bắt buộc phải chọn Mục tiêu nhận."))

    def save(self, *args, **kwargs):
        """Tự động hóa trạng thái thanh toán dựa trên loại xuất"""
        if self.loai_xuat == 'BAN_TRU_LUONG':
            if self.trang_thai_thanh_toan == 'KHONG_AP_DUNG':
                self.trang_thai_thanh_toan = 'CHUA_TRU'
        else:
            self.trang_thai_thanh_toan = 'KHONG_AP_DUNG'
            
        super().save(*args, **kwargs)

    def __str__(self): 
        return f"{self.ma_phieu} - {self.get_loai_xuat_display()}"
    
    class Meta:
        verbose_name = _("5. Phiếu Xuất kho")
        verbose_name_plural = _("5. Quản lý Xuất kho")
        indexes = [models.Index(fields=["tenant_id", "trang_thai", "ngay_xuat"], name="inv_px_tenant_state_dt_idx")]

    @property
    def is_posted(self):
        return self.trang_thai == self.TrangThai.POSTED

    @property
    def is_voided(self):
        return self.trang_thai == self.TrangThai.VOIDED

    @transaction.atomic
    def delete(self, *args, **kwargs):
        # Chỉ cho phép hard delete chứng từ kho còn ở trạng thái nháp.
        # Re-read state from DB so stale in-memory objects cannot bypass the
        # inventory audit guard after an application use case posts/voids them.
        trang_thai_hien_tai = self.trang_thai
        if self.pk:
            trang_thai_hien_tai = (
                type(self).objects
                .for_tenant(self.tenant_id)
                .select_for_update()
                .filter(pk=self.pk)
                .values_list("trang_thai", flat=True)
                .first()
                or self.trang_thai
            )
        if trang_thai_hien_tai != self.TrangThai.DRAFT:
            raise ValidationError(_("Không được xóa cứng phiếu xuất đã ghi sổ hoặc đã hủy."))
        return super().delete(*args, **kwargs)


class ChiTietPhieuXuat(TenantScopedModel):
    """Chi tiết danh sách vật tư trong một phiếu xuất"""
    phieu_xuat = models.ForeignKey(PhieuXuat, related_name='chi_tiet', on_delete=models.CASCADE)
    # Rule 6.4: Bảo vệ Audit Trail - không được xóa Vật tư nếu đã phát sinh phiếu xuất.
    vat_tu = models.ForeignKey(
        VatTu, on_delete=models.PROTECT, verbose_name=_("Vật tư/CCHT")
    )
    so_luong = models.PositiveIntegerField(_("Số lượng xuất"))
    
    # Lưu giá bán tại thời điểm xuất để tránh biến động giá danh mục sau này
    don_gia_ban = models.DecimalField(_("Đơn giá áp dụng"), max_digits=12, decimal_places=0, default=0)

    objects = TenantAwareManager()

    def save(self, *args, **kwargs):
        """Tự động snapshot đơn giá bán tại thời điểm lập chi tiết."""
        # Rule 6.4: Chốt chặn cuối cùng ngăn sửa đổi dữ liệu đã ghi sổ
        if self.phieu_xuat_id and self.phieu_xuat.trang_thai != PhieuXuat.TrangThai.DRAFT:
            raise ValidationError(_("Không được sửa dòng vật tư khi phiếu xuất đã ghi sổ hoặc đã hủy."))
            
        # 1. Tự động áp đơn giá từ danh mục nếu chưa có
        if self.don_gia_ban == 0 and self.vat_tu:
            self.don_gia_ban = self.vat_tu.gia_ban
            
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Rule 6.4: Ngăn chặn xóa liên đới hoặc xóa trực tiếp dòng vật tư đã chốt
        if self.phieu_xuat_id and self.phieu_xuat.trang_thai != PhieuXuat.TrangThai.DRAFT:
            raise ValidationError(_("Không được xóa dòng vật tư khi phiếu xuất đã ghi sổ hoặc đã hủy."))
        return super().delete(*args, **kwargs)

    def clean(self):
        """Kiểm tra tồn kho thực tế trước khi xuất"""
        super().clean()
        if not self.so_luong or not self.vat_tu:
            return
        if self.phieu_xuat_id and self.phieu_xuat.trang_thai != PhieuXuat.TrangThai.DRAFT:
            raise ValidationError(_("Không được sửa chi tiết khi phiếu xuất đã ghi sổ hoặc đã hủy."))
            
        ton_kho = self.vat_tu.so_luong_ton if self.vat_tu.so_luong_ton is not None else 0
        if ton_kho < self.so_luong:
            raise ValidationError(
                _(f"Lỗi kho: Vật tư {self.vat_tu.ten_vat_tu} không đủ tồn (Hiện có: {ton_kho})")
            )

    class Meta:
        verbose_name = _("Chi tiết phiếu xuất")
        verbose_name_plural = _("Chi tiết phiếu xuất")


# --- 5. PHIẾU THU HỒI TÀI SẢN / OFFBOARDING ---

class PhieuThuHoi(TenantScopedModel):
    """Hồ sơ nguồn thu hồi đồng phục/công cụ/tài sản từ nhân viên."""

    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", _("Nháp")
        POSTED = "POSTED", _("Đã ghi sổ")
        VOIDED = "VOIDED", _("Đã hủy")

    ma_phieu = models.CharField(_("Mã phiếu thu hồi"), max_length=64, db_index=True)
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.PROTECT, related_name="cac_phieu_thu_hoi_tai_san", verbose_name=_("Nhân viên bàn giao"))
    quyet_dinh_nghi_viec = models.ForeignKey("users.QuyetDinhNghiViec", on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_phieu_thu_hoi_tai_san", verbose_name=_("Quyết định nghỉ việc"))
    offboarding_checklist = models.ForeignKey("users.OffboardingChecklist", on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_phieu_thu_hoi_tai_san", verbose_name=_("Checklist offboarding"))
    ngay_thu_hoi = models.DateTimeField(_("Ngày thu hồi"), default=timezone.now, db_index=True)
    nguoi_thu_hoi = models.ForeignKey(NhanVien, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_phieu_da_thu_hoi", verbose_name=_("Người thu hồi"))
    file_bien_ban = models.FileField(_("File biên bản"), upload_to="phieu_thu_hoi/%Y/%m/", null=True, blank=True)
    trang_thai = models.CharField(_("Trạng thái"), max_length=20, choices=TrangThai.choices, default=TrangThai.DRAFT, db_index=True)
    ghi_chu = models.TextField(_("Ghi chú"), blank=True)
    posted_at = models.DateTimeField(_("Thời điểm ghi sổ"), null=True, blank=True)
    voided_at = models.DateTimeField(_("Thời điểm hủy"), null=True, blank=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = _("7. Phiếu thu hồi tài sản")
        verbose_name_plural = _("7. Phiếu thu hồi tài sản")
        ordering = ["-ngay_thu_hoi", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "ngay_thu_hoi"], name="inv_rec_tenant_state_dt_idx"),
            models.Index(fields=["tenant_id", "nhan_vien", "trang_thai"], name="inv_rec_tenant_staff_st_idx"),
        ]
        constraints = [models.UniqueConstraint(fields=["tenant_id", "ma_phieu"], name="uq_inv_recovery_tenant_code")]

    def __str__(self):
        return f"{self.ma_phieu} - {self.nhan_vien}"

    def clean(self):
        super().clean()
        if self.quyet_dinh_nghi_viec_id and self.quyet_dinh_nghi_viec.nhan_vien_id != self.nhan_vien_id:
            raise ValidationError(_("Quyết định nghỉ việc phải thuộc cùng nhân viên cần thu hồi."))
        if self.offboarding_checklist_id and self.offboarding_checklist.quyet_dinh.nhan_vien_id != self.nhan_vien_id:
            raise ValidationError(_("Checklist offboarding phải thuộc cùng nhân viên cần thu hồi."))

    @transaction.atomic
    def delete(self, *args, **kwargs):
        current_state = self.trang_thai
        if self.pk:
            current_state = (type(self).objects.for_tenant(self.tenant_id).select_for_update().filter(pk=self.pk).values_list("trang_thai", flat=True).first() or self.trang_thai)
        if current_state != self.TrangThai.DRAFT:
            raise ValidationError(_("Không được xóa cứng phiếu thu hồi đã ghi sổ hoặc đã hủy."))
        return super().delete(*args, **kwargs)


class ChiTietPhieuThuHoi(TenantScopedModel):
    """Dòng thu hồi trace về dòng phiếu xuất gốc đã cấp cho nhân viên."""

    class TinhTrang(models.TextChoices):
        TOT = "TOT", _("Tốt")
        HAO_MON = "HAO_MON", _("Hao mòn")
        HONG = "HONG", _("Hỏng")
        MAT = "MAT", _("Mất")
        THIEU = "THIEU", _("Thiếu")

    phieu_thu_hoi = models.ForeignKey(PhieuThuHoi, related_name="chi_tiet", on_delete=models.CASCADE, verbose_name=_("Phiếu thu hồi"))
    chi_tiet_phieu_xuat = models.ForeignKey(ChiTietPhieuXuat, on_delete=models.PROTECT, related_name="cac_dong_thu_hoi", verbose_name=_("Dòng phiếu xuất gốc"))
    vat_tu = models.ForeignKey(VatTu, on_delete=models.PROTECT, verbose_name=_("Vật tư"))
    so_luong_thu_hoi = models.PositiveIntegerField(_("Số lượng thu hồi"), default=0)
    so_luong_nhap_lai_kho = models.PositiveIntegerField(_("Số lượng nhập lại kho"), default=0)
    so_luong_mat_hong = models.PositiveIntegerField(_("Số lượng mất/hỏng/thiếu"), default=0)
    tinh_trang = models.CharField(_("Tình trạng"), max_length=20, choices=TinhTrang.choices, default=TinhTrang.TOT, db_index=True)
    ghi_chu = models.TextField(_("Ghi chú"), blank=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = _("Chi tiết phiếu thu hồi")
        verbose_name_plural = _("Chi tiết phiếu thu hồi")
        indexes = [
            models.Index(fields=["tenant_id", "chi_tiet_phieu_xuat"], name="inv_recl_tenant_issue_idx"),
            models.Index(fields=["tenant_id", "vat_tu", "tinh_trang"], name="inv_recl_tenant_vt_cond_idx"),
        ]

    def __str__(self):
        return f"{self.phieu_thu_hoi.ma_phieu} - {self.vat_tu}"

    def clean(self):
        super().clean()
        if self.phieu_thu_hoi_id and self.phieu_thu_hoi.trang_thai != PhieuThuHoi.TrangThai.DRAFT:
            raise ValidationError(_("Không được sửa chi tiết khi phiếu thu hồi đã ghi sổ hoặc đã hủy."))
        if self.chi_tiet_phieu_xuat_id:
            issue_line = self.chi_tiet_phieu_xuat
            issue_doc = issue_line.phieu_xuat
            if issue_doc.trang_thai != PhieuXuat.TrangThai.POSTED:
                raise ValidationError(_("Chỉ được thu hồi từ phiếu xuất đã ghi sổ."))
            if self.phieu_thu_hoi_id and issue_doc.nhan_vien_nhan_id != self.phieu_thu_hoi.nhan_vien_id:
                raise ValidationError(_("Phiếu xuất gốc không thuộc nhân viên trên phiếu thu hồi."))
            if self.vat_tu_id and issue_line.vat_tu_id != self.vat_tu_id:
                raise ValidationError(_("Vật tư thu hồi phải khớp dòng phiếu xuất gốc."))
        if self.so_luong_thu_hoi <= 0:
            raise ValidationError(_("Số lượng thu hồi phải lớn hơn 0."))
        if self.so_luong_thu_hoi != (self.so_luong_nhap_lai_kho + self.so_luong_mat_hong):
            raise ValidationError(_("Số lượng thu hồi phải bằng số nhập lại kho cộng số mất/hỏng/thiếu."))

    def save(self, *args, **kwargs):
        if self.chi_tiet_phieu_xuat_id and not self.vat_tu_id:
            self.vat_tu_id = self.chi_tiet_phieu_xuat.vat_tu_id
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.phieu_thu_hoi_id and self.phieu_thu_hoi.trang_thai != PhieuThuHoi.TrangThai.DRAFT:
            raise ValidationError(_("Không được xóa dòng thu hồi khi phiếu thu hồi đã ghi sổ hoặc đã hủy."))
        return super().delete(*args, **kwargs)


class BienBanMatHongVatTu(TenantScopedModel):
    """Biên bản mất/hỏng/thiếu tài sản, là nguồn tạo khoản khấu trừ nếu được duyệt."""

    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", _("Nháp")
        PENDING_APPROVAL = "PENDING_APPROVAL", _("Chờ duyệt")
        APPROVED = "APPROVED", _("Đã duyệt")
        APPLIED = "APPLIED", _("Đã áp dụng khấu trừ")
        CANCELLED = "CANCELLED", _("Đã hủy")

    ALLOWED_STATUS_TRANSITIONS = {
        TrangThai.DRAFT: {TrangThai.PENDING_APPROVAL, TrangThai.CANCELLED},
        TrangThai.PENDING_APPROVAL: {TrangThai.APPROVED, TrangThai.CANCELLED},
        TrangThai.APPROVED: {TrangThai.APPLIED, TrangThai.CANCELLED},
        TrangThai.APPLIED: set(),
        TrangThai.CANCELLED: set(),
    }

    phieu_thu_hoi = models.ForeignKey(PhieuThuHoi, on_delete=models.PROTECT, related_name="cac_bien_ban_mat_hong", verbose_name=_("Phiếu thu hồi"))
    chi_tiet_thu_hoi = models.ForeignKey(ChiTietPhieuThuHoi, on_delete=models.PROTECT, related_name="cac_bien_ban_mat_hong", verbose_name=_("Dòng thu hồi"))
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.PROTECT, related_name="cac_bien_ban_mat_hong_vat_tu", verbose_name=_("Nhân viên chịu trách nhiệm"))
    vat_tu = models.ForeignKey(VatTu, on_delete=models.PROTECT, related_name="cac_bien_ban_mat_hong", verbose_name=_("Vật tư"))
    so_luong = models.PositiveIntegerField(_("Số lượng mất/hỏng/thiếu"))
    don_gia_khau_tru = models.DecimalField(_("Đơn giá khấu trừ"), max_digits=12, decimal_places=0, default=0)
    tong_tien = models.DecimalField(_("Tổng tiền khấu trừ"), max_digits=14, decimal_places=0, default=0, editable=False)
    ly_do = models.TextField(_("Lý do"), blank=True)
    file_minh_chung = models.FileField(_("File minh chứng"), upload_to="bien_ban_mat_hong/%Y/%m/", null=True, blank=True)
    khoan_khau_tru = models.ForeignKey("accounting.KhoanKhauTruNhanVien", on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_bien_ban_mat_hong_vat_tu", verbose_name=_("Khoản khấu trừ liên quan"))
    trang_thai = models.CharField(_("Trạng thái"), max_length=32, choices=TrangThai.choices, default=TrangThai.DRAFT, db_index=True)
    nguoi_duyet = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_bien_ban_mat_hong_vat_tu_da_duyet", verbose_name=_("Người duyệt"))
    ngay_duyet = models.DateTimeField(_("Thời điểm duyệt"), null=True, blank=True)
    ghi_chu = models.TextField(_("Ghi chú"), blank=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = _("8. Biên bản mất/hỏng vật tư")
        verbose_name_plural = _("8. Biên bản mất/hỏng vật tư")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "created_at"], name="inv_dmg_tenant_stat_cr_idx"),
            models.Index(fields=["tenant_id", "nhan_vien", "trang_thai"], name="inv_dmg_tenant_staff_st_idx"),
        ]

    def __str__(self):
        return f"{self.phieu_thu_hoi.ma_phieu} - {self.vat_tu} ({self.so_luong})"

    def clean(self):
        super().clean()
        if self.so_luong <= 0:
            raise ValidationError(_("Số lượng mất/hỏng/thiếu phải lớn hơn 0."))
        if self.chi_tiet_thu_hoi_id:
            if self.so_luong > self.chi_tiet_thu_hoi.so_luong_mat_hong:
                raise ValidationError(_("Số lượng biên bản không được vượt số mất/hỏng trên dòng thu hồi."))
            if self.phieu_thu_hoi_id and self.chi_tiet_thu_hoi.phieu_thu_hoi_id != self.phieu_thu_hoi_id:
                raise ValidationError(_("Dòng thu hồi phải thuộc phiếu thu hồi đã chọn."))
            if self.nhan_vien_id and self.chi_tiet_thu_hoi.phieu_thu_hoi.nhan_vien_id != self.nhan_vien_id:
                raise ValidationError(_("Nhân viên trên biên bản phải khớp phiếu thu hồi."))
            if self.vat_tu_id and self.chi_tiet_thu_hoi.vat_tu_id != self.vat_tu_id:
                raise ValidationError(_("Vật tư trên biên bản phải khớp dòng thu hồi."))

    def save(self, *args, **kwargs):
        self.tong_tien = (self.so_luong or 0) * (self.don_gia_khau_tru or 0)
        self.full_clean()
        return super().save(*args, **kwargs)

    def record_status_transition(self, *, actor=None, old_status=None, new_status=None, note=""):
        new_status = new_status if new_status is not None else self.trang_thai
        if old_status == new_status:
            return None
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="inventory",
                model_name="BienBanMatHongVatTu",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "Asset damage report status transition",
                changes={"status_transition": {"old": old_status, "new": new_status}, "tong_tien": str(self.tong_tien)},
            )
        except Exception:
            return None

    def transition_status(self, new_status, *, actor=None, note=""):
        from core.workflow_transition_policy import WorkflowTransitionPolicy
        old_status = self.trang_thai
        WorkflowTransitionPolicy.validate_transition(type(self).__name__, old_status, new_status, self.ALLOWED_STATUS_TRANSITIONS)
        self.trang_thai = new_status
        update_fields = ["trang_thai", "updated_at"]
        if new_status in (self.TrangThai.APPROVED, self.TrangThai.APPLIED) and actor and not self.nguoi_duyet_id:
            self.nguoi_duyet = actor
            self.ngay_duyet = timezone.now()
            update_fields.extend(["nguoi_duyet", "ngay_duyet"])
        self.save(update_fields=update_fields)
        return self.record_status_transition(actor=actor, old_status=old_status, new_status=new_status, note=note)
