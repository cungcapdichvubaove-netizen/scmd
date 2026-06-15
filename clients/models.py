# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro - Phần mềm chỉ huy và quản trị doanh nghiệp dịch vụ bảo vệ
------------------------------
Copyright (c) 2026 SCMD. All Rights Reserved.
=======
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

File: clients/models.py
Author: Mr. Anh
Created Date: 2025-11-30
<<<<<<< HEAD
Description: Phân hệ quản lý Khách hàng, Hợp đồng & Mục tiêu bảo vệ.
=======
Description: Model quản lý Khách hàng, Hợp đồng & Mục tiêu.
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
             Đã nâng cấp: Cấu hình Lương ĐỘNG theo số ngày thực tế của tháng.

NOTICE: This file is part of a proprietary system. 
Unauthorized copying of this file, via any medium is strictly prohibited.
"""

import uuid
<<<<<<< HEAD
import logging
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
=======
import calendar  # Thư viện để tính ngày trong tháng
import logging
from datetime import timedelta
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.conf import settings
from django.core.exceptions import ValidationError, ImproperlyConfigured
<<<<<<< HEAD
from core.managers import TenantAwareManager, MucTieuManager, TenantScopedModel
from clients.application.contract_transition_policy import ContractTransitionPolicy
from core.workflow_transition_policy import WorkflowTransitionPolicy

if TYPE_CHECKING:
    from core.managers import TenantAwareManager, MucTieuManager

logger = logging.getLogger(__name__)

class KhachHangTiemNang(TenantScopedModel):
=======
from core.managers import TenantAwareManager

logger = logging.getLogger(__name__)

class KhachHangTiemNang(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Quản lý thông tin khách hàng tiềm năng và các đầu mối (Leads) của SCMD"""
    NGUON_DEN = [
        ('WEBSITE', 'Website/Google'),
        ('GIOI_THIEU', 'Người quen giới thiệu'),
        ('MXH', 'Mạng xã hội (FB/Zalo)'),
        ('KHAC', 'Khác'),
    ]
    TRANG_THAI = [
        ('MOI', 'Mới tiếp nhận'),
        ('TIEM_NANG', 'Đang chăm sóc'),
        ('BAO_GIA', 'Đã gửi báo giá'),
        ('CHOT_HOP_DONG', 'Đã ký hợp đồng'),
        ('HUY', 'Khách hủy/Thất bại'),
    ]

<<<<<<< HEAD
=======
    tenant_id = models.UUIDField("Tenant ID", db_index=True, default=uuid.uuid4, editable=False)
    
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    ten_cong_ty = models.CharField(
        "Tên công ty/Khách hàng", 
        max_length=255, 
        db_index=True,
        help_text="Tên pháp nhân trên giấy phép kinh doanh hoặc tên cá nhân khách hàng."
    )
    nguoi_lien_he = models.CharField(
        "Người liên hệ", 
        max_length=100, 
        blank=True,
        help_text="Đầu mối liên hệ trực tiếp tại đơn vị khách hàng."
    )
    sdt = models.CharField(
        "Số điện thoại", 
        max_length=20,
        help_text="Số điện thoại di động hoặc hotline liên lạc."
    )
    email = models.EmailField(
        "Email", 
        blank=True, 
        null=True
    )
    dia_chi = models.CharField(
        "Địa chỉ trụ sở", 
        max_length=255, 
        blank=True
    )
    
    nguon = models.CharField(
        "Nguồn khách hàng", 
        max_length=50, 
        choices=NGUON_DEN, 
        default='KHAC'
    )
    trang_thai = models.CharField(
        "Trạng thái chăm sóc", 
        max_length=20, 
        choices=TRANG_THAI, 
        default='MOI'
    )
    ghi_chu = models.TextField(
        "Ghi chú chăm sóc", 
        blank=True,
        help_text="Lịch sử trao đổi hoặc các lưu ý đặc biệt về khách hàng."
    )
    
    ngay_tao = models.DateTimeField(
        "Ngày khởi tạo hệ thống",
        default=timezone.now
    )

<<<<<<< HEAD
    objects: "TenantAwareManager" = TenantAwareManager()
=======
    objects = TenantAwareManager()

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
        return f"{self.ten_cong_ty} ({self.get_trang_thai_display()})"

    class Meta:
        verbose_name = "Khách hàng & Leads"
        verbose_name_plural = "1. Danh sách Khách hàng"
        ordering = ['-ngay_tao']


