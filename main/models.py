# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: main/models.py
Author: Senior Software Architect
Version: v2.0.0 (Pro Edition)
Description: He thong Audit Log tap trung cho SCMD Pro.
             Tuan thu Nghi dinh 13/2023/ND-CP ve bao ve du lieu ca nhan.
"""

import uuid
import hashlib
import json
from django.db import models
from django.core.exceptions import ValidationError
from main.company_info import invalidate_company_info_cache
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from core.managers import TenantAwareManager, TenantScopedModel


class AuditLogQuerySet(models.QuerySet):
    """Append-only queryset guard for AuditLog.

    Instance-level ``save()``/``delete()`` guards do not catch bulk queryset
    mutation APIs. Block them at the default manager/queryset layer so normal
    ORM callers cannot rewrite or remove audit history accidentally.
    DB-level privileges remain the final protection for direct SQL.
    """

    def update(self, *args, **kwargs):
        raise ValidationError(
            _("AuditLog là append-only. Không được cập nhật hàng loạt bản ghi audit.")
        )

    def delete(self, *args, **kwargs):
        raise ValidationError(
            _("AuditLog là append-only. Không được xóa hàng loạt bản ghi audit.")
        )


class AuditLogManager(models.Manager.from_queryset(AuditLogQuerySet)):
    use_in_migrations = False


class AuditLog(models.Model):
    """
    Source of Truth (SSOT) cho mọi biến động dữ liệu nhạy cảm và thực thi nghiệp vụ quan trọng.
    Thiết kế theo chuẩn Security by Design nhằm mục đích hậu kiểm và bảo mật.
    """
    class Action(models.TextChoices):
        CREATE = 'CREATE', _('Tạo mới')
        UPDATE = 'UPDATE', _('Cập nhật')
        DELETE = 'DELETE', _('Xóa')
        ACCESS = 'ACCESS', _('Truy cập dữ liệu nhạy cảm')
        EXECUTE = 'EXECUTE', _('Thực thi nghiệp vụ')
        LOGIN = 'LOGIN', _('Đăng nhập')

    objects = AuditLogManager()

    tenant_id = models.UUIDField(
        _("Tenant ID"), 
        db_index=True,
        editable=False,
        null=True
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_("Người thực hiện")
    )
    action = models.CharField(_("Hành động"), max_length=20, choices=Action.choices)
    module = models.CharField(_("Phân hệ"), max_length=50, help_text="VD: Operations, Accounting, HR")
    model_name = models.CharField(_("Tên Model"), max_length=100)
    object_id = models.CharField(_("ID đối tượng"), max_length=100, null=True, blank=True)
    
    # Lưu trữ delta thay đổi (Old vs New)
    changes = models.JSONField(_("Thay đổi chi tiết"), null=True, blank=True)
    
    # Thông tin định danh truy cập
    ip_address = models.GenericIPAddressField(_("Địa chỉ IP"), null=True, blank=True)
    user_agent = models.TextField(_("Thông tin thiết bị"), null=True, blank=True)
    
    timestamp = models.DateTimeField(_("Thời điểm"), auto_now_add=True, db_index=True)
    status = models.CharField(_("Trạng thái"), max_length=20, default='SUCCESS')
    checksum = models.CharField(_("Mã xác thực nội dung"), max_length=64, editable=False, null=True)
    note = models.TextField(_("Ghi chú/Lý do"), blank=True)

    class Meta:
        verbose_name = _("Nhật ký hệ thống")
        verbose_name_plural = _("Nhật ký hệ thống (Audit Log)")
        ordering = ['-timestamp']

    def generate_checksum(self):
        """Tạo mã băm bảo vệ tính toàn vẹn của bản ghi log."""
        # Sử dụng định dạng thời gian chuẩn hóa không có microsecond để đảm bảo tính ổn định giữa Memory và DB
        ts_str = self.timestamp.strftime('%Y-%m-%dT%H:%M:%S') if self.timestamp else "None"
        user_id_val = getattr(self, "user_id", "None")
        content = (
            f"{self.tenant_id}-{user_id_val}-{self.action}-{self.model_name}-"
            f"{self.object_id}-{json.dumps(self.changes or {}, sort_keys=True, ensure_ascii=False)}-{ts_str}"
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError(
                _("AuditLog là append-only. Không được cập nhật bản ghi audit đã tạo.")
            )

        if not self.timestamp:
            # Làm tròn về giây để tránh sai lệch độ chính xác giữa Python và Database (Operational Truth)
            self.timestamp = timezone.now().replace(microsecond=0)

        self.tenant_id = getattr(settings, 'SCMD_ORGANIZATION_ID', self.tenant_id)
        self.checksum = self.generate_checksum()
            
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            _("AuditLog là append-only. Không được xóa bản ghi audit đã tạo.")
        )

    @classmethod
    def log_access(cls, user, model_instance, field_name, tenant_id, ip="", ua=""):
        return cls.objects.create(
            user=user,
            tenant_id=tenant_id,
            action=cls.Action.ACCESS,
            module=model_instance._meta.app_label,
            model_name=model_instance._meta.model_name,
            object_id=str(model_instance.pk),
            note=f"Truy cập trường nhạy cảm: {field_name}",
            ip_address=ip,
            user_agent=ua,
        )


class WorkerHeartbeat(models.Model):
    """
    Single SSOT for Celery worker health monitoring.
    """

    tenant_id = models.UUIDField(
        _("Tenant ID"),
        db_index=True,
        default=uuid.uuid4,
        editable=False,
    )
    hostname = models.CharField(_("Tên Worker"), max_length=255, unique=True)
    last_ping = models.DateTimeField(_("Lần cuối phản hồi"), auto_now=True)
    is_active = models.BooleanField(_("Đang hoạt động"), default=True)

    class Meta:
        verbose_name = _("Nhịp tim hệ thống")
        verbose_name_plural = _("Giám sát Workers (Heartbeat)")



class CompanyInfo(TenantScopedModel):
    """
    Single source of truth for company/legal information printed on payroll,
    employee profiles, contracts, inventory forms and other exported documents.
    SCMD Pro is single-organization; keep exactly one active profile per org.
    """

    ten_cong_ty = models.CharField(_("Tên công ty/đơn vị"), max_length=255)
    ten_phap_ly = models.CharField(
        _("Tên pháp lý đầy đủ"),
        max_length=255,
        blank=True,
        help_text=_("Nếu bỏ trống, hệ thống dùng Tên công ty/đơn vị trên mẫu biểu."),
    )
    ma_so_thue = models.CharField(_("Mã số thuế"), max_length=32, blank=True)
    dia_chi = models.CharField(_("Địa chỉ trụ sở"), max_length=255, blank=True)
    dien_thoai = models.CharField(_("Số điện thoại"), max_length=32, blank=True)
    hotline = models.CharField(_("Số điện thoại liên hệ/Hotline"), max_length=32, blank=True)
    email = models.EmailField(_("Email giao dịch"), blank=True)
    website = models.URLField(_("Website"), blank=True)
    nguoi_dai_dien = models.CharField(_("Người đại diện"), max_length=128, blank=True)
    chuc_vu_nguoi_dai_dien = models.CharField(_("Chức vụ người đại diện"), max_length=128, blank=True)
    so_tai_khoan = models.CharField(_("Số tài khoản"), max_length=64, blank=True)
    ngan_hang = models.CharField(_("Ngân hàng"), max_length=128, blank=True)
    logo = models.ImageField(
        _("Logo dùng trên mẫu biểu"),
        upload_to="company/logos/%Y/",
        blank=True,
        null=True,
        help_text=_("Dùng cho header báo cáo/PDF nếu template hỗ trợ logo động."),
    )
    ghi_chu = models.TextField(_("Ghi chú nội bộ"), blank=True)
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)


    class Meta:
        verbose_name = _("Thông tin công ty")
        verbose_name_plural = _("Thông tin công ty")
        indexes = [models.Index(fields=["tenant_id"], name="main_company_tenant_idx")]
        constraints = [
            models.UniqueConstraint(fields=["tenant_id"], name="uq_companyinfo_one_per_org"),
        ]

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        invalidate_company_info_cache(self.tenant_id)

    def delete(self, *args, **kwargs):
        tenant_id = self.tenant_id
        result = super().delete(*args, **kwargs)
        invalidate_company_info_cache(tenant_id)
        return result

    @property
    def display_name(self):
        return self.ten_phap_ly or self.ten_cong_ty

    @property
    def contact_phone(self):
        return self.hotline or self.dien_thoai


    def as_report_context(self):
        return {
            "name": self.display_name,
            "legal_name": self.ten_phap_ly or self.ten_cong_ty,
            "trade_name": self.ten_cong_ty,
            "tax_code": self.ma_so_thue,
            "address": self.dia_chi,
            "phone": self.dien_thoai,
            "hotline": self.contact_phone,
            "email": self.email,
            "website": self.website,
            "representative": self.nguoi_dai_dien,
            "representative_title": self.chuc_vu_nguoi_dai_dien,
            "bank_account": self.so_tai_khoan,
            "bank_name": self.ngan_hang,
            "logo": self.logo,
            "logo_url": getattr(self.logo, "url", "") if self.logo else "",
            "logo_path": getattr(self.logo, "path", "") if self.logo else "",
        }
