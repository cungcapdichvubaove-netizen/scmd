# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: accounting/models.py
Author: Mr. Anh
Created Date: 2025-11-30
Updated Date: 2026-05-15
Version: v2.0.0-pro
Description: Model quản lý Kế toán - Tiền lương (Core Payroll Models).
             HARDENING PHASE: Chuẩn hóa SSOT (CRM -> Payroll) theo DOCUMENTATION.md.
             - Cập nhật định danh các khoản thu nhập/khấu trừ.
             - Đảm bảo tính nhất quán với logic quyết toán tự động.
"""

import uuid
import logging
from django.db import models, transaction
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError, ImproperlyConfigured
from core.managers import TenantAwareManager
from django.conf import settings
from users.models import NhanVien
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

# ==============================================================================
# 0. MULTI-TENANCY CORE
# ==============================================================================

class CauHinhLuong(models.Model):
    """Hồ sơ thiết lập các tham số lương và phụ cấp cố định cho từng nhân viên an ninh"""
    nhan_vien = models.OneToOneField(
        NhanVien, 
        on_delete=models.CASCADE, 
        related_name="cau_hinh_luong", 
        verbose_name="Nhân viên thụ hưởng"
    )

    tenant_id = models.UUIDField("Tenant ID", db_index=True, default=uuid.uuid4, editable=False)
    
    # --- Dữ liệu kế thừa (Legacy) ---
    luong_co_ban_ngay = models.DecimalField(
        "Mức lương đóng BHXH", 
        max_digits=12, 
        decimal_places=0, 
        default=0,
        help_text="Mức lương căn bản dùng để tính bảo hiểm và các chế độ nhà nước."
    )
    
    # --- Hệ thống phụ cấp an ninh mới ---
    phu_cap_trach_nhiem = models.DecimalField(
        "Phụ cấp trách nhiệm", 
        max_digits=12, 
        decimal_places=0, 
        default=0,
        help_text="Phụ cấp dành cho các vị trí chỉ huy, đội trưởng, hoặc mục tiêu trọng yếu."
    )
    phu_cap_xang_xe = models.DecimalField(
        "Phụ cấp đi lại/Xăng xe", 
        max_digits=12, 
        decimal_places=0, 
        default=0,
        help_text="Hỗ trợ chi phí di chuyển giữa các mục tiêu bảo vệ."
    )
    phu_cap_an_uong = models.DecimalField(
        "Phụ cấp ăn ca", 
        max_digits=12, 
        decimal_places=0, 
        default=0,
        help_text="Hỗ trợ tiền ăn trực ca theo quy định của SCMD."
    )

    objects = TenantAwareManager()

    class Meta: 
        verbose_name = "Hồ sơ Lương cá nhân"
        verbose_name_plural = "Hồ sơ Lương cá nhân"

    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID}")
        super().clean()

    def save(self, *args, **kwargs):
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID required.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        super().save(*args, **kwargs)

    def __str__(self): 
        return f"Cấu hình lương: {self.nhan_vien.ho_ten} ({self.nhan_vien.ma_nhan_vien})"


class BangLuongThang(models.Model):
    """Quản lý các kỳ lương tổng hợp hàng tháng của toàn hệ thống SCMD"""
    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", "Dự thảo"
        CALCULATED = "CALCULATED", "Đã tính"
        REVIEWED = "REVIEWED", "Đã đối soát"
        LOCKED = "LOCKED", "Đã khóa kỳ"
        PAID = "PAID", "Đã thanh toán"

    LOCKED_STATES = {TrangThai.LOCKED, TrangThai.PAID}
    
    tenant_id = models.UUIDField("Tenant ID", db_index=True, default=uuid.uuid4, editable=False)

    ten_bang_luong = models.CharField(
        "Tên bảng lương", 
        max_length=200, 
        default="Bảng lương tháng ...",
        help_text="Ví dụ: Bảng lương mục tiêu Vincity - Tháng 03/2026"
    )
    thang = models.IntegerField(
        "Tháng lương", 
        default=timezone.now().month,
        validators=[MinValueValidator(1)]
    )
    nam = models.IntegerField(
        "Năm quyết toán", 
        default=timezone.now().year
    )
    ngay_chot_cong = models.DateField(
        "Ngày chốt dữ liệu công", 
        default=timezone.now,
        help_text="Ngày cuối cùng hệ thống ghi nhận giờ làm việc cho kỳ lương này."
    )
    trang_thai = models.CharField(
        "Trạng thái phê duyệt", 
        max_length=20, 
        choices=TrangThai.choices,
        default=TrangThai.DRAFT
    )
    
    # --- Số liệu thống kê tổng hợp ---
    tong_chi_tra = models.DecimalField(
        "Tổng ngân sách chi trả", 
        max_digits=15, 
        decimal_places=0, 
        default=0,
        help_text="Tổng số tiền thực lĩnh của toàn bộ nhân viên trong kỳ."
    )
    tong_gio_cong = models.FloatField(
        "Tổng giờ công hệ thống", 
        default=0,
        help_text="Tổng hợp toàn bộ giờ làm việc của nhân sự trong tháng."
    )

    nguoi_duyet = models.ForeignKey(
        "users.NhanVien", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Người phê duyệt (KTT/GĐ)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo bảng kê")

    objects = TenantAwareManager()

    class Meta: 
        verbose_name = "Kỳ lương hệ thống"
        verbose_name_plural = "1. Quản lý Kỳ lương"
        unique_together = ('thang', 'nam', 'tenant_id')
        ordering = ['-nam', '-thang']

    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID}")
        super().clean()

    def save(self, *args, **kwargs):
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID required.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        super().save(*args, **kwargs)

    def update_totals(self):
        """Tính toán lại tổng chi và tổng công dựa trên các phiếu lương chi tiết"""
        # SSOT: Sử dụng aggregate trực tiếp từ DB
        stats = self.chi_tiet.all().aggregate(
            total_pay=models.Sum('thuc_lanh', default=0),
            total_hours=models.Sum('tong_gio_lam', default=0)
        )
        
        # Tối ưu: Sử dụng .update() để tránh gọi lại save() của BangLuongThang
        # Điều này ngăn chặn các signal hoặc logic save() khác bị lặp lại vô tận
        BangLuongThang.objects.filter(pk=self.pk).update(
            tong_chi_tra=stats['total_pay'],
            tong_gio_cong=stats['total_hours']
        )

    @property
    def is_locked(self):
        return self.trang_thai in self.LOCKED_STATES

    def can_recalculate(self):
        return not self.is_locked

    def __str__(self): 
        return f"Kỳ lương SCMD - Tháng {self.thang}/{self.nam}"


class ChiTietLuongManager(TenantAwareManager):
    """Manager tối ưu hóa truy vấn để triệt tiêu lỗi N+1 Query"""
    def get_queryset(self):
        return super().get_queryset().select_related(
            'nhan_vien', 
            'bang_luong'
        )


class ChiTietLuong(models.Model):
    """Phiếu lương chi tiết cho từng cá nhân (Payslip). Lưu trữ dữ liệu tĩnh để đối soát lịch sử."""
    bang_luong = models.ForeignKey(
        BangLuongThang, 
        on_delete=models.CASCADE, 
        related_name="chi_tiet",
        verbose_name="Thuộc kỳ lương"
    )
    nhan_vien = models.ForeignKey(
        NhanVien, 
        on_delete=models.CASCADE,
        verbose_name="Nhân sự"
    )
    
    tenant_id = models.UUIDField("Tenant ID", db_index=True, default=uuid.uuid4, editable=False)

    # --- Nhóm dữ liệu Chấm công ---
    tong_gio_lam = models.FloatField("Tổng giờ làm việc", default=0)
    so_ngay_nghi = models.IntegerField("Số ngày nghỉ phép/không lương", default=0)
    
    # --- Nhóm dữ liệu Thu nhập (Earnings) - SSOT Section 7 ---
    luong_chinh = models.DecimalField("Lương khoán (từ CRM)", max_digits=12, decimal_places=0, default=0)
    thuong_chuyen_can = models.DecimalField("Thưởng chuyên cần", max_digits=12, decimal_places=0, default=0)
    phu_cap_khac = models.DecimalField("Tổng phụ cấp khác", max_digits=12, decimal_places=0, default=0)
    
    # --- Nhóm dữ liệu Khấu trừ (Deductions) - SSOT Section 7 ---
    ung_luong = models.DecimalField("Khoản tạm ứng", max_digits=12, decimal_places=0, default=0)
    phat_vi_pham = models.DecimalField("Phạt kỷ luật/Vi phạm", max_digits=12, decimal_places=0, default=0)
    tien_dong_phuc = models.DecimalField("Khấu trừ vật tư/Đồng phục", max_digits=12, decimal_places=0, default=0)
    tien_den_bu = models.DecimalField("Khấu trừ đền bù sự cố", max_digits=12, decimal_places=0, default=0)
    bao_hiem = models.DecimalField("Khấu trừ BHXH/BHYT", max_digits=12, decimal_places=0, default=0)
    phi_cong_doan = models.DecimalField("Kinh phí Công đoàn", max_digits=12, decimal_places=0, default=0)
    
    # --- Kết quả quyết toán ---
    thuc_lanh = models.DecimalField("Thực lĩnh cuối kỳ", max_digits=12, decimal_places=0, default=0)
    ghi_chu = models.TextField("Ghi chú nghiệp vụ", blank=True, help_text="Giải trình các khoản thưởng/phạt đặc thù.")

    class Meta: 
        verbose_name = "Phiếu lương cá nhân"
        verbose_name_plural = "Phiếu lương cá nhân"
        unique_together = ('bang_luong', 'nhan_vien', 'tenant_id')

    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID}")
        super().clean()

    objects = ChiTietLuongManager()

    @staticmethod
    def to_decimal_safe(val):
        """Chuyển đổi giá trị sang Decimal an toàn và làm tròn (SSOT Section 7)."""
        if val is None or val == "":
            return Decimal('0')
        try:
            # Clean currency formatting (commas, spaces) before conversion
            clean_val = str(val).replace(',', '').replace(' ', '')
            # Làm tròn về 0 chữ số thập phân (VNĐ) theo chuẩn ROUND_HALF_UP
            return Decimal(clean_val).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        except Exception:
            return Decimal('0')

    @property
    def tong_thu_nhap(self):
        """Tổng các khoản tiền được nhận trước khi trừ phí"""
        return self.luong_chinh + self.thuong_chuyen_can + self.phu_cap_khac

    @property
    def tong_phu_cap(self):
        """Compatibility alias for legacy templates and reports."""
        return self.phu_cap_khac

    @property
    def tong_khau_tru(self):
        """Tổng các khoản tiền bị trừ vào lương"""
        return (self.ung_luong + self.phat_vi_pham + 
                self.tien_dong_phuc + self.tien_den_bu + 
                self.bao_hiem + self.phi_cong_doan)

    def save(self, *args, **kwargs):
        """Save đơn thuần: Enforce multi-tenancy và cập nhật bảng tổng."""
        # 0. Thực thi Multi-tenancy
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID required.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID

        # Infrastructure Layer only. 
        # Side effects (update_totals) must be called explicitly by the Orchestrator/UseCase.
        with transaction.atomic():
            super().save(*args, **kwargs)
    
    def __str__(self): 
        return f"Phiếu lương: {self.nhan_vien.ma_nhan_vien} | Thực nhận: {self.thuc_lanh:,.0f} VNĐ"


class PhanHoiLuong(models.Model):
    """
    Lưu trữ các phản hồi/khiếu nại về lương từ nhân viên.
    Tuân thủ Audit Trail (Section 12.3 - DOCUMENTATION.md).
    """
    TRANG_THAI = [
        ('MOI', 'Mới tiếp nhận'),
        ('DANG_XU_LY', 'Đang xử lý'),
        ('DA_GIAI_QUYET', 'Đã giải quyết'),
        ('TU_CHOI', 'Từ chối'),
    ]

    tenant_id = models.UUIDField("Tenant ID", db_index=True)
    chi_tiet_luong = models.ForeignKey(
        ChiTietLuong, 
        on_delete=models.CASCADE, 
        related_name="danh_sach_phan_hoi",
        verbose_name="Phiếu lương khiếu nại"
    )
    nhan_vien = models.ForeignKey(
        NhanVien, 
        on_delete=models.CASCADE,
        verbose_name="Nhân viên phản hồi"
    )
    noi_dung = models.TextField("Nội dung phản hồi/thắc mắc")
    phan_hoi_admin = models.TextField("Phản hồi từ kế toán", blank=True)
    trang_thai = models.CharField(
        "Trạng thái xử lý", 
        max_length=20, 
        choices=TRANG_THAI, 
        default='MOI'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Phản hồi lương"
        verbose_name_plural = "2. Phản hồi lương (Dispute)"
        ordering = ['-created_at']

    def __str__(self):
        return f"Phản hồi: {self.nhan_vien.ho_ten} - Kỳ {self.chi_tiet_luong.bang_luong}"