<<<<<<< HEAD
class CoHoiKinhDoanh(TenantScopedModel):
=======
class CoHoiKinhDoanh(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Quản lý Pipeline cơ hội kinh doanh từ khách hàng tiềm năng"""
    class TrangThai(models.TextChoices):
        MOI = "MOI", "Mới tiếp nhận"
        LIEN_HE = "LIENHE", "Đang liên hệ"
        GUI_BAO_GIA = "BAOGIA", "Đã báo giá"
        THUONG_LUONG = "THUONGLUONG", "Đang thương thảo"
        THANH_CONG = "THANHCONG", "Chốt hợp đồng (Thắng)"
        THAT_BAI = "THATBAI", "Thất bại (Thua)"

<<<<<<< HEAD
=======
    tenant_id = models.UUIDField("Tenant ID", db_index=True, default=uuid.uuid4, editable=False)

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    khach_hang_tiem_nang = models.ForeignKey(
        KhachHangTiemNang, 
        on_delete=models.CASCADE, 
        verbose_name="Khách hàng liên quan",
        related_name="cac_co_hoi_kinh_doanh"
    )
    ten_co_hoi = models.CharField(
        "Tên cơ hội/Dự án", 
        max_length=255,
        help_text="Ví dụ: Gói bảo vệ mục tiêu Chung cư Vincity Q9"
    ) 
    gia_tri_uoc_tinh = models.DecimalField(
        "Giá trị dự kiến (VNĐ)", 
        max_digits=15, 
        decimal_places=0, 
        default=0
    )
    trang_thai = models.CharField(
        "Giai đoạn bán hàng", 
        max_length=20, 
        choices=TrangThai.choices, 
        default=TrangThai.MOI
    )
    nguoi_phu_trach = models.ForeignKey(
        "users.NhanVien", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="cac_co_hoi_kinh_doanh",
        verbose_name="Nhân viên Sales phụ trách"
    )
    ngay_tao = models.DateTimeField(
        "Ngày tạo cơ hội",
        auto_now_add=True
    )
<<<<<<< HEAD
    region = models.ForeignKey(
        "users.Region",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_muc_tieu",
        verbose_name="Vùng quản lý",
        help_text="SSOT vùng vận hành dùng cho REGION scope của Quản lý vùng.",
    )

    objects: "TenantAwareManager" = TenantAwareManager()
=======

    objects = TenantAwareManager()

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

    class Meta:
        verbose_name = "Cơ hội Kinh doanh"
        verbose_name_plural = "2. Pipeline (Cơ hội)"

    def __str__(self):
        return f"{self.ten_co_hoi} - {self.get_trang_thai_display()}"


<<<<<<< HEAD
class HopDong(TenantScopedModel):
=======
class HopDong(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Quản lý hợp đồng dịch vụ bảo vệ chính thức của SCMD"""
    TRANG_THAI_HD = [
        ('HIEU_LUC', 'Đang hiệu lực'),
        ('SAP_HET_HAN', 'Sắp hết hạn (Dưới 30 ngày)'),
        ('DA_THANH_LY', 'Đã thanh lý/Hết hạn'),
    ]

<<<<<<< HEAD
=======
    tenant_id = models.UUIDField("Tenant ID", db_index=True, default=uuid.uuid4, editable=False)
    
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    co_hoi = models.OneToOneField(
        CoHoiKinhDoanh, 
        on_delete=models.CASCADE, 
        verbose_name="Chuyển đổi từ cơ hội", 
        related_name="hop_dong",
        null=True, 
        blank=True
    )
    khach_hang_cu = models.ForeignKey(
        KhachHangTiemNang, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='hop_dong_cu',
        verbose_name="Chủ sở hữu hợp đồng"
    )

    so_hop_dong = models.CharField(
        "Số hợp đồng", 
        max_length=100, 
        unique=True, 
        db_index=True,
        help_text="Mã định danh duy nhất của hợp đồng trên hệ thống."
    )
    ngay_ky = models.DateField(
        "Ngày ký kết", 
        default=timezone.now
    )
    ngay_hieu_luc = models.DateField(
        "Ngày bắt đầu hiệu lực", 
        default=timezone.now
    )
    ngay_het_han = models.DateField(
        "Ngày kết thúc hợp đồng", 
        default=timezone.now
    )
    
    gia_tri = models.DecimalField(
        "Giá trị Hợp đồng (Tháng)", 
        max_digits=15, 
        decimal_places=0, 
        default=0,
        help_text="Số tiền thu về từ khách hàng hàng tháng."
    )
    file_hop_dong = models.FileField(
        "Bản Scan hợp đồng (PDF/Image)", 
        upload_to="hop_dong/", 
        null=True, 
        blank=True
    )
    
    trang_thai = models.CharField(
        "Tình trạng hợp đồng", 
        max_length=20, 
        choices=TRANG_THAI_HD, 
        default='HIEU_LUC', 
        db_index=True
    )

<<<<<<< HEAD
    objects: "TenantAwareManager" = TenantAwareManager()

    if TYPE_CHECKING:
        # Type hints cho quan hệ ngược (Rule 14)
        cac_muc_tieu: models.Manager["MucTieu"]

    def save(self, *args, **kwargs):
        """Persist the contract with a state-machine guard and audit trail.

        Status calculation remains in the application/background layer, but
        manual/admin updates still need a local invariant: terminal contracts
        must not be reopened by direct model saves.
        """
        old_status = None
        if self.pk:
            old_status = (
                self.__class__.objects.filter(pk=self.pk)
                .values_list("trang_thai", flat=True)
                .first()
            )
            ContractTransitionPolicy.validate_transition(old_status, self.trang_thai)

        super().save(*args, **kwargs)

        if old_status is not None and old_status != self.trang_thai:
            from main.models import AuditLog

            AuditLog.objects.create(
                user=getattr(self, "_audit_user", None),
                tenant_id=getattr(settings, "SCMD_ORGANIZATION_ID", None),
                action=AuditLog.Action.UPDATE,
                module="clients",
                model_name="HopDong",
                object_id=str(self.pk),
                note="Chuyển trạng thái hợp đồng",
                changes={
                    "trang_thai": {
                        "before": old_status,
                        "after": self.trang_thai,
                    }
                },
            )

=======
    objects = TenantAwareManager()

    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID}")
        super().clean()

    def save(self, *args, **kwargs):
        """
        Infrastructure Layer only: Persist model data.
        Business logic for status calculation moved to Application Layer (Background Jobs).
        """
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID required.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        super().save(*args, **kwargs)

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    class Meta:
        verbose_name = "Hợp đồng Dịch vụ"
        verbose_name_plural = "3. Quản lý Hợp đồng"

    def __str__(self):
        return f"HĐ: {self.so_hop_dong}"


class MucTieu(models.Model):
    """Điểm trực và cấu hình nghiệp vụ tại mục tiêu bảo vệ cụ thể"""
<<<<<<< HEAD
    # SSOT: Sử dụng TenantAwareManager tập trung để tránh duplicate logic quản lý tổ chức.
    # Scope của MucTieu được truy xuất gián tiếp qua HopDong.
    objects: "MucTieuManager" = MucTieuManager()

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    hop_dong = models.ForeignKey(
        HopDong,
        on_delete=models.CASCADE,
        related_name="cac_muc_tieu",
        verbose_name="Thuộc Hợp đồng kinh tế",
    )
    ten_muc_tieu = models.CharField(
        "Tên mục tiêu bảo vệ", 
        max_length=255, 
        db_index=True,
        help_text="Ví dụ: Cổng chính, Kho hàng A, v.v."
    )
    dia_chi = models.TextField(
        "Địa chỉ triển khai mục tiêu",
        help_text="Địa chỉ chi tiết nơi nhân viên an ninh thực hiện nhiệm vụ."
    )
    
    # --- Cấu hình Giám sát GPS ---
    vi_do = models.FloatField(
        "Tọa độ Vĩ độ (Lat)", 
        null=True, 
        blank=True,
        help_text="Sử dụng Google Maps tọa độ để định vị mục tiêu."
    )
    kinh_do = models.FloatField(
        "Tọa độ Kinh độ (Lng)", 
        null=True, 
        blank=True,
        help_text="Sử dụng Google Maps tọa độ để định vị mục tiêu."
    )
    ban_kinh_cho_phep = models.IntegerField(
        "Bán kính kiểm soát (mét)", 
        default=100,
        help_text="Phạm vi cho phép nhân viên Check-in/Check-out hợp lệ."
    )

    # --- CẤU HÌNH LƯƠNG ĐỘNG (AUTO PAYROLL LOGIC) ---
    luong_khoan_bao_ve = models.DecimalField(
        "Lương khoán định mức (Tháng)", 
        max_digits=12, 
        decimal_places=0, 
        default=6000000, 
        help_text="Mức lương chuẩn cho 01 tháng làm đủ 100% công theo lịch trực."
    )
    
    # THAY ĐỔI: Chuyển từ Giờ/Tháng sang Giờ/Ngày để tính tự động
