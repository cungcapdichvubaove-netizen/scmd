# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro
=======
Security Command (SCMD) System
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: accounting/models.py
Author: Mr. Anh
Created Date: 2025-11-30
<<<<<<< HEAD
Updated Date: 2026-06-03
Version: v3.5.0
=======
Updated Date: 2026-05-15
Version: v2.0.0-pro
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
Description: Model quản lý Kế toán - Tiền lương (Core Payroll Models).
             HARDENING PHASE: Chuẩn hóa SSOT (CRM -> Payroll) theo DOCUMENTATION.md.
             - Cập nhật định danh các khoản thu nhập/khấu trừ.
             - Đảm bảo tính nhất quán với logic quyết toán tự động.
"""

import uuid
import logging
<<<<<<< HEAD
from typing import TYPE_CHECKING, Optional
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from django.db import models, transaction
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError, ImproperlyConfigured
<<<<<<< HEAD
from core.managers import ChiTietLuongManager, TenantAwareManager, TenantScopedModel
from core.workflow_transition_policy import WorkflowTransitionPolicy
=======
from core.managers import TenantAwareManager
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from django.conf import settings
from users.models import NhanVien
from decimal import Decimal, ROUND_HALF_UP

<<<<<<< HEAD
if TYPE_CHECKING:
    from core.managers import TenantAwareManager

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
logger = logging.getLogger(__name__)

# ==============================================================================
# 0. MULTI-TENANCY CORE
# ==============================================================================

<<<<<<< HEAD
class CauHinhLuong(TenantScopedModel):
=======
class CauHinhLuong(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Hồ sơ thiết lập các tham số lương và phụ cấp cố định cho từng nhân viên an ninh"""
    nhan_vien = models.OneToOneField(
        NhanVien, 
        on_delete=models.CASCADE, 
        related_name="cau_hinh_luong", 
        verbose_name="Nhân viên thụ hưởng"
    )
<<<<<<< HEAD
    # --- Dữ liệu đóng bảo hiểm ---
=======

    tenant_id = models.UUIDField("Tenant ID", db_index=True, default=uuid.uuid4, editable=False)
    
    # --- Dữ liệu kế thừa (Legacy) ---
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    luong_co_ban_ngay = models.DecimalField(
        "Mức lương đóng BHXH", 
        max_digits=12, 
        decimal_places=0, 
<<<<<<< HEAD
        default=Decimal('0'),
=======
        default=0,
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        help_text="Mức lương căn bản dùng để tính bảo hiểm và các chế độ nhà nước."
    )
    
    # --- Hệ thống phụ cấp an ninh mới ---
    phu_cap_trach_nhiem = models.DecimalField(
        "Phụ cấp trách nhiệm", 
        max_digits=12, 
        decimal_places=0, 
<<<<<<< HEAD
        default=Decimal('0'),
=======
        default=0,
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        help_text="Phụ cấp dành cho các vị trí chỉ huy, đội trưởng, hoặc mục tiêu trọng yếu."
    )
    phu_cap_xang_xe = models.DecimalField(
        "Phụ cấp đi lại/Xăng xe", 
        max_digits=12, 
        decimal_places=0, 
<<<<<<< HEAD
        default=Decimal('0'),
=======
        default=0,
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        help_text="Hỗ trợ chi phí di chuyển giữa các mục tiêu bảo vệ."
    )
    phu_cap_an_uong = models.DecimalField(
        "Phụ cấp ăn ca", 
        max_digits=12, 
        decimal_places=0, 
<<<<<<< HEAD
        default=Decimal('0'),
=======
        default=0,
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        help_text="Hỗ trợ tiền ăn trực ca theo quy định của SCMD."
    )

    objects = TenantAwareManager()

    class Meta: 
        verbose_name = "Hồ sơ Lương cá nhân"
        verbose_name_plural = "Hồ sơ Lương cá nhân"

<<<<<<< HEAD

=======
    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID}")
        super().clean()

    def save(self, *args, **kwargs):
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID required.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        super().save(*args, **kwargs)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

    def __str__(self): 
        return f"Cấu hình lương: {self.nhan_vien.ho_ten} ({self.nhan_vien.ma_nhan_vien})"


