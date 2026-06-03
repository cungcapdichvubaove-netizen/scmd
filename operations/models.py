# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: operations/models.py
Author: Mr. Anh (CTO) & AI Assistant
Created Date: 2025-12-10
Updated Date: 2026-05-15
Version: v2.0.0-pro
Description: Model quản lý Vận hành, Chấm công và Xử lý sự cố.
             HARDENING PHASE: Chuẩn hóa Multi-tenancy và Geo-spatial helpers.
             - Tích hợp PointField cho định vị chính xác cao.
             - Gia cố Anti-fraud và GEOFENCING logic.
             - SSOT: Tuân thủ tuyệt đối DOCUMENTATION.md v2.0.0.
"""

import uuid
import logging
from datetime import datetime, timedelta
from django.contrib.gis.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import IntegrityError, transaction, models as db_models # Alias models to db_models to avoid conflict with gis.db.models
from core.managers import TenantAwareManager

from users.models import NhanVien
from clients.models import MucTieu

# Logger cho hệ thống vận hành SCMD
logger = logging.getLogger(__name__)

from django.conf import settings
# ==============================================================================
# 0. MULTI-TENANCY CORE (Zero Trust Architecture)
# ==============================================================================

class ViTriChotManager(TenantAwareManager):
    """Manager cho ViTriChot giúp tối ưu hóa N+1 với MucTieu"""
    def get_queryset(self):
        return super().get_queryset().select_related('muc_tieu')


class ViTriChot(models.Model):
    """Định nghĩa các vị trí trực cụ thể tại mục tiêu (Cổng chính, Tuần tra, Giám sát...)"""
    tenant_id = models.UUIDField(_("Tenant ID"), db_index=True, default=uuid.uuid4, editable=False) # Default kept for migration compatibility, but enforced in save()
    
    muc_tieu = models.ForeignKey(
        MucTieu, 
        on_delete=models.CASCADE, 
        related_name="cac_vi_tri_chot", 
        verbose_name=_("Mục tiêu bảo vệ"),
        help_text=_("Chọn khách hàng/mục tiêu quản lý vị trí trực này")
    )
    ten_vi_tri = models.CharField(
        _("Tên vị trí trực"), 
        max_length=255,
        help_text=_("VD: Cổng chính, Kho A, Tuần tra vòng ngoài")
    )

    objects = ViTriChotManager()

    def save(self, *args, **kwargs):
        from django.core.exceptions import ImproperlyConfigured
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID is not defined in settings. Cannot save tenant-aware model.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID # Enforce SCMD_ORGANIZATION_ID
        super().save(*args, **kwargs)

    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(_(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID} for this organization."))
        super().clean()

    class Meta:
        verbose_name = _("Vị trí chốt trực")
        verbose_name_plural = _("1. Danh sách Vị trí chốt")

    def __str__(self):
        try:
            return f"{self.ten_vi_tri} ({self.muc_tieu.ten_muc_tieu})"
        except Exception:
            return f"{self.ten_vi_tri}"


class CaLamViec(models.Model):
    """Quy định khung thời gian các ca làm việc (Ca ngày, Ca đêm, Ca hành chính)"""
    tenant_id = models.UUIDField(_("Tenant ID"), db_index=True, default=uuid.uuid4, editable=False) # Default kept for migration compatibility, but enforced in save()

    ten_ca = models.CharField(
        _("Tên ca trực"), 
        max_length=100,
        help_text=_("VD: Ca 1 (06h-18h), Ca hành chính")
    )
    gio_bat_dau = models.TimeField(_("Giờ bắt đầu"))
    gio_ket_thuc = models.TimeField(_("Giờ kết thúc"))

    objects = TenantAwareManager()

    def save(self, *args, **kwargs):
        from django.core.exceptions import ImproperlyConfigured
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID is not defined in settings. Cannot save tenant-aware model.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID # Enforce SCMD_ORGANIZATION_ID
        super().save(*args, **kwargs)

    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(_(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID} for this organization."))
        super().clean()

    class Meta:
        verbose_name = _("Ca làm việc")
        verbose_name_plural = _("2. Danh sách Ca làm việc")
        ordering = ['gio_bat_dau']

    def __str__(self):
        return f"{self.ten_ca} ({self.gio_bat_dau.strftime('%H:%M')} - {self.gio_ket_thuc.strftime('%H:%M')})"
    
    @property
    def is_night_shift(self):
        """Kiểm tra ca trực có vắt qua ngày hôm sau hay không (Ca đêm)"""
        if self.gio_bat_dau and self.gio_ket_thuc:
            return self.gio_ket_thuc < self.gio_bat_dau
        return False


class PhanCongManager(TenantAwareManager):
    """Tối ưu hóa truy vấn bảng phân công nhằm giảm thiểu N+1 Query"""
    def get_queryset(self):
        return super().get_queryset().select_related(
            'nhan_vien', 
            'ca_lam_viec', 
            'vi_tri_chot__muc_tieu',
            'chamcong'  # Thêm quan hệ OneToOne để tránh N+1 khi gọi serializer
        )


class PhanCongCaTruc(models.Model):
    """Lịch trình phân công nhân sự cụ thể theo ngày và vị trí"""
    tenant_id = models.UUIDField(_("Tenant ID"), db_index=True, default=uuid.uuid4, editable=False) # Default kept for migration compatibility, but enforced in save()

    vi_tri_chot = models.ForeignKey(
        ViTriChot, 
        on_delete=models.CASCADE, 
        related_name="cac_phan_cong",
        verbose_name=_("Vị trí chốt")
    )
    nhan_vien = models.ForeignKey(
        NhanVien, 
        on_delete=models.CASCADE, 
        related_name="cac_phan_cong",
        verbose_name=_("Nhân viên thực hiện")
    )
    ca_lam_viec = models.ForeignKey(
        CaLamViec, 
        on_delete=models.CASCADE, 
        related_name="cac_phan_cong",
        verbose_name=_("Ca trực")
    )
    ngay_truc = models.DateField(
        _("Ngày thực hiện"), 
        db_index=True,
        help_text=_("Định dạng chuẩn: Ngày/Tháng/Năm")
    )

    objects = PhanCongManager()

    def save(self, *args, **kwargs):
        from django.core.exceptions import ImproperlyConfigured
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID is not defined in settings. Cannot save tenant-aware model.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID # Enforce SCMD_ORGANIZATION_ID
        super().save(*args, **kwargs)

    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(_(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID} for this organization."))
        super().clean()

    class Meta:
        verbose_name = _("Phân công ca trực")
        verbose_name_plural = _("3. Bảng Phân công ca trực")
        ordering = ["ngay_truc", "ca_lam_viec__gio_bat_dau"]
        unique_together = [['nhan_vien', 'ngay_truc', 'ca_lam_viec']]
        indexes = [
            models.Index(fields=['nhan_vien', 'ngay_truc']),
            models.Index(fields=['vi_tri_chot', 'ngay_truc']),
        ]

    def __str__(self):
        try:
            return f"{self.nhan_vien.ho_ten} - {self.ngay_truc.strftime('%d/%m/%Y')} ({self.ca_lam_viec.ten_ca})"
        except Exception:
            return f"Phân công {self.id}"

    @property
    def da_checkin(self):
        """Kiểm tra nhân viên đã thực hiện điểm danh vào ca chưa"""
        try:
            return hasattr(self, 'chamcong') and self.chamcong.thoi_gian_check_in is not None
        except Exception:
            return False
    
    def get_thoi_gian_bat_dau_thuc_te(self):
        """Kết hợp ngày trực và giờ bắt đầu ca"""
        if not self.ngay_truc or not self.ca_lam_viec:
            return None
        return datetime.combine(self.ngay_truc, self.ca_lam_viec.gio_bat_dau)

    def get_thoi_gian_ket_thuc_thuc_te(self):
        """Tính toán thời điểm kết thúc ca (xử lý trường hợp ca đêm qua ngày)"""
        if not self.ngay_truc or not self.ca_lam_viec:
            return None
        if self.ca_lam_viec.is_night_shift:
            return datetime.combine(self.ngay_truc + timedelta(days=1), self.ca_lam_viec.gio_ket_thuc)
        return datetime.combine(self.ngay_truc, self.ca_lam_viec.gio_ket_thuc)


class ChamCong(models.Model):
    """
    Model lưu trữ dữ liệu chấm công GPS.
    GEO UPDATE: Sử dụng PointField (WGS84) để lưu trữ tọa độ chính xác cao.
    """
    tenant_id = models.UUIDField(_("Tenant ID"), db_index=True, default=uuid.uuid4, editable=False) # Default kept for migration compatibility, but enforced in save()

    ca_truc = models.OneToOneField(
        PhanCongCaTruc, 
        on_delete=models.CASCADE, 
        verbose_name=_("Phiên trực liên quan"), 
        related_name='chamcong'
    )
    
    thoi_gian_check_in = models.DateTimeField(
        _("Thời gian Check-in"), 
        null=True, 
        blank=True, 
        db_index=True
    )
    thoi_gian_check_out = models.DateTimeField(
        _("Thời gian Check-out"), 
        null=True, 
        blank=True
    )
    
    anh_check_in = models.ImageField(
        _("Ảnh xác thực In"), 
        upload_to="check_in/%Y/%m/", 
        null=True, 
        blank=True
    )
    anh_check_out = models.ImageField(
        _("Ảnh xác thực Out"), 
        upload_to="check_out/%Y/%m/", 
        null=True, 
        blank=True
    )
    
    # GEO SPATIAL DATA (SRID 4326 - WGS84)
    location_check_in = models.PointField(
        _("Tọa độ Check-in"), 
        srid=4326, 
        null=True, 
        blank=True, 
        geography=True,
        help_text=_("Tọa độ GPS lúc vào ca (Kinh độ, Vĩ độ)")
    )
    location_check_out = models.PointField(
        _("Tọa độ Check-out"), 
        srid=4326, 
        null=True, 
        blank=True, 
        geography=True,
        help_text=_("Tọa độ GPS lúc ra ca")
    )
    
    # ANTI-FRAUD
    ip_check_in = models.GenericIPAddressField(_("IP nguồn In"), null=True, blank=True)
    ip_check_out = models.GenericIPAddressField(_("IP nguồn Out"), null=True, blank=True)
    thiet_bi_check_in = models.CharField(_("Thiết bị In"), max_length=255, blank=True, null=True)
    thiet_bi_check_out = models.CharField(_("Thiết bị Out"), max_length=255, blank=True, null=True)

    # GEOFENCING VALIDATION (SSOT from MucTieu)
    vi_tri_hop_le = models.BooleanField(
        _("Đúng vị trí quy định?"), 
        default=True,
        help_text=_("Hệ thống tự động kiểm tra bán kính mục tiêu")
    )
    khoang_cach_check_in = models.FloatField(
        _("Độ lệch khoảng cách (m)"), 
        default=0.0,
        help_text=_("Khoảng cách từ nhân viên đến tâm mục tiêu (mét)")
    )

    # PHÂN TÍCH CA TRỰC (AUTO-CALCULATED) - Nâng cấp v2.0.0
    thuc_lam_gio = models.FloatField(
        _("Giờ làm thực tế"), 
        default=0.0,
        help_text=_("Số giờ làm việc tính toán dựa trên thời gian check-in/out")
    )
    di_muon_phut = models.IntegerField(
        _("Đi muộn (phút)"), 
        default=0,
        help_text=_("Số phút vào ca trễ so với quy định")
    )
    ve_som_phut = models.IntegerField(
        _("Về sớm (phút)"), 
        default=0,
        help_text=_("Số phút rời ca sớm so với quy định")
    )
    phat_vi_pham = models.DecimalField(
        _("Tiền phạt ca trực"), 
        max_digits=12, 
        decimal_places=0, 
        default=0,
        help_text=_("Tổng tiền phạt vi phạm phát sinh trong ca trực này")
    )

    ghi_chu = models.TextField(_("Ghi chú chấm công"), blank=True)

    objects = TenantAwareManager()

    def save(self, *args, **kwargs):
        from django.core.exceptions import ImproperlyConfigured
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID is not defined in settings. Cannot save tenant-aware model.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID # Enforce SCMD_ORGANIZATION_ID
        super().save(*args, **kwargs)

    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(_(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID} for this organization."))
        super().clean()

    class Meta:
        verbose_name = _("Dữ liệu Chấm công")
        verbose_name_plural = _("4. Dữ liệu Chấm công")

    def calculate_work_hours(self):
        # Logic này nên được dời về UseCase, tuy nhiên giữ lại wrapper 
        # để không phá vỡ các legacy template tags nếu có.
        from operations.application.attendance_use_cases import CalculateWorkHoursUseCase
        return CalculateWorkHoursUseCase.execute(self)

    # --- API & UI COMPATIBILITY HELPERS ---
    @property
    def lat_check_in(self):
        try:
            return self.location_check_in.y if self.location_check_in else None
        except Exception:
            return None

    @property
    def long_check_in(self):
        try:
            return self.location_check_in.x if self.location_check_in else None
        except Exception:
            return None

    @property
    def lat_check_out(self):
        """Lấy vĩ độ từ PointField check-out (Hardening Phase)"""
        try:
            return self.location_check_out.y if self.location_check_out else None
        except Exception:
            return None

    @property
    def long_check_out(self):
        """Lấy kinh độ từ PointField check-out (Hardening Phase)"""
        try:
            return self.location_check_out.x if self.location_check_out else None
        except Exception:
            return None


# ==============================================================================
# 2. QUẢN LÝ SỰ CỐ & ĐỀN BÙ
# ==============================================================================

class BaoCaoSuCo(models.Model):
    """Hồ sơ ghi nhận các sự việc/sự cố xảy ra tại mục tiêu"""
    MUC_DO_CHOICES = [
        ('THAP', _('Thấp (Nhắc nhở)')), 
        ('TB', _('Trung bình (Lập biên bản)')), 
        ('CAO', _('Cao (Thiệt hại tài sản)')), 
        ('NGUY_HIEM', _('Nguy hiểm (Đe dọa tính mạng/An ninh)'))
    ]
    
    TRANG_THAI_CHOICES = [
        ('CHO_XU_LY', _('⏳ Chờ xử lý')), 
        ('DANG_XU_LY', _('🔄 Đang xử lý')), 
        ('DA_XU_LY', _('✅ Đã xử lý (Không đền bù)')), 
        ('CHO_DEN_BU', _('💸 Chờ đền bù (Có thiệt hại)')), 
        ('HOAN_TAT', _('🏁 Hoàn tất xử lý')), 
        ('HUY', _('❌ Đã hủy bỏ'))
    ]

    tenant_id = models.UUIDField(_("Tenant ID"), db_index=True, default=uuid.uuid4, editable=False) # Default kept for migration compatibility, but enforced in save()

    tieu_de = models.CharField(
        _("Tiêu đề sự cố"), 
        max_length=200,
        help_text=_("Tóm tắt ngắn gọn sự việc xảy ra")
    )
    
    # FIXED: Bổ sung default và blank để vượt qua lỗi migration nullable
    ma_su_co = models.CharField(
        _("Mã vụ việc"), 
        max_length=30, 
        unique=True, 
        editable=False
    )
    
    nhan_vien_bao_cao = models.ForeignKey(
        NhanVien, on_delete=models.CASCADE, 
        related_name='cac_su_co_da_bao', 
        verbose_name=_("Người phát hiện"), 
        null=True, blank=True
    )
    muc_tieu = models.ForeignKey(
        MucTieu, 
        on_delete=models.CASCADE, 
        verbose_name=_("Địa điểm (Mục tiêu)"),
        related_name='cac_su_co',
        null=True, blank=True
    )
    ca_truc = models.ForeignKey(
        PhanCongCaTruc, 
        on_delete=models.SET_NULL, 
        related_name='cac_su_co',
        null=True, blank=True, 
        verbose_name=_("Phiên trực liên quan")
    )
    
    thoi_gian_phat_hien = models.DateTimeField(
        _("Thời gian phát hiện"), 
        default=timezone.now, 
        db_index=True
    )
    mo_ta_chi_tiet = models.TextField(
        _("Diễn biến chi tiết"), 
        default="",
        help_text=_("Tường trình diễn biến từ lúc phát hiện đến lúc xử lý")
    )
    
    hinh_anh_1 = models.ImageField(_("Ảnh hiện trường 1"), upload_to='su_co/%Y/%m/', blank=True, null=True)
    hinh_anh_2 = models.ImageField(_("Ảnh hiện trường 2"), upload_to='su_co/%Y/%m/', blank=True, null=True)
    file_ghi_am = models.FileField(_("File ghi âm (Voice)"), upload_to='su_co/audio/%Y/%m/', blank=True, null=True)

    muc_do = models.CharField(
        _("Mức độ nghiêm trọng"), 
        max_length=20, 
        choices=MUC_DO_CHOICES, 
        default='TB', 
        db_index=True
    )
    trang_thai = models.CharField(
        _("Trạng thái hồ sơ"), 
        max_length=20, 
        choices=TRANG_THAI_CHOICES, 
        default='CHO_XU_LY', 
        db_index=True
    )
    
    tong_thiet_hai = models.DecimalField(
        _("Tổng giá trị thiệt hại"), 
        max_digits=15, 
        decimal_places=0, 
        default=0
    )
    cong_ty_chi_tra = models.DecimalField(
        _("Công ty chi trả"), 
        max_digits=15, 
        decimal_places=0, 
        default=0, 
        help_text=_("Số tiền công ty hỗ trợ đền bù cho khách hàng")
    )
    
    nhan_vien_co_loi = models.ForeignKey(
        NhanVien, on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='cac_su_co_gay_ra', 
        verbose_name=_("Nhân viên gây lỗi")
    )
    phai_thu_nhan_vien = models.DecimalField(
        _("Số tiền trừ lương NV"), 
        max_digits=15, 
        decimal_places=0, 
        default=0, 
        help_text=_("Khoản khấu trừ lương nhân viên gây lỗi")
    )
    
    nguoi_xu_ly = models.ForeignKey(
        NhanVien, on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='cac_su_co_phai_xu_ly', 
        verbose_name=_("Cán bộ thụ lý")
    )
    ghi_chu_quan_ly = models.TextField(_("Phương án/Kết quả xử lý"), blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    thoi_gian_quyet_toan = models.DateTimeField(
        _("Thời điểm chốt đền bù"), 
        null=True, 
        blank=True,
        help_text=_("Mốc thời gian dùng để truy vấn vào bảng lương (SSOT)")
    )

    objects = TenantAwareManager()

    @staticmethod
    def generate_incident_code():
        """Generate a human-readable unique incident code."""
        return f"SC-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"

    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(_(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID} for this organization."))
        super().clean()

    def save(self, *args, **kwargs):
        """Persist incident data while enforcing tenant and identity invariants."""
        from django.core.exceptions import ImproperlyConfigured
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID is not defined in settings. Cannot save tenant-aware model.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID # Enforce SCMD_ORGANIZATION_ID

        auto_generated_code = False
        if not self.ma_su_co or self.ma_su_co == 'PENDING':
            self.ma_su_co = self.generate_incident_code()
            auto_generated_code = True

        for _ in range(5):
            try:
                super().save(*args, **kwargs)
                return
            except IntegrityError as exc:
                if not auto_generated_code or 'ma_su_co' not in str(exc):
                    raise
                self.ma_su_co = self.generate_incident_code()

        raise IntegrityError("Unable to generate a unique ma_su_co after multiple attempts.")

    def __str__(self):
        return f"[{self.get_muc_do_display()}] {self.tieu_de} ({self.ma_su_co})"
    
    class Meta:
        verbose_name = _("Báo cáo sự cố")
        verbose_name_plural = _("5. Danh sách sự cố")
        ordering = ['-created_at']


# ==============================================================================
# 3. QUẢN LÝ ĐỀ XUẤT & KIỂM TRA QUÂN SỐ
# ==============================================================================

class BaoCaoDeXuat(models.Model):
    """Hệ thống đề xuất nghiệp vụ từ mục tiêu về văn phòng"""
    class LoaiDeXuat(models.TextChoices):
        VAT_TU = "VATTU", _("Xin cấp vật tư/Văn phòng phẩm")
        DONG_PHUC = "DONGPHUC", _("Xin cấp mới/đổi đồng phục")
        DOI_CA = "DOICA", _("Xin đổi ca trực/Tăng ca")
        NGHI_PHEP = "NGHIPHEP", _("Xin nghỉ phép/Nghỉ chế độ")
        KHAC = "KHAC", _("Các đề xuất khác")

    class TrangThai(models.TextChoices):
        CHO_CHI_HUY = "CHO_CH", _("⏳ Chờ Chỉ huy mục tiêu duyệt")
        CHO_NGHIEP_VU = "CHO_NV", _("🛡️ Chờ Phòng Nghiệp vụ duyệt")
        DA_DUYET = "DUYET", _("✅ Đã chấp thuận")
        TU_CHOI = "TUCHOI", _("❌ Đã từ chối")
        CHUYEN_VAN_PHONG = "VP", _("🏢 Vượt thẩm quyền - Chuyển Văn phòng")

    tenant_id = models.UUIDField(_("Tenant ID"), db_index=True, default=uuid.uuid4, editable=False) # Default kept for migration compatibility, but enforced in save()

    nhan_vien = models.ForeignKey(
        NhanVien, 
        on_delete=models.CASCADE, 
        related_name='cac_de_xuat',
        verbose_name=_("Nhân viên đề xuất")
    )
    muc_tieu = models.ForeignKey(
        MucTieu, 
        on_delete=models.SET_NULL, 
        related_name='cac_de_xuat',
        null=True, blank=True, 
        verbose_name=_("Tại mục tiêu")
    )
    
    loai_de_xuat = models.CharField(_("Loại đề xuất"), max_length=20, choices=LoaiDeXuat.choices, default=LoaiDeXuat.KHAC)
    tieu_de = models.CharField(_("Tiêu đề ngắn gọn"), max_length=255)
    noi_dung = models.TextField(_("Nội dung trình bày chi tiết"))
    hinh_anh = models.ImageField(_("Hình ảnh/Tài liệu đính kèm"), upload_to="de_xuat/%Y/%m/", null=True, blank=True)
    
    trang_thai = models.CharField(_("Trạng thái phê duyệt"), max_length=20, choices=TrangThai.choices, default=TrangThai.CHO_CHI_HUY)
    ngay_gui = models.DateTimeField(_("Ngày gửi đề xuất"), default=timezone.now, db_index=True)
    
    chi_huy_duyet = models.ForeignKey(
        NhanVien, on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name="cac_de_xuat_chi_huy_duyet", 
        verbose_name=_("Chỉ huy duyệt")
    )
    y_kien_chi_huy = models.TextField(_("Ý kiến của Chỉ huy"), blank=True, null=True)
    thoi_gian_chi_huy_duyet = models.DateTimeField(_("Thời điểm CH duyệt"), null=True, blank=True)
    
    nguoi_duyet_nghiep_vu = models.ForeignKey(
        NhanVien, on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name="cac_de_xuat_nghiep_vu_duyet", 
        verbose_name=_("Nghiệp vụ duyệt")
    )
    y_kien_nghiep_vu = models.TextField(_("Ý kiến của Phòng nghiệp vụ"), blank=True, null=True)
    thoi_gian_nghiep_vu_duyet = models.DateTimeField(_("Thời điểm NV duyệt"), null=True, blank=True)

    objects = TenantAwareManager()

    def save(self, *args, **kwargs):
        from django.core.exceptions import ImproperlyConfigured
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID is not defined in settings. Cannot save tenant-aware model.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID # Enforce SCMD_ORGANIZATION_ID
        super().save(*args, **kwargs)

    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(_(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID} for this organization."))
        super().clean()

    class Meta:
        verbose_name = _("Đề xuất nghiệp vụ")
        verbose_name_plural = _("6. Danh sách Đề xuất")
        ordering = ['-ngay_gui']

    def __str__(self):
        return f"{self.tieu_de} - {self.get_trang_thai_display()}"


class KiemTraQuanSo(models.Model):
    """Giao thức Alive Check: Gọi phản hồi ngẫu nhiên để kiểm tra tình trạng làm việc"""
    TRANG_THAI_CHECK = [
        ('PENDING', _('⏳ Đang chờ phản hồi')), 
        ('OK', _('✅ Đã xác nhận (Hoàn thành)')), 
        ('MISSED', _('❌ Bỏ lỡ (Không phản hồi)')), 
        ('LATE', _('🕒 Phản hồi muộn'))
    ]

    tenant_id = models.UUIDField(_("Tenant ID"), db_index=True, default=uuid.uuid4, editable=False) # Default kept for migration compatibility, but enforced in save()

    ca_truc = models.ForeignKey(
        PhanCongCaTruc, 
        on_delete=models.CASCADE, 
        related_name='cac_lan_kiem_tra', 
        verbose_name=_("Ca trực kiểm tra")
    )
    thoi_gian_gui_yeu_cau = models.DateTimeField(_("Thời điểm phát lệnh"), auto_now_add=True)
    thoi_gian_phan_hoi = models.DateTimeField(_("Thời điểm phản hồi"), null=True, blank=True)
    anh_xac_thuc = models.ImageField(_("Ảnh xác thực Alive"), upload_to='alive_check/%Y/%m/', null=True, blank=True)
    toa_do_xac_thuc = models.CharField(
        _("Vị trí xác thực"), 
        max_length=100, 
        null=True, 
        blank=True,
        help_text=_("Tọa độ chuỗi lưu tạm thời từ Mobile app")
    )
    trang_thai = models.CharField(_("Kết quả kiểm tra"), max_length=20, choices=TRANG_THAI_CHECK, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantAwareManager()

    def save(self, *args, **kwargs):
        from django.core.exceptions import ImproperlyConfigured
        if not hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID is not defined in settings. Cannot save tenant-aware model.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID # Enforce SCMD_ORGANIZATION_ID
        super().save(*args, **kwargs)

    def clean(self):
        if hasattr(settings, 'SCMD_ORGANIZATION_ID') and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(_(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID} for this organization."))
        super().clean()

    class Meta:
        verbose_name = _("Kiểm tra quân số")
        verbose_name_plural = _("7. Lịch sử Alive Check")
        ordering = ['-created_at']

    def __str__(self): 
        try:
            return f"Alive Check: {self.ca_truc.nhan_vien.ho_ten} - {self.get_trang_thai_display()}"
        except Exception:
            return f"Alive Check {self.id}"