<<<<<<< HEAD
    so_gio_mot_ngay = models.DecimalField(
        "Định mức giờ trực/ngày", 
        max_digits=5,
        decimal_places=2,
        default=Decimal("12.00"),
        validators=[MinValueValidator(Decimal("0.25"))],
        help_text="Số giờ ca trực tiêu chuẩn. Hệ thống sẽ tự nhân với số ngày trong tháng."
=======
    so_gio_mot_ngay = models.FloatField(
        "Định mức giờ trực/ngày", 
        default=12.0, 
        help_text="Số giờ ca trực tiêu chuẩn. Hệ thống sẽ tự nhân với số ngày trong tháng (28/30/31)."
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    )
    
    # Hệ thống tính điểm Chuyên cần (Bậc thang khấu trừ)
    tien_chuyen_can = models.DecimalField(
        "Tiền thưởng chuyên cần tối đa", 
        max_digits=12, 
        decimal_places=0, 
        default=1000000,
        help_text="Thưởng tối đa khi nhân viên đi làm đủ công và không vi phạm kỷ luật."
    )
    tru_nghi_1_ngay = models.DecimalField(
        "Khấu trừ chuyên cần (nghỉ 1 ngày)", 
        max_digits=12, 
        decimal_places=0, 
        default=400000
    )
    tru_nghi_2_ngay = models.DecimalField(
        "Khấu trừ chuyên cần (nghỉ 2 ngày)", 
        max_digits=12, 
        decimal_places=0, 
        default=300000
    )
    tru_nghi_3_ngay = models.DecimalField(
        "Khấu trừ chuyên cần (nghỉ từ 3 ngày trở lên)", 
        max_digits=12, 
        decimal_places=0, 
        default=1000000
    )
    
    nguoi_lien_he = models.CharField(
        "Đầu mối liên hệ tại mục tiêu", 
        max_length=255, 
        blank=True
    )
    sdt_lien_he = models.CharField(
        "SĐT liên hệ mục tiêu", 
        max_length=20, 
        blank=True
    )
    so_luong_nhan_vien = models.IntegerField(
        "Định biên quân số (Người)", 
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Số lượng nhân viên tối thiểu cần bố trí cho mục tiêu này."
    )
    
    quan_ly_muc_tieu = models.ForeignKey(
        "users.NhanVien", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Chỉ huy trưởng mục tiêu",
        related_name="cac_muc_tieu_quan_ly"
    )

    quan_ly_vung = models.ForeignKey(
        "users.NhanVien",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_muc_tieu_phu_trach_vung",
        verbose_name="Quản lý vùng phụ trách (Regional Manager)"
    )

<<<<<<< HEAD
    if TYPE_CHECKING:
        # Type hints cho quan hệ ngược và ID tự sinh
        lich_su_don_gia: models.Manager["MucTieuDonGiaHistory"]

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    class Meta:
        verbose_name = "Mục tiêu Bảo vệ"
        verbose_name_plural = "4. Danh sách Mục tiêu"

    def __str__(self):
        return self.ten_muc_tieu
<<<<<<< HEAD

    def _get_effective_payroll_rate_record(self, ngay_truc):
        from accounting.domain.payroll_rate import resolve_effective_rate_record

        prefetched_history = getattr(self, "_prefetched_objects_cache", {}).get(
            "lich_su_don_gia"
        )
        if prefetched_history is not None:
            return resolve_effective_rate_record(prefetched_history, ngay_truc)

        history_qs = self.lich_su_don_gia.order_by("ngay_hieu_luc", "id")
        return resolve_effective_rate_record(history_qs, ngay_truc)

    def get_payroll_rate_context(self, ngay_truc):
        """
        Return effective payroll rate context for a specific shift date.

        When rate history exists, payroll must resolve through the effective-dated
        records to preserve reconciliation for retroactive adjustments.
        """
        from accounting.domain.payroll_rate import calculate_hourly_rate

        rate_record = self._get_effective_payroll_rate_record(ngay_truc)
        if rate_record is None:
            monthly_salary = self.luong_khoan_bao_ve
            standard_hours_per_day = self.so_gio_mot_ngay
            effective_date = self.hop_dong.ngay_hieu_luc
            source = "CURRENT_TARGET_CONFIG"
            rate_record_id = None
        else:
            monthly_salary = rate_record.luong_khoan_bao_ve
            standard_hours_per_day = rate_record.so_gio_mot_ngay
            effective_date = rate_record.ngay_hieu_luc
            source = "RATE_HISTORY"
            rate_record_id = rate_record.id

        hourly_rate = calculate_hourly_rate(
            monthly_salary=monthly_salary,
            standard_hours_per_day=standard_hours_per_day,
            month=ngay_truc.month,
            year=ngay_truc.year,
        )
        return {
            "hourly_rate": hourly_rate,
            "monthly_salary": Decimal(str(monthly_salary)),
            "standard_hours_per_day": Decimal(str(standard_hours_per_day)),
            "effective_date": effective_date,
            "source": source,
            "rate_record_id": rate_record_id,
        }
    
    def get_don_gia_gio_thuc_te(self, thang, nam):
        """
        Compatibility wrapper.

        Logic tính đơn giá giờ chính thức nằm ở accounting.domain.payroll_rate
        để đảm bảo Decimal precision và dễ unit test.
        """
        from accounting.domain.payroll_rate import calculate_hourly_rate

        return calculate_hourly_rate(
            monthly_salary=self.luong_khoan_bao_ve,
            standard_hours_per_day=self.so_gio_mot_ngay,
            month=thang,
            year=nam,
        )


class PhuLucHopDongDichVu(TenantScopedModel):
    """Phụ lục hợp đồng dịch vụ bảo vệ có vòng đời riêng."""

    class LoaiPhuLuc(models.TextChoices):
        DIEU_CHINH_GIA = "DIEU_CHINH_GIA", "Điều chỉnh giá"
        BO_SUNG_MUC_TIEU = "BO_SUNG_MUC_TIEU", "Bổ sung mục tiêu"
        GIA_HAN = "GIA_HAN", "Gia hạn"
        DIEU_CHINH_DIEU_KHOAN = "DIEU_CHINH_DIEU_KHOAN", "Điều chỉnh điều khoản"
        KHAC = "KHAC", "Khác"

    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", "Nháp"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Chờ duyệt"
        ACTIVE = "ACTIVE", "Có hiệu lực"
        EXPIRED = "EXPIRED", "Hết hiệu lực"
        TERMINATED = "TERMINATED", "Chấm dứt"

    ALLOWED_STATUS_TRANSITIONS = {
        TrangThai.DRAFT: {TrangThai.PENDING_APPROVAL, TrangThai.TERMINATED},
        TrangThai.PENDING_APPROVAL: {TrangThai.ACTIVE, TrangThai.TERMINATED},
        TrangThai.ACTIVE: {TrangThai.EXPIRED, TrangThai.TERMINATED},
        TrangThai.EXPIRED: {TrangThai.TERMINATED},
        TrangThai.TERMINATED: set(),
    }

    hop_dong = models.ForeignKey(HopDong, on_delete=models.CASCADE, related_name="cac_phu_luc_dich_vu", verbose_name="Hợp đồng dịch vụ")
    so_phu_luc = models.CharField("Số phụ lục", max_length=64, db_index=True)
    loai_phu_luc = models.CharField("Loại phụ lục", max_length=32, choices=LoaiPhuLuc.choices, default=LoaiPhuLuc.KHAC)
    ngay_ky = models.DateField("Ngày ký", null=True, blank=True)
    ngay_hieu_luc = models.DateField("Ngày hiệu lực", db_index=True)
    ngay_het_han = models.DateField("Ngày hết hạn", null=True, blank=True, db_index=True)
    gia_tri_dieu_chinh = models.DecimalField("Giá trị điều chỉnh", max_digits=15, decimal_places=0, default=Decimal("0"))
    trang_thai = models.CharField("Trạng thái", max_length=32, choices=TrangThai.choices, default=TrangThai.DRAFT, db_index=True)
    file_phu_luc = models.FileField("File phụ lục", upload_to="phu_luc_hop_dong_dich_vu/%Y/%m/", null=True, blank=True)
    nguoi_duyet = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_phu_luc_dich_vu_da_duyet", verbose_name="Người duyệt")
    ngay_duyet = models.DateTimeField("Thời điểm duyệt", null=True, blank=True)
    ghi_chu = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField("Tạo lúc", auto_now_add=True)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Phụ lục hợp đồng dịch vụ"
        verbose_name_plural = "4. Phụ lục hợp đồng dịch vụ"
        ordering = ["-ngay_hieu_luc", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "ngay_het_han"], name="cli_pldv_tenant_stat_exp_idx"),
            models.Index(fields=["tenant_id", "hop_dong", "trang_thai"], name="cli_pldv_tenant_hd_stat_idx"),
        ]
        constraints = [models.UniqueConstraint(fields=["tenant_id", "hop_dong", "so_phu_luc"], name="uq_pldv_tenant_hd_no")]

    def __str__(self):
        return f"{self.so_phu_luc} - {self.hop_dong.so_hop_dong}"

    def clean(self):
        super().clean()
        if self.ngay_het_han and self.ngay_hieu_luc and self.ngay_het_han < self.ngay_hieu_luc:
            raise ValidationError({"ngay_het_han": "Ngày hết hạn phụ lục không được trước ngày hiệu lực."})

    def record_status_transition(self, *, actor=None, old_status=None, new_status=None, note=""):
        new_status = new_status if new_status is not None else self.trang_thai
        if old_status == new_status:
            return None
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="clients",
                model_name="PhuLucHopDongDichVu",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "Service contract appendix status transition",
                changes={"status_transition": {"old": old_status, "new": new_status}, "so_phu_luc": self.so_phu_luc, "hop_dong_id": self.hop_dong_id},
            )
        except Exception as exc:
            logger.error("Failed to audit PhuLucHopDongDichVu status transition: %s", exc)
            return None

    def transition_status(self, new_status, *, actor=None, note=""):
        old_status = self.trang_thai
        WorkflowTransitionPolicy.validate_transition(type(self).__name__, old_status, new_status, self.ALLOWED_STATUS_TRANSITIONS)
        self.trang_thai = new_status
        update_fields = ["trang_thai", "updated_at"]
        if new_status == self.TrangThai.ACTIVE and actor and not self.nguoi_duyet_id:
            self.nguoi_duyet = actor
            self.ngay_duyet = timezone.now()
            update_fields.extend(["nguoi_duyet", "ngay_duyet"])
        self.save(update_fields=update_fields)
        return self.record_status_transition(actor=actor, old_status=old_status, new_status=new_status, note=note)


