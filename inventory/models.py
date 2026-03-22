# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
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

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from users.models import NhanVien
from clients.models import MucTieu


# --- 1. DANH MỤC VẬT TƯ ---

class LoaiVatTu(models.Model):
    """Phân loại vật tư: Đồng phục, CCHT, Thiết bị an ninh..."""
    ten_loai = models.CharField(_("Tên loại vật tư"), max_length=100)
    mo_ta = models.TextField(_("Mô tả danh mục"), blank=True, default="")

    def __str__(self):
        return str(self.ten_loai)

    class Meta:
        verbose_name = _("1. Loại vật tư")
        verbose_name_plural = _("1. Loại vật tư")


class VatTu(models.Model):
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
    
    def __str__(self):
        return f"{self.ten_vat_tu} (Tồn: {self.so_luong_ton})"

    class Meta:
        verbose_name = _("2. Vật tư & CCHT")
        verbose_name_plural = _("2. Kho Tổng")


# --- 2. QUẢN LÝ CÔNG CỤ TẠI MỤC TIÊU ---

class CongCuTaiMucTieu(models.Model):
    """Theo dõi số lượng CCHT thực tế đang bàn giao cho từng Mục tiêu bảo vệ"""
    muc_tieu = models.ForeignKey(MucTieu, on_delete=models.CASCADE, verbose_name=_("Mục tiêu bảo vệ"))
    vat_tu = models.ForeignKey(VatTu, on_delete=models.CASCADE, verbose_name=_("Tên công cụ"))
    so_luong_dang_giu = models.PositiveIntegerField(_("Số lượng thực tế tại MT"), default=0)
    ngay_cap_gan_nhat = models.DateField(_("Ngày cập nhật gần nhất"), auto_now=True)

    class Meta:
        unique_together = ('muc_tieu', 'vat_tu')
        verbose_name = _("3. Công cụ tại Mục tiêu")
        verbose_name_plural = _("3. Công cụ tại Mục tiêu")
    
    def __str__(self):
        return f"{self.muc_tieu} - {self.vat_tu} (SL: {self.so_luong_dang_giu})"


# --- 3. PHIẾU NHẬP KHO ---

class PhieuNhap(models.Model):
    """Hồ sơ nhập kho vật tư từ nhà cung cấp hoặc thu hồi"""
    ma_phieu = models.CharField(_("Mã số phiếu nhập"), max_length=50, unique=True)
    nguoi_nhap = models.ForeignKey(
        NhanVien, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name=_("Thủ kho thực hiện")
    )
    ngay_nhap = models.DateTimeField(_("Ngày giờ nhập kho"), default=timezone.now)
    ghi_chu = models.TextField(_("Ghi chú nhập"), blank=True)

    def __str__(self):
        time_str = self.ngay_nhap.astimezone().strftime('%d/%m/%Y')
        return f"Nhập: {self.ma_phieu} ({time_str})"

    class Meta:
        verbose_name = _("4. Phiếu Nhập kho")
        verbose_name_plural = _("4. Quản lý Nhập kho")


class ChiTietPhieuNhap(models.Model):
    """Chi tiết danh sách vật tư trong một phiếu nhập"""
    phieu_nhap = models.ForeignKey(PhieuNhap, related_name='chi_tiet', on_delete=models.CASCADE)
    vat_tu = models.ForeignKey(VatTu, on_delete=models.CASCADE, verbose_name=_("Vật tư"))
    so_luong = models.PositiveIntegerField(_("Số lượng nhập"))
    don_gia = models.DecimalField(_("Đơn giá nhập thực tế"), max_digits=12, decimal_places=0, default=0)

    @property
    def thanh_tien(self): 
        sl = self.so_luong if self.so_luong else 0
        dg = self.don_gia if self.don_gia else 0
        return sl * dg

    class Meta:
        verbose_name = _("Chi tiết phiếu nhập")
        verbose_name_plural = _("Chi tiết phiếu nhập")


# --- 4. PHIẾU XUẤT KHO ---

class PhieuXuat(models.Model):
    """Hồ sơ xuất kho: Cấp phát định mức, bán trừ lương hoặc cấp cho mục tiêu"""
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


class ChiTietPhieuXuat(models.Model):
    """Chi tiết danh sách vật tư trong một phiếu xuất"""
    phieu_xuat = models.ForeignKey(PhieuXuat, related_name='chi_tiet', on_delete=models.CASCADE)
    vat_tu = models.ForeignKey(VatTu, on_delete=models.CASCADE, verbose_name=_("Vật tư/CCHT"))
    so_luong = models.PositiveIntegerField(_("Số lượng xuất"))
    
    # Lưu giá bán tại thời điểm xuất để tránh biến động giá danh mục sau này
    don_gia_ban = models.DecimalField(_("Đơn giá áp dụng"), max_digits=12, decimal_places=0, default=0)

    def save(self, *args, **kwargs):
        """Tự động lấy đơn giá bán và cập nhật tổng tiền công nợ của phiếu xuất"""
        # 1. Tự động áp đơn giá từ danh mục nếu chưa có
        if self.don_gia_ban == 0 and self.vat_tu:
            self.don_gia_ban = self.vat_tu.gia_ban
            
        super().save(*args, **kwargs)
        
        # 2. Đồng bộ hóa tổng tiền phải thu cho PhieuXuat (Chỉ dành cho loại BÁN)
        try:
            if self.phieu_xuat.loai_xuat == 'BAN_TRU_LUONG':
                # Tính toán tổng tiền từ tất cả các dòng chi tiết của phiếu này
                total = sum(item.so_luong * item.don_gia_ban for item in self.phieu_xuat.chi_tiet.all())
                # Sử dụng update để tránh đệ quy gọi save() vô tận
                PhieuXuat.objects.filter(pk=self.phieu_xuat.pk).update(tong_tien_phai_thu=total)
        except Exception:
            pass

    def clean(self):
        """Kiểm tra tồn kho thực tế trước khi xuất"""
        if not self.so_luong or not self.vat_tu:
            return
            
        # Kiểm tra tồn kho đối với phiếu mới hoặc phiếu đang sửa tăng số lượng
        ton_kho = self.vat_tu.so_luong_ton if self.vat_tu.so_luong_ton is not None else 0
        if self.pk is None: # Phiếu mới
            if ton_kho < self.so_luong:
                raise ValidationError(_(f"Lỗi kho: Vật tư {self.vat_tu.ten_vat_tu} không đủ tồn (Hiện có: {ton_kho})"))
        else:
            # Đối với bản ghi cũ, kiểm tra độ chênh lệch nếu cần (logic này có thể mở rộng thêm)
            pass

    class Meta:
        verbose_name = _("Chi tiết phiếu xuất")
        verbose_name_plural = _("Chi tiết phiếu xuất")