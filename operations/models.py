# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: operations/models.py
Author: Mr. Anh (CTO) & AI Assistant
Created Date: 2025-12-10
Updated Date: 2026-06-08
Version: v3.5.0
Description: Model quản lý Vận hành, Chấm công và Xử lý sự cố.
             HARDENING PHASE: Chuẩn hóa Multi-tenancy và Geo-spatial helpers.
             - Tích hợp PointField cho định vị chính xác cao.
             - Gia cố Anti-fraud và GEOFENCING logic.
             - SSOT: Tuân thủ tuyệt đối DOCUMENTATION.md v2.0.0.
"""

import uuid
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Callable, Any
from django.contrib.gis.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import IntegrityError, transaction, models as db_models # Alias models to db_models to avoid conflict with gis.db.models
from core.managers import PhanCongManager, TenantAwareManager, TenantScopedModel, ViTriChotManager
from core.workflow_transition_policy import WorkflowTransitionPolicy

from users.models import NhanVien
from clients.models import MucTieu

if TYPE_CHECKING:
    from core.managers import PhanCongManager, TenantAwareManager, ViTriChotManager

# Logger cho hệ thống vận hành SCMD
logger = logging.getLogger(__name__)

from django.conf import settings
# ==============================================================================
# 0. MULTI-TENANCY CORE (Zero Trust Architecture)
# ==============================================================================


class ViTriChot(TenantScopedModel):
    """Định nghĩa các vị trí trực cụ thể tại mục tiêu (Cổng chính, Tuần tra, Giám sát...)"""
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

    objects: "ViTriChotManager" = ViTriChotManager()



    class Meta:
        verbose_name = _("Vị trí chốt trực")
        verbose_name_plural = _("1. Danh sách Vị trí chốt")

    def __str__(self):
        try:
            return f"{self.ten_vi_tri} ({self.muc_tieu.ten_muc_tieu})"
        except Exception:
            return f"{self.ten_vi_tri}"


class CaLamViec(TenantScopedModel):
    """Quy định khung thời gian các ca làm việc (Ca ngày, Ca đêm, Ca hành chính)"""
    ten_ca = models.CharField(
        _("Tên ca trực"), 
        max_length=100,
        help_text=_("VD: Ca 1 (06h-18h), Ca hành chính")
    )
    gio_bat_dau = models.TimeField(_("Giờ bắt đầu"))
    gio_ket_thuc = models.TimeField(_("Giờ kết thúc"))

    objects: "TenantAwareManager" = TenantAwareManager()

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



class PhanCongCaTruc(TenantScopedModel):
    """Lịch trình phân công nhân sự cụ thể theo ngày và vị trí"""
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

    objects: "PhanCongManager" = PhanCongManager()



    class Meta:
        verbose_name = _("Phân công ca trực")
        verbose_name_plural = _("3. Bảng Phân công ca trực")
        ordering = ["ngay_truc", "ca_lam_viec__gio_bat_dau"]
        unique_together = [['nhan_vien', 'ngay_truc', 'ca_lam_viec']]
        indexes = [
            models.Index(fields=['tenant_id', 'ngay_truc']),
            models.Index(fields=['nhan_vien', 'ngay_truc']),
            models.Index(fields=['vi_tri_chot', 'ngay_truc']),
        ]

    if TYPE_CHECKING:
        # Type hints cho quan hệ ngược (Rule 14)
        chamcong: "ChamCong"
        cac_su_co: models.Manager["BaoCaoSuCo"]
        cac_lan_kiem_tra: models.Manager["KiemTraQuanSo"]

    def __str__(self):
        try:
            return f"{self.nhan_vien.ho_ten} - {self.ngay_truc.strftime('%d/%m/%Y')} ({self.ca_lam_viec.ten_ca})"
        except Exception:
            return f"Phân công {self.pk}"

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

    def get_related_payroll_period(self):
        from accounting.application.payroll_lock_policy import PayrollLockPolicy

        return PayrollLockPolicy.get_period_for_assignment(self)

    @property
    def is_payroll_locked(self):
        from accounting.application.payroll_lock_policy import PayrollLockPolicy

        return PayrollLockPolicy.is_period_locked_for_assignment(self)

    def clean(self):
        super().clean()
        from accounting.application.payroll_lock_policy import PayrollLockPolicy

        PayrollLockPolicy.enforce_assignment_mutable(self)

    def save(self, *args, **kwargs):
        from accounting.application.payroll_lock_policy import PayrollLockPolicy

        PayrollLockPolicy.enforce_assignment_mutable(self)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from accounting.application.payroll_lock_policy import PayrollLockPolicy

        PayrollLockPolicy.enforce_assignment_mutable(self)
        return super().delete(*args, **kwargs)



class LichTuanTraVanHanh(TenantScopedModel):
    """Lịch tuần tra vận hành do Phòng nghiệp vụ/vận hành tạo.

    Phase 2 domain correction: đây là entity canonical để lập lịch tuần tra
    bảo vệ theo mục tiêu/chốt/ca. Tuyến/điểm QR còn dùng bảng legacy trong
    inspection trong giai đoạn chuyển tiếp, nhưng owner nghiệp vụ là operations.
    """

    class TrangThai(models.TextChoices):
        ACTIVE = "ACTIVE", _("Đang áp dụng")
        INACTIVE = "INACTIVE", _("Tạm ngưng")

    muc_tieu = models.ForeignKey(
        MucTieu,
        on_delete=models.PROTECT,
        related_name="lich_tuan_tra_van_hanh",
        verbose_name=_("Mục tiêu bảo vệ"),
    )
    vi_tri_chot = models.ForeignKey(
        ViTriChot,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="lich_tuan_tra_van_hanh",
        verbose_name=_("Vị trí chốt áp dụng"),
        help_text=_("Để trống nếu lịch áp dụng cho mọi chốt thuộc mục tiêu."),
    )
    ca_lam_viec = models.ForeignKey(
        CaLamViec,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="lich_tuan_tra_van_hanh",
        verbose_name=_("Ca trực áp dụng"),
        help_text=_("Để trống nếu lịch áp dụng cho mọi ca tại mục tiêu/chốt."),
    )
    tuyen_tuan_tra = models.ForeignKey(
        "inspection.LoaiTuanTra",
        on_delete=models.PROTECT,
        related_name="lich_van_hanh",
        verbose_name=_("Tuyến tuần tra vận hành"),
        help_text=_("Bảng tuyến hiện còn legacy trong inspection; owner nghiệp vụ là operations."),
    )
    tan_suat_luot_bat_buoc = models.PositiveSmallIntegerField(
        _("Số lượt bắt buộc trong ca"),
        default=1,
        help_text=_("Số nhiệm vụ tuần tra cần tạo cho mỗi phân công ca phù hợp."),
    )
    khung_gio_bat_dau = models.TimeField(_("Khung giờ bắt đầu"), null=True, blank=True)
    khung_gio_ket_thuc = models.TimeField(_("Khung giờ kết thúc"), null=True, blank=True)
    grace_minutes = models.PositiveSmallIntegerField(_("Grace minutes"), default=10)
    yeu_cau_gps = models.BooleanField(_("Bắt buộc GPS"), default=False)
    yeu_cau_anh = models.BooleanField(_("Bắt buộc ảnh"), default=False)
    trang_thai = models.CharField(
        _("Trạng thái"),
        max_length=16,
        choices=TrangThai.choices,
        default=TrangThai.ACTIVE,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lich_tuan_tra_van_hanh_da_tao",
        verbose_name=_("Người tạo"),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lich_tuan_tra_van_hanh_da_cap_nhat",
        verbose_name=_("Người cập nhật"),
    )
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = _("Lịch tuần tra theo ca")
        verbose_name_plural = _("Lịch tuần tra theo ca")
        ordering = ["muc_tieu__ten_muc_tieu", "vi_tri_chot__ten_vi_tri", "ca_lam_viec__gio_bat_dau", "tuyen_tuan_tra__ten_loai"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "muc_tieu"], name="ops_gpsched_tenant_mt_idx"),
            models.Index(fields=["tenant_id", "vi_tri_chot", "ca_lam_viec"], name="ops_gpsched_post_shift_idx"),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(tan_suat_luot_bat_buoc__gte=1), name="ck_guard_patrol_schedule_freq_ge_1"),
        ]
        permissions = [
            ("quan_ly_lich_tuan_tra_van_hanh", _("Có thể quản lý lịch tuần tra vận hành")),
            ("xem_doi_soat_tuan_tra_van_hanh", _("Có thể xem đối soát tuần tra vận hành")),
        ]

    def __str__(self):
        scope = self.vi_tri_chot.ten_vi_tri if self.vi_tri_chot_id else self.muc_tieu.ten_muc_tieu
        ca = self.ca_lam_viec.ten_ca if self.ca_lam_viec_id else _("Mọi ca")
        return f"{scope} · {ca} · {self.tuyen_tuan_tra}"

    def clean(self):
        super().clean()
        if self.vi_tri_chot_id and self.muc_tieu_id and self.vi_tri_chot.muc_tieu_id != self.muc_tieu_id:
            raise ValidationError({"vi_tri_chot": _("Vị trí chốt phải thuộc mục tiêu của lịch tuần tra.")})
        if self.tuyen_tuan_tra_id and self.muc_tieu_id and self.tuyen_tuan_tra.muc_tieu_id and self.tuyen_tuan_tra.muc_tieu_id != self.muc_tieu_id:
            raise ValidationError({"tuyen_tuan_tra": _("Tuyến tuần tra phải thuộc mục tiêu của lịch tuần tra.")})
        if self.khung_gio_bat_dau and self.khung_gio_ket_thuc and self.khung_gio_bat_dau == self.khung_gio_ket_thuc:
            raise ValidationError({"khung_gio_ket_thuc": _("Khung giờ kết thúc không được trùng khung giờ bắt đầu.")})


class NhiemVuTuanTraCa(TenantScopedModel):
    """Nhiệm vụ tuần tra được materialize cho từng phân công ca trực."""

    class TrangThai(models.TextChoices):
        PLANNED = "PLANNED", _("Đã lên lịch")
        IN_PROGRESS = "IN_PROGRESS", _("Đang thực hiện")
        COMPLETED_VALID = "COMPLETED_VALID", _("Hoàn thành hợp lệ")
        COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS", _("Hoàn thành có cảnh báo")
        MISSED = "MISSED", _("Bỏ lượt/thiếu điểm")
        CANCELLED_WITH_REASON = "CANCELLED_WITH_REASON", _("Đã hủy có lý do")

    lich_tuan_tra = models.ForeignKey(
        LichTuanTraVanHanh,
        on_delete=models.PROTECT,
        related_name="nhiem_vu_theo_ca",
        verbose_name=_("Lịch tuần tra vận hành"),
    )
    phan_cong_ca_truc = models.ForeignKey(
        PhanCongCaTruc,
        on_delete=models.PROTECT,
        related_name="nhiem_vu_tuan_tra",
        verbose_name=_("Phân công ca trực"),
    )
    tuyen_tuan_tra = models.ForeignKey(
        "inspection.LoaiTuanTra",
        on_delete=models.PROTECT,
        related_name="nhiem_vu_van_hanh",
        verbose_name=_("Tuyến tuần tra"),
    )
    thu_tu_luot = models.PositiveSmallIntegerField(_("Thứ tự lượt trong ca"), default=1)
    thoi_gian_bat_dau_du_kien = models.DateTimeField(_("Bắt đầu dự kiến"), null=True, blank=True, db_index=True)
    thoi_gian_ket_thuc_du_kien = models.DateTimeField(_("Kết thúc dự kiến"), null=True, blank=True)
    grace_deadline = models.DateTimeField(_("Hạn grace"), null=True, blank=True, db_index=True)
    trang_thai = models.CharField(
        _("Trạng thái nhiệm vụ"),
        max_length=32,
        choices=TrangThai.choices,
        default=TrangThai.PLANNED,
        db_index=True,
    )
    luot_tuan_tra = models.ForeignKey(
        "inspection.LuotTuanTra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nhiem_vu_van_hanh",
        verbose_name=_("Lượt tuần tra thực tế"),
    )
    so_diem_bat_buoc = models.PositiveIntegerField(_("Số điểm bắt buộc"), default=0)
    so_diem_da_quet = models.PositiveIntegerField(_("Số điểm đã quét"), default=0)
    so_diem_canh_bao = models.PositiveIntegerField(_("Số điểm có cảnh báo"), default=0)
    ly_do_huy_bo = models.TextField(_("Lý do hủy/bỏ lượt"), blank=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = _("Nhiệm vụ tuần tra theo ca")
        verbose_name_plural = _("Nhiệm vụ tuần tra theo ca")
        ordering = ["phan_cong_ca_truc__ngay_truc", "phan_cong_ca_truc__ca_lam_viec__gio_bat_dau", "thu_tu_luot"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "thoi_gian_bat_dau_du_kien"], name="ops_gptask_tenant_stat_idx"),
            models.Index(fields=["tenant_id", "phan_cong_ca_truc", "trang_thai"], name="ops_gptask_shift_stat_idx"),
            models.Index(fields=["tenant_id", "grace_deadline"], name="ops_gptask_grace_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "lich_tuan_tra", "phan_cong_ca_truc", "thu_tu_luot"], name="uq_guard_patrol_task_per_shift"),
            models.CheckConstraint(check=models.Q(thu_tu_luot__gte=1), name="ck_guard_patrol_task_order_ge_1"),
        ]
        permissions = [
            ("thuc_hien_tuan_tra_bao_ve", _("Có thể thực hiện tuần tra bảo vệ")),
            ("xu_ly_canh_bao_tuan_tra_van_hanh", _("Có thể xử lý cảnh báo tuần tra vận hành")),
        ]

    def __str__(self):
        return f"{self.phan_cong_ca_truc} · {self.tuyen_tuan_tra} · lượt {self.thu_tu_luot}"

    def clean(self):
        super().clean()
        if not self.lich_tuan_tra_id or not self.phan_cong_ca_truc_id:
            return
        lich = self.lich_tuan_tra
        phan_cong = self.phan_cong_ca_truc
        if lich.muc_tieu_id and phan_cong.vi_tri_chot_id and phan_cong.vi_tri_chot.muc_tieu_id != lich.muc_tieu_id:
            raise ValidationError({"phan_cong_ca_truc": _("Phân công ca trực không thuộc mục tiêu của lịch tuần tra.")})
        if lich.vi_tri_chot_id and phan_cong.vi_tri_chot_id != lich.vi_tri_chot_id:
            raise ValidationError({"phan_cong_ca_truc": _("Phân công ca trực không thuộc chốt áp dụng của lịch tuần tra.")})
        if lich.ca_lam_viec_id and phan_cong.ca_lam_viec_id != lich.ca_lam_viec_id:
            raise ValidationError({"phan_cong_ca_truc": _("Phân công ca trực không thuộc ca áp dụng của lịch tuần tra.")})

class ShiftChangeRequest(TenantScopedModel):
    """SSOT hồ sơ đổi ca/tăng ca/hủy ca có vòng đời phê duyệt riêng.

    Không sửa trực tiếp ``PhanCongCaTruc`` khi yêu cầu được tạo. Việc áp dụng
    thay đổi vào lịch trực phải đi qua use case/policy riêng để không phá payroll
    lock và dữ liệu chấm công hiện tại.
    """

    class LoaiYeuCau(models.TextChoices):
        CHANGE_SHIFT = "CHANGE_SHIFT", _("Đổi ca")
        SWAP_STAFF = "SWAP_STAFF", _("Đổi người trực")
        OVERTIME = "OVERTIME", _("Tăng ca")
        CANCEL_SHIFT = "CANCEL_SHIFT", _("Hủy ca")

    class TrangThai(models.TextChoices):
        DRAFT = "DRAFT", _("Nháp")
        PENDING_APPROVAL = "PENDING_APPROVAL", _("Chờ duyệt")
        APPROVED = "APPROVED", _("Đã duyệt")
        APPLIED = "APPLIED", _("Đã áp dụng")
        REJECTED = "REJECTED", _("Từ chối")
        CANCELLED = "CANCELLED", _("Đã hủy")

    ALLOWED_STATUS_TRANSITIONS = {
        TrangThai.DRAFT: {TrangThai.PENDING_APPROVAL, TrangThai.CANCELLED},
        TrangThai.PENDING_APPROVAL: {TrangThai.APPROVED, TrangThai.REJECTED, TrangThai.CANCELLED},
        TrangThai.APPROVED: {TrangThai.APPLIED, TrangThai.CANCELLED},
        TrangThai.APPLIED: set(),
        TrangThai.REJECTED: set(),
        TrangThai.CANCELLED: set(),
    }

    ma_yeu_cau = models.CharField(_("Mã yêu cầu"), max_length=64, db_index=True)
    nguoi_yeu_cau = models.ForeignKey(
        NhanVien,
        on_delete=models.CASCADE,
        related_name="cac_yeu_cau_doi_ca",
        verbose_name=_("Người yêu cầu"),
    )
    phan_cong_goc = models.ForeignKey(
        PhanCongCaTruc,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_yeu_cau_thay_doi",
        verbose_name=_("Phân công gốc"),
    )
    loai_yeu_cau = models.CharField(_("Loại yêu cầu"), max_length=32, choices=LoaiYeuCau.choices, default=LoaiYeuCau.CHANGE_SHIFT)
    ngay_mong_muon = models.DateField(_("Ngày trực mong muốn"), null=True, blank=True, db_index=True)
    ca_mong_muon = models.ForeignKey(
        CaLamViec,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_yeu_cau_doi_ca_mong_muon",
        verbose_name=_("Ca mong muốn"),
    )
    vi_tri_mong_muon = models.ForeignKey(
        ViTriChot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_yeu_cau_doi_ca_mong_muon",
        verbose_name=_("Vị trí mong muốn"),
    )
    nhan_vien_thay_the = models.ForeignKey(
        NhanVien,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_yeu_cau_thay_the_ca",
        verbose_name=_("Nhân viên thay thế"),
    )
    trang_thai = models.CharField(_("Trạng thái"), max_length=32, choices=TrangThai.choices, default=TrangThai.DRAFT, db_index=True)
    ly_do = models.TextField(_("Lý do"), blank=True)
    file_minh_chung = models.FileField(_("File minh chứng"), upload_to="shift_change_requests/%Y/%m/", null=True, blank=True)
    nguoi_duyet = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cac_yeu_cau_doi_ca_da_duyet",
        verbose_name=_("Người duyệt"),
    )
    ngay_duyet = models.DateTimeField(_("Thời điểm duyệt"), null=True, blank=True)
    ghi_chu = models.TextField(_("Ghi chú"), blank=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        verbose_name = _("Yêu cầu đổi ca/tăng ca")
        verbose_name_plural = _("Yêu cầu đổi ca/tăng ca")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "trang_thai", "created_at"], name="ops_shiftreq_tenant_stat_idx"),
            models.Index(fields=["tenant_id", "nguoi_yeu_cau", "trang_thai"], name="ops_shiftreq_tenant_staff_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "ma_yeu_cau"], name="uq_shiftreq_tenant_code"),
        ]

    def __str__(self):
        return f"{self.ma_yeu_cau} - {self.nguoi_yeu_cau}"

    def clean(self):
        super().clean()
        if self.loai_yeu_cau in (self.LoaiYeuCau.CHANGE_SHIFT, self.LoaiYeuCau.OVERTIME) and not self.ngay_mong_muon:
            raise ValidationError({"ngay_mong_muon": _("Yêu cầu đổi ca/tăng ca phải có ngày mong muốn.")})
        if self.loai_yeu_cau == self.LoaiYeuCau.SWAP_STAFF and not self.nhan_vien_thay_the_id:
            raise ValidationError({"nhan_vien_thay_the": _("Yêu cầu đổi người trực phải có nhân viên thay thế.")})

    def record_status_transition(self, *, actor=None, old_status=None, new_status=None, note=""):
        new_status = new_status if new_status is not None else self.trang_thai
        if old_status == new_status:
            return None
        try:
            from main.models import AuditLog
            return AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.UPDATE,
                module="operations",
                model_name="ShiftChangeRequest",
                object_id=str(self.pk),
                tenant_id=getattr(self, "tenant_id", None),
                note=note or "Operations shift change request status transition",
                changes={"status_transition": {"old": old_status, "new": new_status}, "ma_yeu_cau": self.ma_yeu_cau, "nguoi_yeu_cau_id": self.nguoi_yeu_cau_id},
            )
        except Exception as exc:
            logger.error("Failed to audit ShiftChangeRequest status transition: %s", exc)
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


class ChamCong(TenantScopedModel):
    """
    Model lưu trữ dữ liệu chấm công GPS.
    """
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
        default=Decimal('0'),
        help_text=_("Tổng tiền phạt vi phạm phát sinh trong ca trực này")
    )

    ghi_chu = models.TextField(_("Ghi chú chấm công"), blank=True)

    objects: "TenantAwareManager" = TenantAwareManager()

    if TYPE_CHECKING:
        get_trang_thai_display: Callable[[], str]

    class Meta:
        verbose_name = _("Dữ liệu Chấm công")
        verbose_name_plural = _("4. Dữ liệu Chấm công")
        indexes = [
            models.Index(
                fields=['tenant_id', 'thoi_gian_check_in'], 
                name='ops_cc_tenant_checkin_idx'
            ),
        ]

    if TYPE_CHECKING:
        # Type hints cho quan hệ ngược
        adjustments: models.Manager["ChamCongAdjustment"]

    def calculate_work_hours(self):
        # Wrapper cho các template tags hiện có
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

    AUDIT_GUARDED_FIELDS = (
        "thoi_gian_check_in",
        "thoi_gian_check_out",
        "anh_check_in",
        "anh_check_out",
        "location_check_in",
        "location_check_out",
        "ip_check_in",
        "ip_check_out",
        "thiet_bi_check_in",
        "thiet_bi_check_out",
        "vi_tri_hop_le",
        "khoang_cach_check_in",
        "thuc_lam_gio",
        "di_muon_phut",
        "ve_som_phut",
        "ghi_chu",
    )

    @classmethod
    def _serialize_audit_value(cls, value):
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if hasattr(value, "wkt"):
            return value.wkt
        if hasattr(value, "name"):
            return value.name
        return value

    def _changed_audit_guarded_fields(self):
        if self._state.adding or not self.pk:
            return []

        persisted = (
            type(self).objects
            .for_tenant(self.tenant_id)
            .filter(pk=self.pk)
            .only(*self.AUDIT_GUARDED_FIELDS)
            .first()
        )
        if persisted is None:
            return []

        changed = []
        for field_name in self.AUDIT_GUARDED_FIELDS:
            old_value = self._serialize_audit_value(getattr(persisted, field_name, None))
            new_value = self._serialize_audit_value(getattr(self, field_name, None))
            if old_value != new_value:
                changed.append(field_name)
        return changed

    def save(self, *args, **kwargs):
        from accounting.application.payroll_lock_policy import PayrollLockPolicy
        from core.audit_context import is_attendance_mutation_allowed

        changed_fields = self._changed_audit_guarded_fields()
        if (changed_fields or self.pk or (self.ca_truc and self.ca_truc.pk)) and PayrollLockPolicy.is_period_locked_for_attendance(self):
            raise ValidationError(
                _(
                    "Kỳ lương đã LOCKED/PAID. Không được sửa trực tiếp chấm công. "
                    "Hãy xử lý bằng adjustment/reconciliation có audit trail."
                )
            )
        if changed_fields and not is_attendance_mutation_allowed():
            raise ValidationError(
                _(
                    "Dữ liệu chấm công nhạy cảm chỉ được sửa qua application use case có audit trail. "
                    f"Các trường bị chặn: {', '.join(changed_fields)}"
                )
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from accounting.application.payroll_lock_policy import PayrollLockPolicy

        PayrollLockPolicy.enforce_attendance_mutable(self)
        return super().delete(*args, **kwargs)

    def get_related_payroll_period(self):
        from accounting.application.payroll_lock_policy import PayrollLockPolicy

        return PayrollLockPolicy.get_period_for_attendance(self)

    @property
    def is_payroll_locked(self):
        from accounting.application.payroll_lock_policy import PayrollLockPolicy

        return PayrollLockPolicy.is_period_locked_for_attendance(self)


class ChamCongAdjustment(TenantScopedModel):
    """Lưu vết chỉnh sửa chấm công để bảo vệ đối soát payroll/attendance."""
    cham_cong = models.ForeignKey(
        ChamCong,
        on_delete=models.CASCADE,
        related_name="adjustments",
        verbose_name=_("Bản ghi chấm công"),
    )
    bang_luong = models.ForeignKey(
        "accounting.BangLuongThang",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_adjustments",
        verbose_name=_("Kỳ lương liên quan"),
    )
    nguoi_dieu_chinh = models.ForeignKey(
        NhanVien,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cham_cong_adjustments",
        verbose_name=_("Người điều chỉnh"),
    )
    ly_do = models.TextField(_("Lý do điều chỉnh"))
    truoc_dieu_chinh = db_models.JSONField(_("Dữ liệu trước chỉnh sửa"), default=dict, blank=True)
    sau_dieu_chinh = db_models.JSONField(_("Dữ liệu sau chỉnh sửa"), default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects: "TenantAwareManager" = TenantAwareManager()

    def save(self, *args, **kwargs):
        from django.core.exceptions import ImproperlyConfigured

        if not hasattr(settings, "SCMD_ORGANIZATION_ID"):
            raise ImproperlyConfigured("SCMD_ORGANIZATION_ID is not defined in settings. Cannot save tenant-aware model.")
        self.tenant_id = settings.SCMD_ORGANIZATION_ID
        super().save(*args, **kwargs)

    def clean(self):
        if hasattr(settings, "SCMD_ORGANIZATION_ID") and self.tenant_id != settings.SCMD_ORGANIZATION_ID:
            raise ValidationError(_(f"Tenant ID must be {settings.SCMD_ORGANIZATION_ID} for this organization."))
        super().clean()

    class Meta:
        verbose_name = _("Điều chỉnh chấm công")
        verbose_name_plural = _("4B. Điều chỉnh chấm công")
        ordering = ["-created_at"]


# ==============================================================================
# 2. QUẢN LÝ SỰ CỐ & ĐỀN BÙ
# ==============================================================================

class BaoCaoSuCo(TenantScopedModel):
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
        default=Decimal('0')
    )
    cong_ty_chi_tra = models.DecimalField(
        _("Công ty chi trả"), 
        max_digits=15, 
        decimal_places=0, 
        default=Decimal('0'), 
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
        default=Decimal('0'), 
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

    objects: "TenantAwareManager" = TenantAwareManager()

    if TYPE_CHECKING:
        # Type hints for dynamic Django methods
        get_muc_do_display: Callable[[], str]

    @staticmethod
    def generate_incident_code():
        """Generate a human-readable unique incident code."""
        return f"SC-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"


    def save(self, *args, **kwargs):
        """Persist incident data while enforcing organization scope and identity invariants."""
        # Rule 6.3: Incident reconciliation - Closed incidents cannot be edited.
        if self.pk:
            from operations.application.incident_transition_policy import IncidentTransitionPolicy
            
            # Lấy trạng thái hiện tại từ DB để so sánh (không tin vào state trong memory)
            # SCMD Pro: Enforce organization scope guard for internal state comparison.
            old_instance = (
                BaoCaoSuCo.objects.for_tenant(self.tenant_id)
                .filter(pk=self.pk).only('trang_thai').first()
            )
            if old_instance:
                # 1. Kiểm tra máy trạng thái (State Machine Guard)
                try:
                    IncidentTransitionPolicy.validate_transition(old_instance.trang_thai, self.trang_thai)
                except ValueError as exc:
                    raise ValidationError(_(str(exc)))
                
                # Lưu ý: Việc kiểm tra sửa đổi PRIMARY_FIELDS được ưu tiên xử lý tại Application Layer (Form/Serializer)
                # để tránh overhead query mỗi lần save() ở mức thấp.

        auto_generated_code = False
        if not self.ma_su_co or self.ma_su_co == 'PENDING':
            self.ma_su_co = self.generate_incident_code()
            auto_generated_code = True

        for attempt in range(5):
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
        indexes = [
            models.Index(fields=['tenant_id', 'trang_thai', 'created_at']),
            models.Index(fields=['tenant_id', 'created_at']),
        ]


# ==============================================================================
# 3. QUẢN LÝ ĐỀ XUẤT & KIỂM TRA QUÂN SỐ
# ==============================================================================

class BaoCaoDeXuat(TenantScopedModel):
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

    objects: "TenantAwareManager" = TenantAwareManager()

    if TYPE_CHECKING:
        get_trang_thai_display: Callable[[], str]

    class Meta:
        verbose_name = _("Đề xuất nghiệp vụ")
        verbose_name_plural = _("6. Danh sách Đề xuất")
        ordering = ['-ngay_gui']

    def __str__(self):
        return f"{self.tieu_de} - {self.get_trang_thai_display()}"


class KiemTraQuanSo(TenantScopedModel):
    """Giao thức Alive Check: Gọi phản hồi ngẫu nhiên để kiểm tra tình trạng làm việc"""
    TRANG_THAI_CHECK = [
        ('PENDING', _('⏳ Đang chờ phản hồi')), 
        ('OK', _('✅ Đã xác nhận (Hoàn thành)')), 
        ('MISSED', _('❌ Bỏ lỡ (Không phản hồi)')), 
        ('LATE', _('🕒 Phản hồi muộn'))
    ]
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
    device_id_xac_thuc = models.CharField(
        _("Thiết bị xác thực"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Mã thiết bị đã dùng để phản hồi Alive Check.")
    )
    trang_thai = models.CharField(_("Kết quả kiểm tra"), max_length=20, choices=TRANG_THAI_CHECK, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    objects: "TenantAwareManager" = TenantAwareManager()

    if TYPE_CHECKING:
        get_trang_thai_display: Callable[[], str]



    class Meta:
        verbose_name = _("Kiểm tra quân số")
        verbose_name_plural = _("7. Lịch sử Alive Check")
        ordering = ['-created_at']

    def __str__(self): 
        try:
            return f"Alive Check: {self.ca_truc.nhan_vien.ho_ten} - {self.get_trang_thai_display()}"
        except Exception:
            return f"Alive Check {self.pk}"