class BienBanNghiemThu(TenantScopedModel):
    """Biên bản nghiệm thu dịch vụ theo hợp đồng/mục tiêu."""

    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", "Nháp"
        PENDING_SIGNATURE = "PENDING_SIGNATURE", "Chờ ký"
        SIGNED = "SIGNED", "Đã ký"
        REJECTED = "REJECTED", "Từ chối"
        CANCELLED = "CANCELLED", "Đã hủy"

    ALLOWED_STATUS_TRANSITIONS = {
        TrangThai.DRAFT: {TrangThai.PENDING_SIGNATURE, TrangThai.CANCELLED},
        TrangThai.PENDING_SIGNATURE: {TrangThai.SIGNED, TrangThai.REJECTED, TrangThai.CANCELLED},
        TrangThai.SIGNED: set(),
        TrangThai.REJECTED: set(),
        TrangThai.CANCELLED: set(),
    }

    hop_dong = models.ForeignKey(HopDong, on_delete=models.CASCADE, related_name="cac_bien_ban_nghiem_thu", verbose_name="Hợp đồng dịch vụ")
    muc_tieu = models.ForeignKey(MucTieu, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_bien_ban_nghiem_thu", verbose_name="Mục tiêu")
    so_bien_ban = models.CharField("Số biên bản", max_length=64, db_index=True)
    tu_ngay = models.DateField("Nghiệm thu từ ngày", db_index=True)
    den_ngay = models.DateField("Nghiệm thu đến ngày", db_index=True)
    ngay_lap = models.DateField("Ngày lập", default=timezone.localdate)
    tong_gia_tri_nghiem_thu = models.DecimalField("Tổng giá trị nghiệm thu", max_digits=15, decimal_places=0, default=Decimal("0"), validators=[MinValueValidator(0)])
    trang_thai = models.CharField("Trạng thái", max_length=32, choices=TrangThai.choices, default=TrangThai.DRAFT, db_index=True)
    file_bien_ban = models.FileField("File biên bản", upload_to="bien_ban_nghiem_thu/%Y/%m/", null=True, blank=True)
    nguoi_duyet = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_bien_ban_nghiem_thu_da_duyet", verbose_name="Người duyệt/ký")
    ngay_duyet = models.DateTimeField("Thời điểm duyệt/ký", null=True, blank=True)
    ghi_chu = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField("Tạo lúc", auto_now_add=True)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Biên bản nghiệm thu"
        verbose_name_plural = "5. Biên bản nghiệm thu"
        ordering = ["-ngay_lap", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "ngay_lap"], name="cli_bbnt_tenant_stat_date_idx"),
            models.Index(fields=["tenant_id", "hop_dong", "tu_ngay"], name="cli_bbnt_tenant_hd_from_idx"),
        ]
        constraints = [models.UniqueConstraint(fields=["tenant_id", "so_bien_ban"], name="uq_bbnt_tenant_no")]

    def __str__(self):
        return f"{self.so_bien_ban} - {self.hop_dong.so_hop_dong}"

    def clean(self):
        super().clean()
        if self.den_ngay and self.tu_ngay and self.den_ngay < self.tu_ngay:
            raise ValidationError({"den_ngay": "Ngày kết thúc nghiệm thu không được trước ngày bắt đầu."})
        if self.muc_tieu_id and self.hop_dong_id and self.muc_tieu.hop_dong_id != self.hop_dong_id:
            raise ValidationError({"muc_tieu": "Mục tiêu nghiệm thu phải thuộc cùng hợp đồng."})

    def record_status_transition(self, *, actor=None, old_status=None, new_status=None, note=""):
        new_status = new_status if new_status is not None else self.trang_thai
        if old_status == new_status:
            return None
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="clients",
                model_name="BienBanNghiemThu",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "Acceptance report status transition",
                changes={"status_transition": {"old": old_status, "new": new_status}, "so_bien_ban": self.so_bien_ban, "hop_dong_id": self.hop_dong_id},
            )
        except Exception as exc:
            logger.error("Failed to audit BienBanNghiemThu status transition: %s", exc)
            return None

    def transition_status(self, new_status, *, actor=None, note=""):
        old_status = self.trang_thai
        WorkflowTransitionPolicy.validate_transition(type(self).__name__, old_status, new_status, self.ALLOWED_STATUS_TRANSITIONS)
        self.trang_thai = new_status
        update_fields = ["trang_thai", "updated_at"]
        if new_status == self.TrangThai.SIGNED and actor and not self.nguoi_duyet_id:
            self.nguoi_duyet = actor
            self.ngay_duyet = timezone.now()
            update_fields.extend(["nguoi_duyet", "ngay_duyet"])
        self.save(update_fields=update_fields)
        return self.record_status_transition(actor=actor, old_status=old_status, new_status=new_status, note=note)


