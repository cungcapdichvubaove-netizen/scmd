# -*- coding: utf-8 -*-
"""Assignment and region scope models for SCMD Pro access hardening."""

from __future__ import annotations

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.managers import TenantAwareManager, TenantScopedModel
from users.models import NhanVien


class Region(TenantScopedModel):
    """Operational region / area used for area-manager scope enforcement."""

    ma_vung = models.CharField(_("Mã vùng"), max_length=50, unique=True, db_index=True)
    ten_vung = models.CharField(_("Tên vùng"), max_length=255)
    mo_ta = models.TextField(_("Mô tả"), blank=True, default="")

    class Meta:
        verbose_name = _("Vùng quản lý")
        verbose_name_plural = _("Vùng quản lý")
        indexes = [models.Index(fields=["tenant_id", "ten_vung"], name="user_region_tenant_name_idx")]

    def __str__(self):
        return f"{self.ma_vung} - {self.ten_vung}"

class NhanVienRegionAssignmentManager(TenantAwareManager):
    """Quản lý truy vấn lịch sử phân vùng nhân sự."""

    def get_queryset(self):
        return super().get_queryset().select_related("region", "nhan_vien")

    def get_active_assignment_for_date(self, nhan_vien, target_date):
        """
        Tìm bản ghi phân vùng có hiệu lực cho nhân viên tại một ngày cụ thể.
        Sử dụng logic: starts_at <= target_date <= ends_at (hoặc ends_at is NULL).
        """
        return self.filter(
            nhan_vien=nhan_vien,
            starts_at__lte=target_date,
            status="ACTIVE"
        ).filter(
            models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=target_date)
        ).order_by('-starts_at').first()


class NhanVienRegionAssignment(TenantScopedModel):
    """Direct assignment of an employee/manager to an operational region."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", _("Đang hiệu lực")
        INACTIVE = "INACTIVE", _("Ngưng hiệu lực")

    nhan_vien = models.ForeignKey(
        NhanVien,
        on_delete=models.CASCADE,
        related_name="cac_phan_vung_quan_ly",
        verbose_name=_("Nhân viên"),
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="cac_nhan_vien_duoc_phan_vung",
        verbose_name=_("Vùng quản lý"),
    )
    starts_at = models.DateField(_("Hiệu lực từ"), db_index=True)
    ends_at = models.DateField(_("Hiệu lực đến"), null=True, blank=True, db_index=True)
    status = models.CharField(
        _("Trạng thái"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    assigned_by = models.ForeignKey(
        NhanVien,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_phan_vung_da_gan",
        verbose_name=_("Người gán vùng"),
    )
    reason = models.TextField(_("Lý do phân vùng"), blank=True, default="")

    objects = NhanVienRegionAssignmentManager()

    def clean(self):
        """Kiểm tra logic nghiệp vụ và ngăn chặn chồng chéo thời gian."""
        super().clean()

        # 1. Kiểm tra tính hợp lệ của khoảng ngày
        if self.starts_at and self.ends_at and self.ends_at < self.starts_at:
            raise ValidationError({
                "ends_at": _("Ngày kết thúc không được phép trước ngày bắt đầu.")
            })

        # 2. Kiểm tra chồng chéo cho các bản ghi đang có hiệu lực (ACTIVE)
        if self.status == self.Status.ACTIVE:
            overlapping = NhanVienRegionAssignment.objects.filter(
                nhan_vien=self.nhan_vien,
                status=self.Status.ACTIVE,
            ).exclude(pk=self.pk)

            # Logic kiểm tra overlap:
            # (Other.starts_at <= Self.ends_at) AND (Self.starts_at <= Other.ends_at)
            # Lưu ý: ends_at = None được hiểu là vô thời hạn (vô cùng lớn)
            if self.ends_at:
                overlapping = overlapping.filter(starts_at__lte=self.ends_at)

            overlapping = overlapping.filter(
                models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=self.starts_at)
            )

            conflict = overlapping.select_related('region').first()
            if conflict:
                raise ValidationError(_(
                    "Nhân viên đã được gán vào vùng '%(region)s' trong khoảng thời gian này. "
                    "Vui lòng đóng hoặc điều chỉnh bản ghi cũ trước khi tạo mới."
                ) % {'region': conflict.region.ten_vung})

    class Meta:
        verbose_name = _("Phân công vùng cho nhân viên")
        verbose_name_plural = _("Phân công vùng cho nhân viên")
        indexes = [
            # SCMD Pro: Shorten index names to comply with 30-char limit (models.E034)
            models.Index(fields=["tenant_id", "nhan_vien", "status"], name="usr_rasg_t_stf_stat_idx"),
            models.Index(fields=["tenant_id", "region", "status"], name="usr_rasg_t_reg_stat_idx"),
        ]

    def __str__(self):
        return f"{self.nhan_vien} @ {self.region}"
