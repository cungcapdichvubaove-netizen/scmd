# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: main/models.py
Author: Senior Software Architect
Version: v2.0.0 (Pro Edition)
Description: Hệ thống Audit Log tập trung cho SCMD Erp.
             Tuân thủ Nghị định 13/2023/ND-CP về bảo vệ dữ liệu cá nhân.
"""

import uuid
import hashlib
import json
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

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

    tenant_id = models.UUIDField(
        _("Tenant ID"), 
        db_index=True, 
        default=uuid.uuid4, 
        editable=False
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
        # Sử dụng định dạng ISO cho timestamp để đảm bảo tính ổn định khi đối soát
        ts_str = self.timestamp.isoformat() if self.timestamp else "None"
        content = f"{self.tenant_id}-{self.user_id}-{self.action}-{self.model_name}-{self.object_id}-{json.dumps(self.changes or {})}-{ts_str}"
        return hashlib.sha256(content.encode()).hexdigest()

    def save(self, *args, **kwargs):
        if not self.timestamp:
            self.timestamp = timezone.now()
            
        if not self.tenant_id and hasattr(settings, 'SCMD_ORGANIZATION_ID'):
            self.tenant_id = settings.SCMD_ORGANIZATION_ID
            
        if not self.checksum:
            self.checksum = self.generate_checksum()
            
        super().save(*args, **kwargs)

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

    def save(self, *args, **kwargs):
        if hasattr(settings, "SCMD_ORGANIZATION_ID"):
            self.tenant_id = settings.SCMD_ORGANIZATION_ID
        super().save(*args, **kwargs)