class HoaDon(TenantScopedModel):
    """Hóa đơn/đề nghị thanh toán gắn hợp đồng và nghiệm thu."""

    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", "Nháp"
        ISSUED = "ISSUED", "Đã phát hành"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Thanh toán một phần"
        PAID = "PAID", "Đã thanh toán"
        OVERDUE = "OVERDUE", "Quá hạn"
        CANCELLED = "CANCELLED", "Đã hủy"

    ALLOWED_STATUS_TRANSITIONS = {
        TrangThai.DRAFT: {TrangThai.ISSUED, TrangThai.CANCELLED},
        TrangThai.ISSUED: {TrangThai.PARTIALLY_PAID, TrangThai.PAID, TrangThai.OVERDUE, TrangThai.CANCELLED},
        TrangThai.PARTIALLY_PAID: {TrangThai.PAID, TrangThai.OVERDUE, TrangThai.CANCELLED},
        TrangThai.OVERDUE: {TrangThai.ISSUED, TrangThai.PARTIALLY_PAID, TrangThai.PAID, TrangThai.CANCELLED},
        TrangThai.PAID: set(),
        TrangThai.CANCELLED: set(),
    }

    hop_dong = models.ForeignKey(HopDong, on_delete=models.CASCADE, related_name="cac_hoa_don", verbose_name="Hợp đồng dịch vụ")
    bien_ban = models.ForeignKey(BienBanNghiemThu, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_hoa_don", verbose_name="Biên bản nghiệm thu")
    so_hoa_don = models.CharField("Số hóa đơn", max_length=64, db_index=True)
    ngay_phat_hanh = models.DateField("Ngày phát hành", default=timezone.localdate, db_index=True)
    ngay_den_han = models.DateField("Ngày đến hạn", null=True, blank=True, db_index=True)
    tong_tien = models.DecimalField("Tổng tiền", max_digits=15, decimal_places=0, validators=[MinValueValidator(0)])
    trang_thai = models.CharField("Trạng thái", max_length=32, choices=TrangThai.choices, default=TrangThai.DRAFT, db_index=True)
    file_hoa_don = models.FileField("File hóa đơn", upload_to="hoa_don/%Y/%m/", null=True, blank=True)
    ghi_chu = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField("Tạo lúc", auto_now_add=True)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Hóa đơn"
        verbose_name_plural = "6. Hóa đơn"
        ordering = ["-ngay_phat_hanh", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "ngay_den_han"], name="cli_inv_tenant_stat_due_idx"),
            models.Index(fields=["tenant_id", "hop_dong", "ngay_phat_hanh"], name="cli_inv_tenant_hd_date_idx"),
        ]
        constraints = [models.UniqueConstraint(fields=["tenant_id", "so_hoa_don"], name="uq_invoice_tenant_no")]

    def __str__(self):
        return f"{self.so_hoa_don} - {self.hop_dong.so_hop_dong}"

    def clean(self):
        super().clean()
        if self.ngay_den_han and self.ngay_phat_hanh and self.ngay_den_han < self.ngay_phat_hanh:
            raise ValidationError({"ngay_den_han": "Ngày đến hạn không được trước ngày phát hành."})
        if self.bien_ban_id and self.hop_dong_id and self.bien_ban.hop_dong_id != self.hop_dong_id:
            raise ValidationError({"bien_ban": "Biên bản nghiệm thu phải thuộc cùng hợp đồng."})

    def is_overdue_on(self, day=None):
        day = day or timezone.localdate()
        return bool(self.ngay_den_han and self.ngay_den_han < day and self.trang_thai not in (self.TrangThai.PAID, self.TrangThai.CANCELLED))

    @property
    def so_tien_da_thu_tu_phan_bo(self):
        total = self.cac_phan_bo_thanh_toan.aggregate(total=models.Sum("so_tien"))["total"] if self.pk else None
        return total or Decimal("0")

    @property
    def so_tien_con_lai(self):
        return max(self.tong_tien - self.so_tien_da_thu_tu_phan_bo, Decimal("0"))

    def record_status_transition(self, *, actor=None, old_status=None, new_status=None, note=""):
        new_status = new_status if new_status is not None else self.trang_thai
        if old_status == new_status:
            return None
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="clients",
                model_name="HoaDon",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "Invoice status transition",
                changes={"status_transition": {"old": old_status, "new": new_status}, "so_hoa_don": self.so_hoa_don, "hop_dong_id": self.hop_dong_id},
            )
        except Exception as exc:
            logger.error("Failed to audit HoaDon status transition: %s", exc)
            return None

    def transition_status(self, new_status, *, actor=None, note=""):
        old_status = self.trang_thai
        WorkflowTransitionPolicy.validate_transition(type(self).__name__, old_status, new_status, self.ALLOWED_STATUS_TRANSITIONS)
        if new_status == self.TrangThai.PAID and self.so_tien_da_thu_tu_phan_bo < self.tong_tien:
            raise ValidationError("Không được chuyển hóa đơn sang PAID khi chưa có phân bổ thanh toán đủ tiền.")
        self.trang_thai = new_status
        self.save(update_fields=["trang_thai", "updated_at"])
        return self.record_status_transition(actor=actor, old_status=old_status, new_status=new_status, note=note)