<<<<<<< HEAD
class BangLuongThang(TenantScopedModel):
=======
class BangLuongThang(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Quản lý các kỳ lương tổng hợp hàng tháng của toàn hệ thống SCMD"""
    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", "Dự thảo"
        CALCULATED = "CALCULATED", "Đã tính"
        REVIEWED = "REVIEWED", "Đã đối soát"
        LOCKED = "LOCKED", "Đã khóa kỳ"
        PAID = "PAID", "Đã thanh toán"

    LOCKED_STATES = {TrangThai.LOCKED, TrangThai.PAID}
<<<<<<< HEAD
=======
    
    tenant_id = models.UUIDField("Tenant ID", db_index=True, default=uuid.uuid4, editable=False)

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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
<<<<<<< HEAD
        default=Decimal('0'),
=======
        default=0,
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        help_text="Tổng số tiền thực lĩnh của toàn bộ nhân viên trong kỳ."
    )
    tong_gio_cong = models.FloatField(
        "Tổng giờ công hệ thống", 
        default=0,
        help_text="Tổng hợp toàn bộ giờ làm việc của nhân sự trong tháng."
    )

    nguoi_duyet = models.ForeignKey(
        "users.NhanVien", 
<<<<<<< HEAD
        on_delete=models.SET_NULL,
=======
        on_delete=models.SET_NULL, 
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        null=True, 
        blank=True, 
        verbose_name="Người phê duyệt (KTT/GĐ)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo bảng kê")

<<<<<<< HEAD
    objects: "TenantAwareManager" = TenantAwareManager()
=======
    objects = TenantAwareManager()
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

    class Meta: 
        verbose_name = "Kỳ lương hệ thống"
        verbose_name_plural = "1. Quản lý Kỳ lương"
        unique_together = ('thang', 'nam', 'tenant_id')
        ordering = ['-nam', '-thang']
<<<<<<< HEAD
        indexes = [
            models.Index(fields=['tenant_id', 'nam', 'thang']),
            models.Index(fields=['tenant_id', 'trang_thai', 'nam', 'thang']),
        ]

    if TYPE_CHECKING:
        chi_tiet: models.Manager["ChiTietLuong"]


=======

    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID}")
        super().clean()

    def save(self, *args, **kwargs):
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID required.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        super().save(*args, **kwargs)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

    def update_totals(self):
        """Tính toán lại tổng chi và tổng công dựa trên các phiếu lương chi tiết"""
        # SSOT: Sử dụng aggregate trực tiếp từ DB
        stats = self.chi_tiet.all().aggregate(
            total_pay=models.Sum('thuc_lanh', default=0),
            total_hours=models.Sum('tong_gio_lam', default=0)
        )
        
        # Tối ưu: Sử dụng .update() để tránh gọi lại save() của BangLuongThang
        # Điều này ngăn chặn các signal hoặc logic save() khác bị lặp lại vô tận
<<<<<<< HEAD
        # SCMD Pro: Enforce organization scope SSOT (WHITEPAPER.md 9)
        BangLuongThang.objects.for_tenant(self.tenant_id).filter(pk=self.pk).update(
=======
        BangLuongThang.objects.filter(pk=self.pk).update(
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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


<<<<<<< HEAD

class ChiTietLuong(TenantScopedModel):
=======
class ChiTietLuongManager(TenantAwareManager):
    """Manager tối ưu hóa truy vấn để triệt tiêu lỗi N+1 Query"""
    def get_queryset(self):
        return super().get_queryset().select_related(
            'nhan_vien', 
            'bang_luong'
        )


class ChiTietLuong(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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
<<<<<<< HEAD
# --- Nhóm dữ liệu Chấm công ---
=======
    
    tenant_id = models.UUIDField("Tenant ID", db_index=True, default=uuid.uuid4, editable=False)

    # --- Nhóm dữ liệu Chấm công ---
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    tong_gio_lam = models.FloatField("Tổng giờ làm việc", default=0)
    so_ngay_nghi = models.IntegerField("Số ngày nghỉ phép/không lương", default=0)
    
    # --- Nhóm dữ liệu Thu nhập (Earnings) - SSOT Section 7 ---
<<<<<<< HEAD
    luong_chinh = models.DecimalField("Lương khoán (từ CRM)", max_digits=12, decimal_places=0, default=Decimal('0'))
    thuong_chuyen_can = models.DecimalField("Thưởng chuyên cần", max_digits=12, decimal_places=0, default=Decimal('0'))
    phu_cap_khac = models.DecimalField("Tổng phụ cấp khác", max_digits=12, decimal_places=0, default=Decimal('0'))
    
    # --- Nhóm dữ liệu Khấu trừ (Deductions) - SSOT Section 7 ---
    ung_luong = models.DecimalField("Khoản tạm ứng", max_digits=12, decimal_places=0, default=Decimal('0'))
    phat_vi_pham = models.DecimalField("Phạt kỷ luật/Vi phạm", max_digits=12, decimal_places=0, default=Decimal('0'))
    tien_dong_phuc = models.DecimalField("Khấu trừ vật tư/Đồng phục", max_digits=12, decimal_places=0, default=Decimal('0'))
    tien_den_bu = models.DecimalField("Khấu trừ đền bù sự cố", max_digits=12, decimal_places=0, default=Decimal('0'))
    bao_hiem = models.DecimalField("Khấu trừ BHXH/BHYT", max_digits=12, decimal_places=0, default=Decimal('0'))
    phi_cong_doan = models.DecimalField("Kinh phí Công đoàn", max_digits=12, decimal_places=0, default=Decimal('0'))
    
    # --- Kết quả quyết toán ---
    thuc_lanh = models.DecimalField("Thực lĩnh cuối kỳ", max_digits=12, decimal_places=0, default=Decimal('0'))
    ghi_chu = models.TextField("Ghi chú nghiệp vụ", blank=True, help_text="Giải trình các khoản thưởng/phạt đặc thù.")
    nguon_du_lieu_snapshot = models.JSONField(
        "Snapshot dữ liệu nguồn",
        default=dict,
        blank=True,
        help_text="Dữ liệu đối soát nguồn tại thời điểm tính lương.",
    )
    reconciliation_note = models.TextField(
        "Ghi chú đối soát",
        blank=True,
        help_text="Giải thích thay đổi thực lãnh hoặc lần tính lại.",
    )
=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

    class Meta: 
        verbose_name = "Phiếu lương cá nhân"
        verbose_name_plural = "Phiếu lương cá nhân"
        unique_together = ('bang_luong', 'nhan_vien', 'tenant_id')

<<<<<<< HEAD
    if TYPE_CHECKING:
        # Type hints for dynamic and auto-generated attributes
        bang_luong_id: int
        _audit_note: str
        _audit_user: Optional[NhanVien]

    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID}")
        if self.bang_luong_id and self.bang_luong.is_locked:
            raise ValidationError(
                "Kỳ lương đã LOCKED/PAID. Phiếu lương chi tiết chỉ được đọc, không được sửa trực tiếp."
            )
=======
    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID}")
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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
<<<<<<< HEAD
        """Compatibility alias cho các báo cáo và template."""
=======
        """Compatibility alias for legacy templates and reports."""
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        return self.phu_cap_khac

    @property
    def tong_khau_tru(self):
        """Tổng các khoản tiền bị trừ vào lương"""
        return (self.ung_luong + self.phat_vi_pham + 
                self.tien_dong_phuc + self.tien_den_bu + 
                self.bao_hiem + self.phi_cong_doan)

    def save(self, *args, **kwargs):
<<<<<<< HEAD
        """Save đơn thuần: enforce organization scope và validate payroll lock."""
        self.tenant_id = self.organization_id()
        self.full_clean()
=======
        """Save đơn thuần: Enforce multi-tenancy và cập nhật bảng tổng."""
        # 0. Thực thi Multi-tenancy
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID required.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

        # Infrastructure Layer only. 
        # Side effects (update_totals) must be called explicitly by the Orchestrator/UseCase.
        with transaction.atomic():
            super().save(*args, **kwargs)
<<<<<<< HEAD
            # Capability 11: Bổ sung audit trail trực tiếp tại model cho dữ liệu nhạy cảm
            if hasattr(self, '_audit_note'):
                 from main.models import AuditLog
                 AuditLog.objects.create(
                     user=getattr(self, '_audit_user', None),
                     action=AuditLog.Action.UPDATE,
                     module="accounting",
                     model_name="ChiTietLuong",
                     object_id=self.pk,
                     note=self._audit_note
                 )
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    
    def __str__(self): 
        return f"Phiếu lương: {self.nhan_vien.ma_nhan_vien} | Thực nhận: {self.thuc_lanh:,.0f} VNĐ"


<<<<<<< HEAD
class PayrollAdjustment(TenantScopedModel):
    """Append-only retroactive payroll adjustment after a payroll period is locked/paid.

    SCMD Pro rule: do not edit ``ChiTietLuong`` directly after a payroll period
    reaches LOCKED/PAID. Any correction must be recorded here with a signed
    amount, reason, creator, timestamp and audit log from the use case/admin.
    """

    bang_luong = models.ForeignKey(
        BangLuongThang,
        on_delete=models.PROTECT,
        related_name="adjustments",
        verbose_name="Kỳ lương đã khóa/đã thanh toán",
    )
    chi_tiet_luong = models.ForeignKey(
        ChiTietLuong,
        on_delete=models.PROTECT,
        related_name="adjustments",
        null=True,
        blank=True,
        verbose_name="Phiếu lương liên quan",
    )
    nhan_vien = models.ForeignKey(
        NhanVien,
        on_delete=models.PROTECT,
        related_name="payroll_adjustments",
        verbose_name="Nhân sự điều chỉnh",
    )
    so_tien_dieu_chinh = models.DecimalField(
        "Số tiền điều chỉnh (+/-)",
        max_digits=12,
        decimal_places=0,
        help_text="Số dương là truy lĩnh/bổ sung; số âm là thu hồi/khấu trừ hồi tố.",
    )
    ly_do = models.TextField("Lý do điều chỉnh")
    metadata = models.JSONField("Dữ liệu đối soát", default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payroll_adjustments_created",
        verbose_name="Người tạo điều chỉnh",
    )
    created_at = models.DateTimeField("Thời điểm tạo", auto_now_add=True, db_index=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Điều chỉnh lương hồi tố"
        verbose_name_plural = "3. Điều chỉnh lương hồi tố"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["tenant_id", "bang_luong", "created_at"], name="acc_adj_t_pay_created_idx"),
            models.Index(fields=["tenant_id", "nhan_vien", "created_at"], name="acc_adj_t_staff_created_idx"),
        ]

    @property
    def is_increase(self):
        return self.so_tien_dieu_chinh > Decimal("0")

    def clean(self):
        super().clean()
        if self.so_tien_dieu_chinh == Decimal("0"):
            raise ValidationError("Số tiền điều chỉnh phải khác 0.")
        if self.bang_luong_id and not self.bang_luong.is_locked:
            raise ValidationError(
                "Chỉ tạo PayrollAdjustment cho kỳ lương đã LOCKED/PAID. "
                "Kỳ chưa khóa phải sửa qua quy trình tính/đối soát bình thường."
            )
        if self.chi_tiet_luong_id:
            if self.chi_tiet_luong.bang_luong_id != self.bang_luong_id:
                raise ValidationError("Phiếu lương liên quan phải thuộc cùng kỳ lương.")
            if self.chi_tiet_luong.nhan_vien_id != self.nhan_vien_id:
                raise ValidationError("Phiếu lương liên quan phải thuộc cùng nhân sự điều chỉnh.")

    def save(self, *args, **kwargs):
        self.tenant_id = self.organization_id()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        sign = "+" if self.so_tien_dieu_chinh > 0 else ""
        return f"Điều chỉnh {self.nhan_vien} {sign}{self.so_tien_dieu_chinh:,.0f} VNĐ - {self.bang_luong}"


class TamUngLuong(TenantScopedModel):
    """SSOT hồ sơ tạm ứng lương có phê duyệt và bằng chứng riêng.

    Không tự động ghi vào ``ChiTietLuong.ung_luong`` trong patch này để tránh phá
    payroll hiện tại. Việc đồng bộ vào kỳ lương phải qua use case đối soát riêng.
    """

    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", "Nháp"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Chờ duyệt"
        APPROVED = "APPROVED", "Đã duyệt"
        PAID = "PAID", "Đã chi"
        DEDUCTED = "DEDUCTED", "Đã khấu trừ"
        REJECTED = "REJECTED", "Từ chối"
        CANCELLED = "CANCELLED", "Đã hủy"

    ALLOWED_STATUS_TRANSITIONS = {
        TrangThai.DRAFT: {TrangThai.PENDING_APPROVAL, TrangThai.CANCELLED},
        TrangThai.PENDING_APPROVAL: {TrangThai.APPROVED, TrangThai.REJECTED, TrangThai.CANCELLED},
        TrangThai.APPROVED: {TrangThai.PAID, TrangThai.CANCELLED},
        TrangThai.PAID: {TrangThai.DEDUCTED},
        TrangThai.DEDUCTED: set(),
        TrangThai.REJECTED: set(),
        TrangThai.CANCELLED: set(),
    }

    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="cac_tam_ung_luong", verbose_name="Nhân viên")
    so_phieu = models.CharField("Số phiếu tạm ứng", max_length=64, db_index=True)
    ngay_de_nghi = models.DateField("Ngày đề nghị", default=timezone.localdate, db_index=True)
    bang_luong_du_kien = models.ForeignKey(
        BangLuongThang,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_tam_ung_luong",
        verbose_name="Kỳ lương dự kiến khấu trừ",
    )
    so_tien = models.DecimalField("Số tiền tạm ứng", max_digits=14, decimal_places=0, validators=[MinValueValidator(0)])
    trang_thai = models.CharField("Trạng thái", max_length=32, choices=TrangThai.choices, default=TrangThai.DRAFT, db_index=True)
    ly_do = models.TextField("Lý do", blank=True)
    file_minh_chung = models.FileField("File/bằng chứng", upload_to="tam_ung_luong/%Y/%m/", null=True, blank=True)
    nguoi_duyet = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_tam_ung_luong_da_duyet", verbose_name="Người duyệt")
    ngay_duyet = models.DateTimeField("Thời điểm duyệt", null=True, blank=True)
    ghi_chu = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField("Tạo lúc", auto_now_add=True)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Tạm ứng lương"
        verbose_name_plural = "4. Tạm ứng lương"
        ordering = ["-ngay_de_nghi", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "ngay_de_nghi"], name="acc_adv_tenant_stat_date_idx"),
            models.Index(fields=["tenant_id", "nhan_vien", "trang_thai"], name="acc_adv_tenant_staff_idx"),
        ]
        constraints = [models.UniqueConstraint(fields=["tenant_id", "so_phieu"], name="uq_adv_tenant_voucher")]

    def __str__(self):
        return f"{self.so_phieu} - {self.nhan_vien}"

    def clean(self):
        super().clean()
        if self.so_tien is not None and self.so_tien <= 0:
            raise ValidationError("Số tiền tạm ứng phải lớn hơn 0.")

    def record_status_transition(self, *, actor=None, old_status=None, new_status=None, note=""):
        new_status = new_status if new_status is not None else self.trang_thai
        if old_status == new_status:
            return None
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="accounting",
                model_name="TamUngLuong",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "Payroll advance status transition",
                changes={"status_transition": {"old": old_status, "new": new_status}, "so_phieu": self.so_phieu, "nhan_vien_id": self.nhan_vien_id, "so_tien": str(self.so_tien)},
            )
        except Exception as exc:
            logger.error("Failed to audit TamUngLuong status transition: %s", exc)
            return None

    def transition_status(self, new_status, *, actor=None, note=""):
        old_status = self.trang_thai
        WorkflowTransitionPolicy.validate_transition(type(self).__name__, old_status, new_status, self.ALLOWED_STATUS_TRANSITIONS)
        self.trang_thai = new_status
        update_fields = ["trang_thai", "updated_at"]
        if new_status == self.TrangThai.APPROVED and actor and not self.nguoi_duyet_id:
            self.nguoi_duyet = actor
            self.ngay_duyet = timezone.now()
            update_fields.extend(["nguoi_duyet", "ngay_duyet"])
        self.save(update_fields=update_fields)
        return self.record_status_transition(actor=actor, old_status=old_status, new_status=new_status, note=note)


class KhoanKhauTruNhanVien(TenantScopedModel):
    """SSOT khoản khấu trừ nhân viên có hồ sơ nguồn riêng."""

    class LoaiKhauTru(models.TextChoices):
        TAM_UNG = "TAM_UNG", "Khấu trừ tạm ứng"
        DONG_PHUC = "DONG_PHUC", "Đồng phục/công cụ"
        DEN_BU = "DEN_BU", "Đền bù"
        VI_PHAM = "VI_PHAM", "Vi phạm/kỷ luật"
        BAO_HIEM = "BAO_HIEM", "Bảo hiểm"
        KHAC = "KHAC", "Khác"

    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", "Nháp"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Chờ duyệt"
        APPROVED = "APPROVED", "Đã duyệt"
        APPLIED = "APPLIED", "Đã áp dụng kỳ lương"
        REJECTED = "REJECTED", "Từ chối"
        CANCELLED = "CANCELLED", "Đã hủy"

    ALLOWED_STATUS_TRANSITIONS = {
        TrangThai.DRAFT: {TrangThai.PENDING_APPROVAL, TrangThai.CANCELLED},
        TrangThai.PENDING_APPROVAL: {TrangThai.APPROVED, TrangThai.REJECTED, TrangThai.CANCELLED},
        TrangThai.APPROVED: {TrangThai.APPLIED, TrangThai.CANCELLED},
        TrangThai.APPLIED: set(),
        TrangThai.REJECTED: set(),
        TrangThai.CANCELLED: set(),
    }

    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="cac_khoan_khau_tru", verbose_name="Nhân viên")
    so_chung_tu = models.CharField("Số chứng từ", max_length=64, db_index=True)
    loai_khau_tru = models.CharField("Loại khấu trừ", max_length=32, choices=LoaiKhauTru.choices, default=LoaiKhauTru.KHAC)
    tam_ung = models.ForeignKey(TamUngLuong, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_khoan_khau_tru", verbose_name="Phiếu tạm ứng liên quan")
    bang_luong_du_kien = models.ForeignKey(BangLuongThang, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_khoan_khau_tru", verbose_name="Kỳ lương dự kiến")
    ngay_ap_dung = models.DateField("Ngày áp dụng", default=timezone.localdate, db_index=True)
    so_tien = models.DecimalField("Số tiền khấu trừ", max_digits=14, decimal_places=0, validators=[MinValueValidator(0)])
    trang_thai = models.CharField("Trạng thái", max_length=32, choices=TrangThai.choices, default=TrangThai.DRAFT, db_index=True)
    ly_do = models.TextField("Lý do", blank=True)
    file_minh_chung = models.FileField("File/bằng chứng", upload_to="khoan_khau_tru/%Y/%m/", null=True, blank=True)
    nguoi_duyet = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_khoan_khau_tru_da_duyet", verbose_name="Người duyệt")
    ngay_duyet = models.DateTimeField("Thời điểm duyệt", null=True, blank=True)
    ghi_chu = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField("Tạo lúc", auto_now_add=True)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Khoản khấu trừ nhân viên"
        verbose_name_plural = "5. Khoản khấu trừ nhân viên"
        ordering = ["-ngay_ap_dung", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "ngay_ap_dung"], name="acc_ded_tenant_stat_date_idx"),
            models.Index(fields=["tenant_id", "nhan_vien", "loai_khau_tru"], name="acc_ded_tenant_staff_type_idx"),
        ]
        constraints = [models.UniqueConstraint(fields=["tenant_id", "so_chung_tu"], name="uq_ded_tenant_doc_no")]

    def __str__(self):
        return f"{self.so_chung_tu} - {self.nhan_vien}"

    def clean(self):
        super().clean()
        if self.so_tien is not None and self.so_tien <= 0:
            raise ValidationError("Số tiền khấu trừ phải lớn hơn 0.")
        if self.tam_ung_id and self.tam_ung.nhan_vien_id != self.nhan_vien_id:
            raise ValidationError("Phiếu tạm ứng liên quan phải thuộc cùng nhân viên.")

    def record_status_transition(self, *, actor=None, old_status=None, new_status=None, note=""):
        new_status = new_status if new_status is not None else self.trang_thai
        if old_status == new_status:
            return None
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="accounting",
                model_name="KhoanKhauTruNhanVien",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "Employee deduction status transition",
                changes={"status_transition": {"old": old_status, "new": new_status}, "so_chung_tu": self.so_chung_tu, "nhan_vien_id": self.nhan_vien_id, "so_tien": str(self.so_tien)},
            )
        except Exception as exc:
            logger.error("Failed to audit KhoanKhauTruNhanVien status transition: %s", exc)
            return None

    def transition_status(self, new_status, *, actor=None, note=""):
        old_status = self.trang_thai
        WorkflowTransitionPolicy.validate_transition(type(self).__name__, old_status, new_status, self.ALLOWED_STATUS_TRANSITIONS)
        self.trang_thai = new_status
        update_fields = ["trang_thai", "updated_at"]
        if new_status == self.TrangThai.APPROVED and actor and not self.nguoi_duyet_id:
            self.nguoi_duyet = actor
            self.ngay_duyet = timezone.now()
            update_fields.extend(["nguoi_duyet", "ngay_duyet"])
        self.save(update_fields=update_fields)
        return self.record_status_transition(actor=actor, old_status=old_status, new_status=new_status, note=note)


class PhanHoiLuong(TenantScopedModel):
=======
class PhanHoiLuong(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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
<<<<<<< HEAD
=======

    tenant_id = models.UUIDField("Tenant ID", db_index=True)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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

<<<<<<< HEAD
    objects = TenantAwareManager()

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    class Meta:
        verbose_name = "Phản hồi lương"
        verbose_name_plural = "2. Phản hồi lương (Dispute)"
        ordering = ['-created_at']

    def __str__(self):
        return f"Phản hồi: {self.nhan_vien.ho_ten} - Kỳ {self.chi_tiet_luong.bang_luong}"
