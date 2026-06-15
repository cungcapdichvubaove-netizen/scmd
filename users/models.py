# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: users/models.py
Author: Mr. Anh
Created Date: 2025-12-05
Updated Date: 2026-04-28
Version: v1.1.0
Description: Model quản lý cấu trúc nhân sự, định danh và hồ sơ nghiệp vụ SCMD.
             ENHANCEMENT: Tối ưu Manager, gia cố logic Atomic và chuẩn hóa PEP8.
"""

import logging
import uuid
from datetime import timedelta
from django.db import models, transaction, IntegrityError
from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _ # noqa: F401
from core.infrastructure.security import decrypt_aes256
from core.managers import TenantAwareManager, TenantScopedModel, organization_id
from core.workflow_transition_policy import WorkflowTransitionPolicy

# Logger cho hệ thống SCMD
logger = logging.getLogger(__name__)

# --- VALIDATORS ---
phone_validator = RegexValidator(
    regex=r'^0\d{9}$',
    message=_("Số điện thoại không hợp lệ. Vui lòng nhập 10 chữ số bắt đầu bằng số 0 (VD: 0912345678).")
)


# --- MANAGERS TỐI ƯU HÓA TRUY VẤN ---
class NhanVienManager(TenantAwareManager):
    """Organization-scoped employee manager safe for read and write paths.

    The default queryset intentionally avoids automatic ``select_related`` on
    nullable profile relations. Django's ``update_or_create()`` internally uses
    ``select_for_update()``; combining that lock with nullable outer joins raises
    ``FOR UPDATE cannot be applied to the nullable side of an outer join`` on
    PostgreSQL. Read paths that need the N+1 guard should opt in explicitly via
    ``with_profile_related()`` or local ``select_related(...)``.
    """

    def get_queryset(self):
        return super().get_queryset()

    def with_profile_related(self):
        return self.get_queryset().select_related('phong_ban', 'chuc_danh', 'user')

    def bulk_create(self, objs, *args, **kwargs):
        """Normalize employee records for bulk inserts.

        bulk_create() bypasses model.save(), so keep the blank-email guard here
        as well to avoid duplicate unique values from empty strings.
        """
        for obj in objs:
            if getattr(obj, "email", None) == "":
                obj.email = None
        return super().bulk_create(objs, *args, **kwargs)


class LichSuCongTacManager(models.Manager):
    """Quản lý các phương thức truy vấn chuyên biệt cho lịch sử công tác."""
    def get_current_position(self, nhan_vien):
        return self.filter(
            nhan_vien=nhan_vien, 
            ngay_ket_thuc__isnull=True
        ).order_by('-ngay_bat_dau').first()


# --- CÁC MODEL CẤU HÌNH HỆ THỐNG ---
class CauHinhMaNhanVien(models.Model):
    tien_to = models.CharField(_("Tiền tố"), max_length=5, default="NV")
    do_dai_so = models.PositiveIntegerField(_("Độ dài phần số"), default=4)
    so_hien_tai = models.PositiveIntegerField(_("Số hiện tại"), default=0)

    class Meta:
        verbose_name = _("Cấu hình Mã nhân viên")
        verbose_name_plural = _("Cấu hình Mã nhân viên")

    def __str__(self):
        return f"{self.tien_to} (Hiện tại: {self.so_hien_tai})"


class ChucDanh(models.Model):
    ten_chuc_danh = models.CharField(_("Tên chức danh"), max_length=100, unique=True)
    mo_ta = models.TextField(_("Mô tả"), blank=True, null=True)
    nhom_quyen = models.ForeignKey(
        Group, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_("Nhóm quyền quản trị")
    )
    
    def __str__(self):
        return self.ten_chuc_danh

    class Meta:
        verbose_name = _("Chức danh")
        verbose_name_plural = _("1. Danh mục Chức danh")

class PhongBan(TenantScopedModel):
    ten_phong_ban = models.CharField(_("Tên phòng ban"), max_length=100, unique=True)
    mo_ta = models.TextField(_("Mô tả"), blank=True, null=True)
    nhom_quyen = models.ForeignKey(
        Group, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Nhóm quyền mặc định")
    )

    objects = TenantAwareManager()
    
    def __str__(self):
        return self.ten_phong_ban

    class Meta:
        verbose_name = _("Phòng ban")
        verbose_name_plural = _("2. Danh mục Phòng ban")


# --- MODEL NHÂN VIÊN (CORE ENTITY) ---
class NhanVien(TenantScopedModel):
    class GioiTinh(models.TextChoices):
        NAM = "M", _("Nam")
        NU = "F", _("Nữ")
        KHAC = "O", _("Khác")
        
    class TrangThaiLamViec(models.TextChoices):
        THU_VIEC = "THUVIEC", _("Thử việc")
        CHINH_THUC = "CHINHTHUC", _("Chính thức")
        TAM_HOAN = "TAMHOAN", _("Tạm hoãn")
        NGHI_VIEC = "NGHIVIEC", _("Đã nghỉ việc")

    class LoaiHopDong(models.TextChoices):
        XAC_DINH_THOI_HAN = "XDTH", _("Xác định thời hạn")
        KHONG_XAC_DINH_THOI_HAN = "KXDTH", _("Không xác định thời hạn")
        THOI_VU = "THOIVU", _("Thời vụ")

    # Liên kết tài khoản
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name="nhan_vien", 
        verbose_name=_("Tài khoản hệ thống")
    )
    
    # Thông tin tổ chức
    phong_ban = models.ForeignKey(PhongBan, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Phòng ban"), related_name="cac_nhan_vien")
    chuc_danh = models.ForeignKey(ChucDanh, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Chức danh"), related_name="cac_nhan_vien")
    ma_nhan_vien = models.CharField(_("Mã số NV"), max_length=20, unique=True, editable=False, db_index=True)
    
    # Thông tin cá nhân
    anh_the = models.ImageField(_("Ảnh thẻ hồ sơ"), upload_to="anh_the/", null=True, blank=True)
    ho_ten = models.CharField(_("Họ và Tên"), max_length=255, db_index=True)
    ngay_sinh = models.DateField(_("Ngày sinh"), null=True, blank=True)
    gioi_tinh = models.CharField(_("Giới tính"), max_length=1, choices=GioiTinh.choices, null=True, blank=True)
    
    # Liên lạc và định danh
    sdt_chinh = models.CharField(
        _("Số điện thoại"), 
        max_length=20,
        validators=[phone_validator],
        db_index=True, 
        null=True, 
        blank=True,
        help_text=_("Định dạng: 0xxxxxxxxx (10 số)")
    )
    fcm_token = models.CharField(
        _("FCM Token"), 
        max_length=255, 
        null=True, 
        blank=True,
        help_text=_("Token định danh thiết bị cho Firebase Cloud Messaging")
    )
    so_cccd = models.CharField(_("Số CCCD/CMND (Encrypted)"), max_length=255, unique=True, null=True, blank=True)
    email = models.EmailField(_("Email cá nhân"), unique=True, null=True, blank=True)
    dia_chi_thuong_tru = models.CharField(_("Địa chỉ thường trú"), max_length=255, blank=True)
    dia_chi_tam_tru = models.CharField(_("Địa chỉ tạm trú"), max_length=255, blank=True)
    nguoi_lien_he_khan_cap = models.CharField(_("Người liên hệ khẩn cấp"), max_length=255, blank=True)
    sdt_khan_cap = models.CharField(_("SĐT khẩn cấp"), max_length=20, blank=True)
    
    # Thông tin công tác
    ngay_vao_lam = models.DateField(_("Ngày vào làm"), null=True, blank=True)
    ngay_nghi_viec = models.DateField(_("Ngày nghỉ việc"), null=True, blank=True)
    trang_thai_lam_viec = models.CharField(
        _("Trạng thái nhân sự"), 
        max_length=50, 
        choices=TrangThaiLamViec.choices, 
        default=TrangThaiLamViec.THU_VIEC
    )
    loai_hop_dong = models.CharField(_("Loại hợp đồng"), max_length=50, choices=LoaiHopDong.choices, blank=True)
    
    # Tài chính
    so_tai_khoan = models.CharField(_("Số tài khoản (Encrypted)"), max_length=255, blank=True)
    ngan_hang = models.CharField(_("Ngân hàng"), max_length=255, blank=True)
    chi_nhanh_ngan_hang = models.CharField(_("Chi nhánh"), max_length=255, blank=True)

    # Manager tùy chỉnh
    objects = NhanVienManager()

    class Meta:
        verbose_name = _("Nhân viên")
        verbose_name_plural = _("3. Danh sách Nhân viên")
        ordering = ['ma_nhan_vien']

    def __str__(self):
        return f"{self.ma_nhan_vien} - {self.ho_ten}"
        
    def _audit_pii_access(self, field_label: str):
        """
        Ghi lại nhật ký truy cập dữ liệu cá nhân nhạy cảm (PII).
        Tuân thủ Section 12.3 - DOCUMENTATION.md.
        """
        from crum import get_current_user, get_current_request
        from main.models import AuditLog

        actor = "SYSTEM/UNKNOWN"
        user = None
        ip = ""
        ua = ""

        try:
            user = get_current_user()
            request = get_current_request()
            
            if user and user.is_authenticated:
                actor = user.username

            if request:
                # Trích xuất IP chính xác (xử lý qua Load Balancer/Proxy)
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
                ua = request.META.get('HTTP_USER_AGENT', '')
        except (ImportError, Exception):
            pass

        # 1. Ghi ra log file (dự phòng cho hệ thống giám sát log tập trung)
        logger.info(
            f"[PII-ACCESS-AUDIT] Actor: {actor} | Action: VIEW | Field: {field_label} | "
            f"Target: {self.ma_nhan_vien} ({self.ho_ten}) | ID: {self.pk}"
        )

        # 2. Lưu vào Database AuditLog (Nguồn sự thật cho báo cáo hậu kiểm)
        try:
            AuditLog.log_access(
                user=user if user and user.is_authenticated else None,
                model_instance=self,
                field_name=field_label,
                tenant_id=getattr(self, 'tenant_id', settings.SCMD_ORGANIZATION_ID),
                ip=ip,
                ua=ua
            )
        except Exception as e:
            logger.error(f"CRITICAL: Failed to save AuditLog for PII access: {str(e)}")

    @property
    def decrypted_cccd(self):
        """Giải mã CCCD khi cần hiển thị (Yêu cầu quyền hạn phù hợp)"""
        self._audit_pii_access("Số CCCD")
        return decrypt_aes256(self.so_cccd)

    @property
    def masked_cccd(self):
        """Hiển thị CCCD dạng che dấu (VD: ********1234)"""
        val = self.decrypted_cccd
        return f"{'*' * (len(val)-4)}{val[-4:]}" if val else "-"

    @property
    def masked_stk(self):
        """Hiển thị Số tài khoản dạng che dấu"""
        val = self.decrypted_stk
        return f"{'*' * (len(val)-3)}{val[-3:]}" if val else "-"

    @property
    def decrypted_stk(self):
        """Giải mã số tài khoản ngân hàng"""
        self._audit_pii_access("Số tài khoản")
        return decrypt_aes256(self.so_tai_khoan)
        
    @property
    def avatar_url(self):
        """Trả về URL ảnh thẻ hoặc ảnh mặc định cho giao diện Jazzmin."""
        try:
            if self.anh_the and hasattr(self.anh_the, 'url'):
                return self.anh_the.url
        except Exception as e:
            logger.warning(f"Lỗi truy cập URL ảnh thẻ của {self.ma_nhan_vien}: {str(e)}")
        return f"{settings.STATIC_URL}img/default-avatar.png"

    def avatar_tag(self):
        """Thumbnail hiển thị trong trang danh sách Admin."""
        return mark_safe(f'<img src="{self.avatar_url}" width="50" height="50" style="border-radius:50%; object-fit:cover; border: 1px solid #ddd;" />')
    avatar_tag.short_description = _('Ảnh hồ sơ')

<<<<<<< HEAD
    def get_active_labor_contract(self, day=None):
        """Trả về HĐLĐ có hiệu lực từ model HopDongLaoDong, không dùng loai_hop_dong legacy."""
        day = day or timezone.localdate()
        return self.cac_hop_dong_lao_dong.filter(
            trang_thai__in=HopDongLaoDong.ACTIVE_CONTRACT_STATUSES,
            ngay_hieu_luc__lte=day,
        ).filter(
            models.Q(ngay_het_han__isnull=True) | models.Q(ngay_het_han__gte=day)
        ).order_by("-ngay_hieu_luc").first()

    def has_active_labor_contract(self, day=None):
        """SSOT kiểm tra HĐLĐ active: field loai_hop_dong trên NhanVien không đủ."""
        return self.get_active_labor_contract(day=day) is not None

    def save(self, *args, **kwargs):
        """Xử lý logic tự động hóa trước khi lưu."""
        self.tenant_id = organization_id()
        if self.email == "":
            self.email = None
=======
    def save(self, *args, **kwargs):
        """Xử lý logic tự động hóa trước khi lưu."""
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        # Sinh mã nhân viên nếu chưa có (Trường hợp tạo từ Signal hoặc Admin)
        if not self.ma_nhan_vien:
            try:
                with transaction.atomic():
                    # Khóa bản ghi cấu hình để tránh trùng mã khi concurrency cao (Race Condition protection)
                    config = CauHinhMaNhanVien.objects.select_for_update().first()
                    if not config:
                        config = CauHinhMaNhanVien.objects.create(tien_to="NV", do_dai_so=4, so_hien_tai=0)
                    
                    config.so_hien_tai += 1
                    config.save()
                    
                    self.ma_nhan_vien = f"{config.tien_to}{str(config.so_hien_tai).zfill(config.do_dai_so)}"
            except Exception as e:
                logger.error(f"Lỗi tự động sinh mã nhân viên tại model layer: {str(e)}")

        super().save(*args, **kwargs)


<<<<<<< HEAD
ACTIVE_EMPLOYEE_STATUSES = [
    NhanVien.TrangThaiLamViec.CHINH_THUC,
    NhanVien.TrangThaiLamViec.THU_VIEC,
]


class HopDongLaoDong(TenantScopedModel):
    """Hồ sơ nguồn cho vòng đời Hợp đồng lao động của nhân viên.

    ``NhanVien.loai_hop_dong`` chỉ còn là trường legacy/compatibility để không
    phá các màn hình cũ. Hợp đồng lao động có hiệu lực phải được xác định từ
    model này: trạng thái, ngày hiệu lực, ngày hết hạn và file/bằng chứng ký kết.
    """

    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", _("Nháp")
        PENDING_SIGNATURE = "PENDING_SIGNATURE", _("Chờ ký")
        ACTIVE = "ACTIVE", _("Đã ký/hiệu lực")
        EXPIRING = "EXPIRING", _("Sắp hết hạn")
        EXPIRED = "EXPIRED", _("Hết hạn")
        TERMINATED = "TERMINATED", _("Chấm dứt")

    class NguonHoSo(models.TextChoices):
        HR_ADMIN = "HR_ADMIN", _("Nhập từ HR Admin")
        IMPORT = "IMPORT", _("Import dữ liệu")
        LEGACY = "LEGACY", _("Legacy/đối soát cũ")
        OTHER = "OTHER", _("Nguồn khác")

    ACTIVE_CONTRACT_STATUSES = (TrangThai.ACTIVE, TrangThai.EXPIRING)
    ALLOWED_STATUS_TRANSITIONS = {
        TrangThai.DRAFT: {TrangThai.PENDING_SIGNATURE, TrangThai.TERMINATED},
        TrangThai.PENDING_SIGNATURE: {TrangThai.ACTIVE, TrangThai.TERMINATED},
        TrangThai.ACTIVE: {TrangThai.EXPIRING, TrangThai.EXPIRED, TrangThai.TERMINATED},
        TrangThai.EXPIRING: {TrangThai.ACTIVE, TrangThai.EXPIRED, TrangThai.TERMINATED},
        TrangThai.EXPIRED: {TrangThai.TERMINATED},
        TrangThai.TERMINATED: set(),
    }

    nhan_vien = models.ForeignKey(
        NhanVien,
        on_delete=models.CASCADE,
        related_name="cac_hop_dong_lao_dong",
        verbose_name=_("Nhân viên"),
    )
    so_hop_dong = models.CharField(_("Số hợp đồng"), max_length=64, db_index=True)
    loai_hop_dong = models.CharField(
        _("Loại hợp đồng"),
        max_length=50,
        choices=NhanVien.LoaiHopDong.choices,
        help_text=_("SSOT loại hợp đồng cho hồ sơ HĐLĐ; không dùng NhanVien.loai_hop_dong để xác định hiệu lực."),
    )
    ngay_ky = models.DateField(_("Ngày ký"), null=True, blank=True)
    ngay_hieu_luc = models.DateField(_("Ngày hiệu lực"), db_index=True)
    ngay_het_han = models.DateField(
        _("Ngày hết hạn"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Để trống với hợp đồng không xác định thời hạn."),
    )
    trang_thai = models.CharField(
        _("Trạng thái"),
        max_length=32,
        choices=TrangThai.choices,
        default=TrangThai.DRAFT,
        db_index=True,
    )
    muc_luong_co_ban = models.DecimalField(
        _("Mức lương cơ bản"),
        max_digits=14,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_("Giá trị tham chiếu trên hợp đồng. Payroll hiện tại không tự động lấy từ trường này."),
    )
    phu_cap = models.DecimalField(
        _("Phụ cấp"),
        max_digits=14,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_("Tổng phụ cấp tham chiếu trên hợp đồng; không tự động ghi đè cấu hình lương hiện tại."),
    )
    file_hop_dong = models.FileField(
        _("File hợp đồng"),
        upload_to="hop_dong_lao_dong/%Y/%m/",
        null=True,
        blank=True,
    )
    nguon_ho_so = models.CharField(
        _("Nguồn hồ sơ"),
        max_length=32,
        choices=NguonHoSo.choices,
        default=NguonHoSo.HR_ADMIN,
    )
    nguoi_duyet = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_hop_dong_lao_dong_da_duyet",
        verbose_name=_("Người duyệt/ký xác nhận"),
    )
    ngay_duyet = models.DateTimeField(_("Thời điểm duyệt/ký xác nhận"), null=True, blank=True)
    ghi_chu = models.TextField(_("Ghi chú"), blank=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = _("Hợp đồng lao động")
        verbose_name_plural = _("4. Hợp đồng lao động")
        ordering = ["-ngay_hieu_luc", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "ngay_het_han"], name="usr_hdld_tenant_status_exp_idx"),
            models.Index(fields=["tenant_id", "nhan_vien", "trang_thai"], name="usr_hdld_tenant_staff_stat_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "so_hop_dong"], name="uq_hdld_tenant_so_hop_dong"),
        ]

    def __str__(self):
        return f"{self.so_hop_dong} - {self.nhan_vien}"

    def clean(self):
        super().clean()
        if self.ngay_het_han and self.ngay_hieu_luc and self.ngay_het_han < self.ngay_hieu_luc:
            raise ValidationError({"ngay_het_han": _("Ngày hết hạn không được trước ngày hiệu lực.")})
        if self.loai_hop_dong == NhanVien.LoaiHopDong.XAC_DINH_THOI_HAN and not self.ngay_het_han:
            raise ValidationError({"ngay_het_han": _("Hợp đồng xác định thời hạn phải có ngày hết hạn.")})

    def is_effective_on(self, day=None):
        day = day or timezone.localdate()
        if self.trang_thai not in self.ACTIVE_CONTRACT_STATUSES:
            return False
        if self.ngay_hieu_luc and self.ngay_hieu_luc > day:
            return False
        if self.ngay_het_han and self.ngay_het_han < day:
            return False
        return True

    def is_expiring_within(self, days=30, today=None):
        today = today or timezone.localdate()
        if self.trang_thai not in self.ACTIVE_CONTRACT_STATUSES:
            return False
        if not self.ngay_het_han:
            return False
        return today <= self.ngay_het_han <= today + timedelta(days=days)

    def is_expired_on(self, day=None):
        day = day or timezone.localdate()
        return bool(self.ngay_het_han and self.ngay_het_han < day)

    def record_status_transition(self, *, actor=None, old_status=None, new_status=None, note=""):
        old_status = old_status if old_status is not None else None
        new_status = new_status if new_status is not None else self.trang_thai
        if old_status == new_status:
            return None

        try:
            from main.models import AuditLog

            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="users",
                model_name="HopDongLaoDong",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                changes={
                    "status_transition": {
                        "old": old_status,
                        "new": new_status,
                    },
                    "so_hop_dong": self.so_hop_dong,
                    "nhan_vien_id": self.nhan_vien_id,
                    "ma_nhan_vien": getattr(self.nhan_vien, "ma_nhan_vien", ""),
                },
                note=note or "HR labor contract status transition",
            )
        except Exception as exc:
            logger.error("Failed to audit HopDongLaoDong status transition: %s", exc)
            return None

    def transition_status(self, new_status, *, actor=None, note=""):
        """Chuyển trạng thái có audit log, không tự động đổi trạng thái nhân viên."""
        old_status = self.trang_thai
        WorkflowTransitionPolicy.validate_transition(type(self).__name__, old_status, new_status, self.ALLOWED_STATUS_TRANSITIONS)
        self.trang_thai = new_status
        update_fields = ["trang_thai", "updated_at"]
        if new_status in self.ACTIVE_CONTRACT_STATUSES and actor and not self.nguoi_duyet_id:
            self.nguoi_duyet = actor
            self.ngay_duyet = timezone.now()
            update_fields.extend(["nguoi_duyet", "ngay_duyet"])
        self.save(update_fields=update_fields)
        self.record_status_transition(actor=actor, old_status=old_status, new_status=new_status, note=note)


class PhuLucHopDongLaoDong(TenantScopedModel):
    """Phụ lục của HĐLĐ, tách riêng để không nhồi vòng đời phụ lục vào hợp đồng gốc."""

    hop_dong = models.ForeignKey(
        HopDongLaoDong,
        on_delete=models.CASCADE,
        related_name="cac_phu_luc",
        verbose_name=_("Hợp đồng lao động"),
    )
    so_phu_luc = models.CharField(_("Số phụ lục"), max_length=64)
    ngay_ky = models.DateField(_("Ngày ký"), null=True, blank=True)
    ngay_hieu_luc = models.DateField(_("Ngày hiệu lực"), null=True, blank=True)
    ngay_het_han = models.DateField(_("Ngày hết hạn"), null=True, blank=True)
    noi_dung = models.TextField(_("Nội dung phụ lục"), blank=True)
    file_phu_luc = models.FileField(_("File phụ lục"), upload_to="phu_luc_hop_dong_lao_dong/%Y/%m/", null=True, blank=True)
    ghi_chu = models.TextField(_("Ghi chú"), blank=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = _("Phụ lục hợp đồng lao động")
        verbose_name_plural = _("Phụ lục hợp đồng lao động")
        ordering = ["-ngay_hieu_luc", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "hop_dong", "so_phu_luc"], name="uq_plhdld_tenant_contract_no"),
        ]

    def __str__(self):
        return f"{self.so_phu_luc} - {self.hop_dong.so_hop_dong}"

    def clean(self):
        super().clean()
        if self.ngay_het_han and self.ngay_hieu_luc and self.ngay_het_han < self.ngay_hieu_luc:
            raise ValidationError({"ngay_het_han": _("Ngày hết hạn phụ lục không được trước ngày hiệu lực.")})



class DonNghiPhep(TenantScopedModel):
    """Hồ sơ nguồn cho nghiệp vụ nghỉ phép/nghỉ không lương.

    Không dùng Báo cáo/Đề xuất generic để thay thế vì nghỉ phép có vòng đời,
    ngày hiệu lực, trạng thái phê duyệt và ảnh hưởng trực tiếp tới chấm công/lương.
    Patch này chỉ tạo SSOT hồ sơ; payroll hiện tại chưa tự động khấu trừ theo model này.
    """

    class LoaiNghi(models.TextChoices):
        PHEP_NAM = "PHEP_NAM", _("Phép năm")
        KHONG_LUONG = "KHONG_LUONG", _("Nghỉ không lương")
        OM_DAU = "OM_DAU", _("Ốm đau")
        VIEC_RIENG = "VIEC_RIENG", _("Việc riêng")
        KHAC = "KHAC", _("Khác")

    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", _("Nháp")
        PENDING_APPROVAL = "PENDING_APPROVAL", _("Chờ duyệt")
        APPROVED = "APPROVED", _("Đã duyệt")
        REJECTED = "REJECTED", _("Từ chối")
        CANCELLED = "CANCELLED", _("Đã hủy")

    ACTIVE_APPROVAL_STATUSES = (TrangThai.PENDING_APPROVAL, TrangThai.APPROVED)
    ALLOWED_STATUS_TRANSITIONS = {
        TrangThai.DRAFT: {TrangThai.PENDING_APPROVAL, TrangThai.CANCELLED},
        TrangThai.PENDING_APPROVAL: {TrangThai.APPROVED, TrangThai.REJECTED, TrangThai.CANCELLED},
        TrangThai.APPROVED: {TrangThai.CANCELLED},
        TrangThai.REJECTED: set(),
        TrangThai.CANCELLED: set(),
    }

    nhan_vien = models.ForeignKey(
        NhanVien,
        on_delete=models.CASCADE,
        related_name="cac_don_nghi_phep",
        verbose_name=_("Nhân viên"),
    )
    ma_don = models.CharField(_("Mã đơn"), max_length=64, db_index=True)
    loai_nghi = models.CharField(_("Loại nghỉ"), max_length=32, choices=LoaiNghi.choices, default=LoaiNghi.PHEP_NAM)
    tu_ngay = models.DateField(_("Từ ngày"), db_index=True)
    den_ngay = models.DateField(_("Đến ngày"), db_index=True)
    so_ngay = models.DecimalField(_("Số ngày"), max_digits=5, decimal_places=2, default=1, validators=[MinValueValidator(0)])
    trang_thai = models.CharField(_("Trạng thái"), max_length=32, choices=TrangThai.choices, default=TrangThai.DRAFT, db_index=True)
    ly_do = models.TextField(_("Lý do"), blank=True)
    file_minh_chung = models.FileField(_("File minh chứng"), upload_to="don_nghi_phep/%Y/%m/", null=True, blank=True)
    nguoi_duyet = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_don_nghi_phep_da_duyet",
        verbose_name=_("Người duyệt"),
    )
    ngay_duyet = models.DateTimeField(_("Thời điểm duyệt"), null=True, blank=True)
    ghi_chu = models.TextField(_("Ghi chú"), blank=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = _("Đơn nghỉ phép")
        verbose_name_plural = _("5. Đơn nghỉ phép")
        ordering = ["-tu_ngay", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "tu_ngay"], name="usr_leave_tenant_stat_from_idx"),
            models.Index(fields=["tenant_id", "nhan_vien", "tu_ngay"], name="usr_leave_t_staff_from_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "ma_don"], name="uq_leave_tenant_code"),
        ]

    def __str__(self):
        return f"{self.ma_don} - {self.nhan_vien}"

    def clean(self):
        super().clean()
        if self.den_ngay and self.tu_ngay and self.den_ngay < self.tu_ngay:
            raise ValidationError({"den_ngay": _("Ngày kết thúc nghỉ không được trước ngày bắt đầu.")})
        if self.so_ngay is not None and self.so_ngay <= 0:
            raise ValidationError({"so_ngay": _("Số ngày nghỉ phải lớn hơn 0.")})

    def record_status_transition(self, *, actor=None, old_status=None, new_status=None, note=""):
        new_status = new_status if new_status is not None else self.trang_thai
        if old_status == new_status:
            return None
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="users",
                model_name="DonNghiPhep",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "HR leave request status transition",
                changes={"status_transition": {"old": old_status, "new": new_status}, "ma_don": self.ma_don, "nhan_vien_id": self.nhan_vien_id},
            )
        except Exception as exc:
            logger.error("Failed to audit DonNghiPhep status transition: %s", exc)
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


class QuyetDinhNghiViec(TenantScopedModel):
    """Hồ sơ nguồn cho quyết định nghỉ việc/offboarding.

    Model này không tự động đổi ``NhanVien.trang_thai_lam_viec`` hoặc
    ``NhanVien.ngay_nghi_viec``. Việc đổi trạng thái nhân viên cần rule riêng và
    phê duyệt rõ ràng để tránh phá payroll/chấm công hiện hữu.
    """

    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", _("Nháp")
        PENDING_APPROVAL = "PENDING_APPROVAL", _("Chờ duyệt")
        APPROVED = "APPROVED", _("Đã duyệt")
        EFFECTIVE = "EFFECTIVE", _("Có hiệu lực")
        CANCELLED = "CANCELLED", _("Đã hủy")

    ALLOWED_STATUS_TRANSITIONS = {
        TrangThai.DRAFT: {TrangThai.PENDING_APPROVAL, TrangThai.CANCELLED},
        TrangThai.PENDING_APPROVAL: {TrangThai.APPROVED, TrangThai.CANCELLED},
        TrangThai.APPROVED: {TrangThai.EFFECTIVE, TrangThai.CANCELLED},
        TrangThai.EFFECTIVE: set(),
        TrangThai.CANCELLED: set(),
    }

    nhan_vien = models.ForeignKey(
        NhanVien,
        on_delete=models.CASCADE,
        related_name="cac_quyet_dinh_nghi_viec",
        verbose_name=_("Nhân viên"),
    )
    so_quyet_dinh = models.CharField(_("Số quyết định"), max_length=64, db_index=True)
    ngay_quyet_dinh = models.DateField(_("Ngày quyết định"), default=timezone.localdate)
    ngay_hieu_luc = models.DateField(_("Ngày hiệu lực"), db_index=True)
    ly_do_nghi = models.TextField(_("Lý do nghỉ việc"), blank=True)
    trang_thai = models.CharField(_("Trạng thái"), max_length=32, choices=TrangThai.choices, default=TrangThai.DRAFT, db_index=True)
    file_quyet_dinh = models.FileField(_("File quyết định"), upload_to="quyet_dinh_nghi_viec/%Y/%m/", null=True, blank=True)
    nguoi_duyet = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_quyet_dinh_nghi_viec_da_duyet",
        verbose_name=_("Người duyệt"),
    )
    ngay_duyet = models.DateTimeField(_("Thời điểm duyệt"), null=True, blank=True)
    ghi_chu = models.TextField(_("Ghi chú"), blank=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = _("Quyết định nghỉ việc")
        verbose_name_plural = _("6. Quyết định nghỉ việc")
        ordering = ["-ngay_hieu_luc", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "ngay_hieu_luc"], name="usr_exit_tenant_stat_eff_idx"),
            models.Index(fields=["tenant_id", "nhan_vien", "trang_thai"], name="usr_exit_tenant_staff_stat_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "so_quyet_dinh"], name="uq_exit_tenant_decision_no"),
        ]

    def __str__(self):
        return f"{self.so_quyet_dinh} - {self.nhan_vien}"

    def clean(self):
        super().clean()
        if self.ngay_quyet_dinh and self.ngay_hieu_luc and self.ngay_hieu_luc < self.ngay_quyet_dinh:
            raise ValidationError({"ngay_hieu_luc": _("Ngày hiệu lực không được trước ngày quyết định.")})

    def record_status_transition(self, *, actor=None, old_status=None, new_status=None, note=""):
        new_status = new_status if new_status is not None else self.trang_thai
        if old_status == new_status:
            return None
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="users",
                model_name="QuyetDinhNghiViec",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "HR offboarding decision status transition",
                changes={"status_transition": {"old": old_status, "new": new_status}, "so_quyet_dinh": self.so_quyet_dinh, "nhan_vien_id": self.nhan_vien_id},
            )
        except Exception as exc:
            logger.error("Failed to audit QuyetDinhNghiViec status transition: %s", exc)
            return None

    def transition_status(self, new_status, *, actor=None, note=""):
        old_status = self.trang_thai
        WorkflowTransitionPolicy.validate_transition(type(self).__name__, old_status, new_status, self.ALLOWED_STATUS_TRANSITIONS)
        self.trang_thai = new_status
        update_fields = ["trang_thai", "updated_at"]
        if new_status in (self.TrangThai.APPROVED, self.TrangThai.EFFECTIVE) and actor and not self.nguoi_duyet_id:
            self.nguoi_duyet = actor
            self.ngay_duyet = timezone.now()
            update_fields.extend(["nguoi_duyet", "ngay_duyet"])
        self.save(update_fields=update_fields)
        return self.record_status_transition(actor=actor, old_status=old_status, new_status=new_status, note=note)


class OffboardingChecklist(TenantScopedModel):
    """Checklist bàn giao khi nghỉ việc, tách khỏi NhanVien để có vòng đời riêng."""

    quyet_dinh = models.OneToOneField(
        QuyetDinhNghiViec,
        on_delete=models.CASCADE,
        related_name="checklist_ban_giao",
        verbose_name=_("Quyết định nghỉ việc"),
    )
    thu_hoi_dong_phuc = models.BooleanField(_("Thu hồi đồng phục/công cụ"), default=False)
    ban_giao_tai_san = models.BooleanField(_("Bàn giao tài sản"), default=False)
    khoa_tai_khoan = models.BooleanField(_("Khóa/thu hồi tài khoản"), default=False)
    chot_cong = models.BooleanField(_("Chốt công"), default=False)
    quyet_toan_luong = models.BooleanField(_("Quyết toán lương"), default=False)
    hoan_tat = models.BooleanField(_("Hoàn tất offboarding"), default=False, db_index=True)
    nguoi_xac_nhan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_checklist_offboarding_xac_nhan",
        verbose_name=_("Người xác nhận"),
    )
    ngay_hoan_tat = models.DateTimeField(_("Thời điểm hoàn tất"), null=True, blank=True)
    ghi_chu = models.TextField(_("Ghi chú"), blank=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = _("Checklist nghỉ việc")
        verbose_name_plural = _("Checklist nghỉ việc")
        ordering = ["hoan_tat", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "hoan_tat"], name="usr_offboard_tenant_done_idx"),
        ]

    def __str__(self):
        return f"Checklist - {self.quyet_dinh}"

    @property
    def is_ready_to_complete(self):
        return all([
            self.thu_hoi_dong_phuc,
            self.ban_giao_tai_san,
            self.khoa_tai_khoan,
            self.chot_cong,
            self.quyet_toan_luong,
        ])

    def mark_completed(self, *, actor=None, note=""):
        if not self.is_ready_to_complete:
            raise ValidationError(_("Chưa đủ các bước bàn giao để hoàn tất offboarding."))
        try:
            from inventory.application.asset_recovery_use_cases import GetEmployeeOutstandingAssetsUseCase
            if not GetEmployeeOutstandingAssetsUseCase.can_complete_offboarding(
                nhan_vien=self.quyet_dinh.nhan_vien,
                tenant_id=getattr(self, "tenant_id", None),
            ):
                raise ValidationError(_("Nhân viên còn tài sản chưa thu hồi hoặc biên bản mất/hỏng chưa xử lý; không được hoàn tất offboarding."))
        except ImportError:
            # Compatibility guard for migration/runtime bootstrapping; production
            # code with inventory installed must enforce the Phase F source record.
            pass
        self.hoan_tat = True
        self.nguoi_xac_nhan = actor if actor and getattr(actor, "is_authenticated", False) else self.nguoi_xac_nhan
        self.ngay_hoan_tat = timezone.now()
        self.save(update_fields=["hoan_tat", "nguoi_xac_nhan", "ngay_hoan_tat", "updated_at"])
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="users",
                model_name="OffboardingChecklist",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "HR offboarding checklist completed",
                changes={"hoan_tat": True, "quyet_dinh_id": self.quyet_dinh_id},
            )
        except Exception as exc:
            logger.error("Failed to audit OffboardingChecklist completion: %s", exc)
            return None


class HoSoBaoHiem(TenantScopedModel):
    """Hồ sơ bảo hiểm của nhân viên, không dùng ghi chú/field rời trên NhanVien."""

    class LoaiBaoHiem(models.TextChoices):
        BHXH = "BHXH", _("BHXH")
        BHYT = "BHYT", _("BHYT")
        BHTN = "BHTN", _("BHTN")
        BAO_HIEM_KHAC = "BAO_HIEM_KHAC", _("Bảo hiểm khác")

    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", _("Nháp")
        ACTIVE = "ACTIVE", _("Đang hiệu lực")
        PAUSED = "PAUSED", _("Tạm dừng")
        TERMINATED = "TERMINATED", _("Đã chấm dứt")

    ACTIVE_STATUSES = (TrangThai.ACTIVE,)
    ALLOWED_STATUS_TRANSITIONS = {
        TrangThai.DRAFT: {TrangThai.ACTIVE, TrangThai.PAUSED, TrangThai.TERMINATED},
        TrangThai.ACTIVE: {TrangThai.PAUSED, TrangThai.TERMINATED},
        TrangThai.PAUSED: {TrangThai.ACTIVE, TrangThai.TERMINATED},
        TrangThai.TERMINATED: set(),
    }

    nhan_vien = models.ForeignKey(
        NhanVien,
        on_delete=models.CASCADE,
        related_name="cac_ho_so_bao_hiem",
        verbose_name=_("Nhân viên"),
    )
    so_bao_hiem = models.CharField(_("Số sổ/thẻ bảo hiểm"), max_length=64, db_index=True)
    loai_bao_hiem = models.CharField(_("Loại bảo hiểm"), max_length=32, choices=LoaiBaoHiem.choices, default=LoaiBaoHiem.BHXH)
    ngay_tham_gia = models.DateField(_("Ngày tham gia"), db_index=True)
    ngay_ket_thuc = models.DateField(_("Ngày kết thúc"), null=True, blank=True, db_index=True)
    trang_thai = models.CharField(_("Trạng thái"), max_length=32, choices=TrangThai.choices, default=TrangThai.DRAFT, db_index=True)
    file_ho_so = models.FileField(_("File hồ sơ bảo hiểm"), upload_to="ho_so_bao_hiem/%Y/%m/", null=True, blank=True)
    nguoi_duyet = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_ho_so_bao_hiem_da_duyet",
        verbose_name=_("Người duyệt"),
    )
    ngay_duyet = models.DateTimeField(_("Thời điểm duyệt"), null=True, blank=True)
    ghi_chu = models.TextField(_("Ghi chú"), blank=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = _("Hồ sơ bảo hiểm")
        verbose_name_plural = _("7. Hồ sơ bảo hiểm")
        ordering = ["-ngay_tham_gia", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "ngay_ket_thuc"], name="usr_ins_tenant_stat_end_idx"),
            models.Index(fields=["tenant_id", "nhan_vien", "loai_bao_hiem"], name="usr_ins_tenant_staff_type_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "nhan_vien", "loai_bao_hiem", "so_bao_hiem"], name="uq_ins_tenant_staff_type_no"),
        ]

    def __str__(self):
        return f"{self.so_bao_hiem} - {self.nhan_vien}"

    def clean(self):
        super().clean()
        if self.ngay_ket_thuc and self.ngay_tham_gia and self.ngay_ket_thuc < self.ngay_tham_gia:
            raise ValidationError({"ngay_ket_thuc": _("Ngày kết thúc bảo hiểm không được trước ngày tham gia.")})

    def is_active_on(self, day=None):
        day = day or timezone.localdate()
        if self.trang_thai not in self.ACTIVE_STATUSES:
            return False
        if self.ngay_tham_gia and self.ngay_tham_gia > day:
            return False
        if self.ngay_ket_thuc and self.ngay_ket_thuc < day:
            return False
        return True

    def record_status_transition(self, *, actor=None, old_status=None, new_status=None, note=""):
        new_status = new_status if new_status is not None else self.trang_thai
        if old_status == new_status:
            return None
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="users",
                model_name="HoSoBaoHiem",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "HR insurance profile status transition",
                changes={"status_transition": {"old": old_status, "new": new_status}, "so_bao_hiem": self.so_bao_hiem, "nhan_vien_id": self.nhan_vien_id},
            )
        except Exception as exc:
            logger.error("Failed to audit HoSoBaoHiem status transition: %s", exc)
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

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
# --- MODEL HỖ TRỢ HỒ SƠ ---
class HocVan(models.Model):
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="cac_hoc_van")
    truong_dao_tao = models.CharField(_("Trường đào tạo"), max_length=255)
    chuyen_nganh = models.CharField(_("Chuyên ngành"), max_length=255)
    trinh_do = models.CharField(_("Trình độ"), max_length=100)
    tu_ngay = models.DateField(_("Từ ngày"))
    den_ngay = models.DateField(_("Đến ngày"), null=True, blank=True)
    
    class Meta:
        verbose_name = _("Học vấn")
        verbose_name_plural = _("Quá trình Học vấn")


class BangCapChungChi(models.Model):
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="cac_bang_cap")
    ten_bang_cap = models.CharField(_("Tên bằng cấp"), max_length=255)
    noi_cap = models.CharField(_("Nơi cấp"), max_length=255)
    ngay_cap = models.DateField(_("Ngày cấp"))
    ngay_het_han = models.DateField(_("Ngày hết hạn"), null=True, blank=True)
    file_dinh_kem = models.FileField(_("File đính kèm"), upload_to="bang_cap/", null=True, blank=True)

    class Meta:
        verbose_name = _("Bằng cấp")
        verbose_name_plural = _("Bằng cấp & Chứng chỉ")


<<<<<<< HEAD
class LichSuCongTac(TenantScopedModel):
=======
class LichSuCongTac(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="cac_lich_su_cong_tac")
    muc_tieu = models.ForeignKey("clients.MucTieu", on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Mục tiêu bảo vệ"))
    chuc_danh_kiem_nhiem = models.ForeignKey(ChucDanh, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Chức danh kiêm nhiệm"))
    quan_ly_truc_tiep = models.ForeignKey(NhanVien, on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_nhan_vien_cap_duoi", verbose_name=_("Quản lý trực tiếp"))
    ngay_bat_dau = models.DateField(_("Ngày bắt đầu"), db_index=True)
    ngay_ket_thuc = models.DateField(_("Ngày kết thúc"), null=True, blank=True)
    
<<<<<<< HEAD
    objects = TenantAwareMa