class CongNo(TenantScopedModel):
    """Hồ sơ công nợ phải thu theo hóa đơn."""

    class TrangThai(models.TextChoices):
        OPEN = "OPEN", "Chưa thu"
        PARTIAL = "PARTIAL", "Thu một phần"
        PAID = "PAID", "Đã thu đủ"
        OVERDUE = "OVERDUE", "Quá hạn"
        WRITTEN_OFF = "WRITTEN_OFF", "Xóa/điều chỉnh nợ"

    ALLOWED_STATUS_TRANSITIONS = {
        TrangThai.OPEN: {TrangThai.PARTIAL, TrangThai.PAID, TrangThai.OVERDUE, TrangThai.WRITTEN_OFF},
        TrangThai.PARTIAL: {TrangThai.PAID, TrangThai.OVERDUE, TrangThai.WRITTEN_OFF},
        TrangThai.OVERDUE: {TrangThai.OPEN, TrangThai.PARTIAL, TrangThai.PAID, TrangThai.WRITTEN_OFF},
        TrangThai.PAID: set(),
        TrangThai.WRITTEN_OFF: set(),
    }

    hoa_don = models.ForeignKey(HoaDon, on_delete=models.CASCADE, related_name="cac_cong_no", verbose_name="Hóa đơn")
    so_tham_chieu = models.CharField("Số tham chiếu công nợ", max_length=64, db_index=True)
    ngay_den_han = models.DateField("Ngày đến hạn", db_index=True)
    so_tien_phai_thu = models.DecimalField("Số tiền phải thu", max_digits=15, decimal_places=0, validators=[MinValueValidator(0)])
    so_tien_da_thu = models.DecimalField("Số tiền đã thu", max_digits=15, decimal_places=0, default=Decimal("0"), validators=[MinValueValidator(0)])
    trang_thai = models.CharField("Trạng thái", max_length=32, choices=TrangThai.choices, default=TrangThai.OPEN, db_index=True)
    ghi_chu = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField("Tạo lúc", auto_now_add=True)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Công nợ"
        verbose_name_plural = "7. Công nợ"
        ordering = ["ngay_den_han", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "ngay_den_han"], name="cli_debt_tenant_stat_due_idx"),
            models.Index(fields=["tenant_id", "hoa_don", "trang_thai"], name="cli_debt_tenant_inv_stat_idx"),
        ]
        constraints = [models.UniqueConstraint(fields=["tenant_id", "so_tham_chieu"], name="uq_debt_tenant_ref")]

    def __str__(self):
        return f"{self.so_tham_chieu} - {self.hoa_don.so_hoa_don}"

    @property
    def so_tien_con_lai(self):
        return max(self.so_tien_phai_thu - self.so_tien_da_thu, Decimal("0"))

    @property
    def so_tien_da_thu_tu_phan_bo(self):
        total = self.cac_phan_bo_thanh_toan.aggregate(total=models.Sum("so_tien"))["total"] if self.pk else None
        return total or Decimal("0")

    def clean(self):
        super().clean()
        if self.so_tien_phai_thu is not None and self.so_tien_phai_thu <= 0:
            raise ValidationError({"so_tien_phai_thu": "Số tiền phải thu phải lớn hơn 0."})
        if self.so_tien_da_thu is not None and self.so_tien_da_thu < 0:
            raise ValidationError({"so_tien_da_thu": "Số tiền đã thu không được âm."})
        if self.so_tien_phai_thu is not None and self.so_tien_da_thu is not None and self.so_tien_da_thu > self.so_tien_phai_thu:
            raise ValidationError({"so_tien_da_thu": "Số tiền đã thu không được lớn hơn số tiền phải thu."})

    def is_overdue_on(self, day=None):
        day = day or timezone.localdate()
        return self.ngay_den_han < day and self.trang_thai not in (self.TrangThai.PAID, self.TrangThai.WRITTEN_OFF)

    def record_status_transition(self, *, actor=None, old_status=None, new_status=None, note=""):
        new_status = new_status if new_status is not None else self.trang_thai
        if old_status == new_status:
            return None
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="clients",
                model_name="CongNo",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "Receivable status transition",
                changes={"status_transition": {"old": old_status, "new": new_status}, "so_tham_chieu": self.so_tham_chieu, "hoa_don_id": self.hoa_don_id},
            )
        except Exception as exc:
            logger.error("Failed to audit CongNo status transition: %s", exc)
            return None

    def transition_status(self, new_status, *, actor=None, note=""):
        old_status = self.trang_thai
        WorkflowTransitionPolicy.validate_transition(type(self).__name__, old_status, new_status, self.ALLOWED_STATUS_TRANSITIONS)
        if new_status == self.TrangThai.PAID and self.so_tien_da_thu < self.so_tien_phai_thu:
            raise ValidationError("Không được chuyển công nợ sang PAID khi chưa có phân bổ thanh toán đủ tiền.")
        self.trang_thai = new_status
        self.save(update_fields=["trang_thai", "updated_at"])
        return self.record_status_transition(actor=actor, old_status=old_status, new_status=new_status, note=note)


class ThanhToanKhachHang(TenantScopedModel):
    """Hồ sơ nguồn thanh toán khách hàng cho vòng đời công nợ/hóa đơn."""

    class HinhThucThanhToan(models.TextChoices):
        TIEN_MAT = "TIEN_MAT", "Tiền mặt"
        CHUYEN_KHOAN = "CHUYEN_KHOAN", "Chuyển khoản"
        KHAC = "KHAC", "Khác"

    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", "Nháp"
        RECEIVED = "RECEIVED", "Đã ghi nhận tiền"
        ALLOCATED = "ALLOCATED", "Đã phân bổ"
        CANCELLED = "CANCELLED", "Đã hủy"

    ALLOWED_STATUS_TRANSITIONS = {
        TrangThai.DRAFT: {TrangThai.RECEIVED, TrangThai.CANCELLED},
        TrangThai.RECEIVED: {TrangThai.ALLOCATED, TrangThai.CANCELLED},
        TrangThai.ALLOCATED: set(),
        TrangThai.CANCELLED: set(),
    }

    khach_hang = models.ForeignKey(
        KhachHangTiemNang,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_thanh_toan_khach_hang",
        verbose_name="Khách hàng",
    )
    hop_dong = models.ForeignKey(
        HopDong,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_thanh_toan_khach_hang",
        verbose_name="Hợp đồng dịch vụ",
    )
    ma_phieu = models.CharField("Mã phiếu thanh toán", max_length=64, db_index=True)
    ngay_thanh_toan = models.DateField("Ngày thanh toán", default=timezone.localdate, db_index=True)
    so_tien = models.DecimalField("Số tiền thanh toán", max_digits=15, decimal_places=0, validators=[MinValueValidator(0)])
    hinh_thuc = models.CharField("Hình thức thanh toán", max_length=32, choices=HinhThucThanhToan.choices, default=HinhThucThanhToan.CHUYEN_KHOAN)
    ma_giao_dich = models.CharField("Mã giao dịch/chứng từ ngân hàng", max_length=128, blank=True, db_index=True)
    file_chung_tu = models.FileField("File chứng từ", upload_to="thanh_toan_khach_hang/%Y/%m/", null=True, blank=True)
    trang_thai = models.CharField("Trạng thái", max_length=32, choices=TrangThai.choices, default=TrangThai.DRAFT, db_index=True)
    nguoi_ghi_nhan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_thanh_toan_khach_hang_da_ghi_nhan", verbose_name="Người ghi nhận")
    nguoi_duyet = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_thanh_toan_khach_hang_da_duyet", verbose_name="Người duyệt")
    ngay_duyet = models.DateTimeField("Thời điểm duyệt/ghi nhận", null=True, blank=True)
    ghi_chu = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField("Tạo lúc", auto_now_add=True)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True)

    objects = TenantAwareManager()

    IMMUTABLE_AFTER_ALLOCATION_FIELDS = (
        "ma_phieu",
        "so_tien",
        "khach_hang_id",
        "hop_dong_id",
        "ngay_thanh_toan",
        "hinh_thuc",
        "ma_giao_dich",
        "file_chung_tu",
    )

    class Meta:
        verbose_name = "Thanh toán khách hàng"
        verbose_name_plural = "8. Thanh toán khách hàng"
        ordering = ["-ngay_thanh_toan", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "ngay_thanh_toan"], name="cli_pay_tenant_stat_date_idx"),
            models.Index(fields=["tenant_id", "hop_dong", "trang_thai"], name="cli_pay_tenant_hd_stat_idx"),
            models.Index(fields=["tenant_id", "khach_hang", "ngay_thanh_toan"], name="cli_pay_tenant_cus_date_idx"),
        ]
        constraints = [models.UniqueConstraint(fields=["tenant_id", "ma_phieu"], name="uq_payment_tenant_code")]

    def __str__(self):
        return f"{self.ma_phieu} - {self.so_tien:,.0f}"

    @property
    def so_tien_da_phan_bo(self):
        total = self.cac_phan_bo.aggregate(total=models.Sum("so_tien"))["total"] if self.pk else None
        return total or Decimal("0")

    @property
    def so_tien_chua_phan_bo(self):
        return max(self.so_tien - self.so_tien_da_phan_bo, Decimal("0"))

    def clean(self):
        super().clean()
        if self.so_tien is not None and self.so_tien <= 0:
            raise ValidationError({"so_tien": "Số tiền thanh toán phải lớn hơn 0."})
        if self.hop_dong_id and self.khach_hang_id and self.hop_dong.khach_hang_cu_id and self.hop_dong.khach_hang_cu_id != self.khach_hang_id:
            raise ValidationError({"khach_hang": "Khách hàng thanh toán phải khớp khách hàng của hợp đồng."})

    def _immutable_value(self, field_name):
        value = getattr(self, field_name)
        if field_name == "file_chung_tu":
            return getattr(value, "name", str(value or ""))
        return value

    def assert_financial_source_fields_unchanged_after_allocation(self):
        """Keep allocated customer payment source records append-only.

        Once a payment has allocation records, core financial source fields must
        not be edited directly. Corrections require an explicit reversal or
        adjustment record in a later phase so the audit trail remains intact.
        """
        if not self.pk:
            return
        existing = type(self).objects.filter(pk=self.pk).first()
        if existing is None or not existing.cac_phan_bo.exists():
            return
        changed = []
        for field_name in self.IMMUTABLE_AFTER_ALLOCATION_FIELDS:
            if self._immutable_value(field_name) != existing._immutable_value(field_name):
                changed.append(field_name)
        if changed:
            raise ValidationError(
                "Không được sửa chứng từ thanh toán đã phát sinh phân bổ. "
                "Cần chứng từ đảo/điều chỉnh riêng ở recovery phase.",
                code="allocated_payment_immutable",
            )

    def save(self, *args, **kwargs):
        self.assert_financial_source_fields_unchanged_after_allocation()
        super().save(*args, **kwargs)

    def record_event(self, *, actor=None, action=None, note="", changes=None):
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=action or AuditLog.Action.EXECUTE,
                module="clients",
                model_name="ThanhToanKhachHang",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "Customer payment workflow event",
                changes=changes or {"ma_phieu": self.ma_phieu, "trang_thai": self.trang_thai},
            )
        except Exception as exc:
            logger.error("Failed to audit ThanhToanKhachHang event: %s", exc)
            return None

    def record_status_transition(self, *, actor=None, old_status=None, new_status=None, note=""):
        new_status = new_status if new_status is not None else self.trang_thai
        if old_status == new_status:
            return None
        return self.record_event(
            actor=actor,
            note=note or "Customer payment status transition",
            changes={"status_transition": {"old": old_status, "new": new_status}, "ma_phieu": self.ma_phieu, "so_tien": str(self.so_tien)},
        )

    def transition_status(self, new_status, *, actor=None, note=""):
        old_status = self.trang_thai
        WorkflowTransitionPolicy.validate_transition(type(self).__name__, old_status, new_status, self.ALLOWED_STATUS_TRANSITIONS)
        if new_status == self.TrangThai.CANCELLED and self.cac_phan_bo.exists():
            raise ValidationError("Không được hủy thanh toán đã có phân bổ. Cần recovery path/reversal riêng.")
        if new_status == self.TrangThai.ALLOCATED and self.so_tien_da_phan_bo <= 0:
            raise ValidationError("Không được chuyển thanh toán sang ALLOCATED khi chưa có phân bổ.")
        self.trang_thai = new_status
        update_fields = ["trang_thai", "updated_at"]
        if new_status in (self.TrangThai.RECEIVED, self.TrangThai.ALLOCATED) and actor and not self.nguoi_duyet_id:
            self.nguoi_duyet = actor
            self.ngay_duyet = timezone.now()
            update_fields.extend(["nguoi_duyet", "ngay_duyet"])
        self.save(update_fields=update_fields)
        return self.record_status_transition(actor=actor, old_status=old_status, new_status=new_status, note=note)


class PhanBoThanhToanHoaDon(TenantScopedModel):
    """Phân bổ một khoản thanh toán khách hàng vào hóa đơn/công nợ."""

    thanh_toan = models.ForeignKey(ThanhToanKhachHang, on_delete=models.PROTECT, related_name="cac_phan_bo", verbose_name="Thanh toán khách hàng")
    hoa_don = models.ForeignKey(HoaDon, on_delete=models.PROTECT, null=True, blank=True, related_name="cac_phan_bo_thanh_toan", verbose_name="Hóa đơn")
    cong_no = models.ForeignKey(CongNo, on_delete=models.PROTECT, null=True, blank=True, related_name="cac_phan_bo_thanh_toan", verbose_name="Công nợ")
    so_tien = models.DecimalField("Số tiền phân bổ", max_digits=15, decimal_places=0, validators=[MinValueValidator(0)])
    ngay_phan_bo = models.DateTimeField("Thời điểm phân bổ", auto_now_add=True, db_index=True)
    nguoi_phan_bo = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_phan_bo_thanh_toan_khach_hang", verbose_name="Người phân bổ")
    ghi_chu = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField("Tạo lúc", auto_now_add=True)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = "Phân bổ thanh toán hóa đơn"
        verbose_name_plural = "9. Phân bổ thanh toán hóa đơn"
        ordering = ["-ngay_phan_bo", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "thanh_toan", "ngay_phan_bo"], name="cli_alloc_tenant_pay_date_idx"),
            models.Index(fields=["tenant_id", "hoa_don"], name="cli_alloc_tenant_inv_idx"),
            models.Index(fields=["tenant_id", "cong_no"], name="cli_alloc_tenant_debt_idx"),
        ]

    def __str__(self):
        target = self.cong_no or self.hoa_don
        return f"{self.thanh_toan.ma_phieu} → {target} ({self.so_tien:,.0f})"

    def _sum_existing_for_payment(self):
        qs = PhanBoThanhToanHoaDon.objects.filter(thanh_toan=self.thanh_toan)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return qs.aggregate(total=models.Sum("so_tien"))["total"] or Decimal("0")

    def _sum_existing_for_invoice(self):
        if not self.hoa_don_id:
            return Decimal("0")
        qs = PhanBoThanhToanHoaDon.objects.filter(hoa_don=self.hoa_don)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return qs.aggregate(total=models.Sum("so_tien"))["total"] or Decimal("0")

    def _sum_existing_for_debt(self):
        if not self.cong_no_id:
            return Decimal("0")
        qs = PhanBoThanhToanHoaDon.objects.filter(cong_no=self.cong_no)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return qs.aggregate(total=models.Sum("so_tien"))["total"] or Decimal("0")

    IMMUTABLE_SOURCE_FIELDS = ("thanh_toan_id", "hoa_don_id", "cong_no_id", "so_tien")

    def assert_source_fields_unchanged_after_create(self):
        """Make payment allocation source records append-only after creation."""
        if not self.pk:
            return
        existing = type(self).objects.filter(pk=self.pk).first()
        if existing is None:
            return
        changed = [field for field in self.IMMUTABLE_SOURCE_FIELDS if getattr(self, field) != getattr(existing, field)]
        if changed:
            raise ValidationError(
                "Không được sửa phân bổ thanh toán đã tạo. Cần chứng từ đảo/điều chỉnh riêng ở recovery phase.",
                code="allocation_source_immutable",
            )

    def clean(self):
        super().clean()
        self.assert_source_fields_unchanged_after_create()
        if self.so_tien is not None and self.so_tien <= 0:
            raise ValidationError({"so_tien": "Số tiền phân bổ phải lớn hơn 0."})
        if not self.cong_no_id:
            raise ValidationError({"cong_no": "Phase E v3 yêu cầu phân bổ phải gắn với công nợ cụ thể để không lệch hóa đơn/công nợ."})
        if self.cong_no_id and not self.hoa_don_id:
            self.hoa_don = self.cong_no.hoa_don
        if self.cong_no_id and self.hoa_don_id and self.cong_no.hoa_don_id != self.hoa_don_id:
            raise ValidationError({"cong_no": "Công nợ phải thuộc cùng hóa đơn được phân bổ."})
        tenant_ids = {
            tenant_id
            for tenant_id in (
                getattr(self.thanh_toan, "tenant_id", None),
                getattr(self.hoa_don, "tenant_id", None) if self.hoa_don_id else None,
                getattr(self.cong_no, "tenant_id", None) if self.cong_no_id else None,
            )
            if tenant_id is not None
        }
        if len(tenant_ids) > 1:
            raise ValidationError("Thanh toán, hóa đơn và công nợ phải thuộc cùng tenant.")
        target_invoice = self.hoa_don or (self.cong_no.hoa_don if self.cong_no_id else None)
        if target_invoice is not None:
            if self.thanh_toan.hop_dong_id and target_invoice.hop_dong_id != self.thanh_toan.hop_dong_id:
                raise ValidationError({"hoa_don": "Thanh toán chỉ được phân bổ vào hóa đơn/công nợ cùng hợp đồng."})
            payment_customer_id = self.thanh_toan.khach_hang_id or getattr(getattr(self.thanh_toan, "hop_dong", None), "khach_hang_cu_id", None)
            target_customer_id = getattr(getattr(target_invoice, "hop_dong", None), "khach_hang_cu_id", None)
            if payment_customer_id and target_customer_id and payment_customer_id != target_customer_id:
                raise ValidationError({"hoa_don": "Thanh toán chỉ được phân bổ vào hóa đơn/công nợ cùng khách hàng."})
        if self.thanh_toan.trang_thai not in (ThanhToanKhachHang.TrangThai.RECEIVED, ThanhToanKhachHang.TrangThai.ALLOCATED):
            raise ValidationError({"thanh_toan": "Chỉ được phân bổ thanh toán đã ghi nhận tiền."})
        if self.hoa_don and self.hoa_don.trang_thai == HoaDon.TrangThai.CANCELLED:
            raise ValidationError({"hoa_don": "Không được phân bổ vào hóa đơn đã hủy."})
        if self.cong_no and self.cong_no.trang_thai == CongNo.TrangThai.WRITTEN_OFF:
            raise ValidationError({"cong_no": "Không được phân bổ vào công nợ đã xóa/điều chỉnh nợ."})
        if self._sum_existing_for_payment() + self.so_tien > self.thanh_toan.so_tien:
            raise ValidationError({"so_tien": "Tổng phân bổ không được vượt số tiền thanh toán."})
        if self.cong_no_id and self._sum_existing_for_debt() + self.so_tien > self.cong_no.so_tien_phai_thu:
            raise ValidationError({"so_tien": "Phân bổ không được vượt số còn phải thu của công nợ."})
        if self.hoa_don_id and self._sum_existing_for_invoice() + self.so_tien > self.hoa_don.tong_tien:
            raise ValidationError({"so_tien": "Phân bổ không được vượt số còn phải thu của hóa đơn."})

    def save(self, *args, **kwargs):
        self.assert_source_fields_unchanged_after_create()
        if not self.cong_no_id:
            raise ValidationError("Phase E v3 yêu cầu phân bổ phải gắn với công nợ cụ thể; invoice-only allocation bị chặn.")
        if self.cong_no_id and not self.hoa_don_id:
            self.hoa_don = self.cong_no.hoa_don
        if self.cong_no_id and self.hoa_don_id and self.cong_no.hoa_don_id != self.hoa_don_id:
            raise ValidationError("Công nợ phải thuộc cùng hóa đơn được phân bổ.")
        super().save(*args, **kwargs)

    def record_event(self, *, actor=None, note="", changes=None):
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.EXECUTE,
                module="clients",
                model_name="PhanBoThanhToanHoaDon",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "Customer payment allocation event",
                changes=changes or {
                    "thanh_toan_id": self.thanh_toan_id,
                    "hoa_don_id": self.hoa_don_id,
                    "cong_no_id": self.cong_no_id,
                    "so_tien": str(self.so_tien),
                },
            )
        except Exception as exc:
            logger.error("Failed to audit PhanBoThanhToanHoaDon event: %s", exc)
            return None


class MucTieuDonGiaHistory(TenantScopedModel):
    """
    Effective-dated payroll rate history for reconciliation-safe retroactive payroll.
    """

    muc_tieu = models.ForeignKey(
        MucTieu,
        on_delete=models.CASCADE,
        related_name="lich_su_don_gia",
        verbose_name="Muc tieu bao ve",
    )
    ngay_hieu_luc = models.DateField(
        "Ngay hieu luc",
        help_text="Moc bat dau ap dung don gia cho payroll.",
    )
    luong_khoan_bao_ve = models.DecimalField(
        "Luong khoan dinh muc (Thang)",
        max_digits=12,
        decimal_places=0,
    )
    so_gio_mot_ngay = models.DecimalField(
        "Dinh muc gio truc/ngay",
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.25"))],
    )
    ghi_chu = models.TextField(
        "Ghi chu doi soat",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects: "TenantAwareManager" = TenantAwareManager()

    class Meta:
        verbose_name = "Lich su don gia muc tieu"
        verbose_name_plural = "5. Lich su don gia muc tieu"
        ordering = ["ngay_hieu_luc", "id"]
        unique_together = ("muc_tieu", "ngay_hieu_luc", "tenant_id")

    def clean(self):
        if self.muc_tieu_id and self.muc_tieu.hop_dong.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError("Lich su don gia phai cung organization voi muc tieu.")
        super().clean()

    def __str__(self):
        return f"{self.muc_tieu.ten_muc_tieu} - {self.ngay_hieu_luc:%d/%m/%Y}"
=======
    
    def get_don_gia_gio_thuc_te(self, thang, nam):
        """
        Hàm tính đơn giá giờ dựa trên số ngày thực tế của tháng/năm đó.
        Nghiệp vụ: Đơn giá = Lương khoán / (Số ngày tháng thực tế * Số giờ ca trực).
        Ví dụ: Tháng 2/2025 (28 ngày) trực ca 12h -> Tổng giờ chuẩn = 336h.
        """
        try:
            # monthrange trả về (thứ ngày đầu tiên, tổng số ngày trong tháng)
            _, so_ngay_trong_thang = calendar.monthrange(int(nam), int(thang))
            tong_gio_chuan = float(so_ngay_trong_thang) * float(self.so_gio_mot_ngay)
            
            if tong_gio_chuan > 0:
                return float(self.luong_khoan_bao_ve) / tong_gio_chuan
            return 0
        except (TypeError, ValueError, ZeroDivisionError, calendar.IllegalMonthError):
            return 0
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
