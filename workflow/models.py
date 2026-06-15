# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: workflow/models.py
Author: Mr. Anh (CTO) & AI Assistant
Updated Date: 2026-03-21
Description: Models cho Văn phòng số (Professional Office Workflow).
             ENHANCEMENT: Tự động hóa trạng thái, gia cố Validation 
             và chuẩn hóa Audit Trail cho quy trình phê duyệt.
"""

from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from users.models import NhanVien
from operations.models import MucTieu


# ==============================================================================
# 1. QUẢN LÝ CÔNG VIỆC (TASK)
# ==============================================================================
class Task(models.Model):
    """Điều phối và giám sát thực thi nhiệm vụ trong hệ thống SCMD."""
    
    class Priority(models.TextChoices):
        THAP = 'THAP', _('🟢 Thấp')
        TRUNG_BINH = 'TB', _('🔵 Trung bình')
        CAO = 'CAO', _('🟠 Cao')
        KHAN = 'KHAN', _('🔴 Khẩn cấp')

    class Status(models.TextChoices):
        MOI = 'MOI', _('Mới giao')
        DANG_THUC_HIEN = 'DANG_LAM', _('Đang thực hiện')
        CHO_DUYET = 'CHO_DUYET', _('Chờ nghiệm thu')
        HOAN_THANH = 'HOAN_THANH', _('Hoàn thành')
        DA_HUY = 'HUY', _('Đã hủy')

    tieu_de = models.CharField(_("Tiêu đề công việc"), max_length=255, db_index=True)
    noi_dung = models.TextField(_("Nội dung chi tiết"))
    
    # Phân vai trò nhân sự
    nguoi_giao = models.ForeignKey(
        NhanVien, on_delete=models.CASCADE, 
        related_name='task_giao', verbose_name=_("Người giao việc")
    )
    nguoi_nhan = models.ForeignKey(
        NhanVien, on_delete=models.CASCADE, 
        related_name='task_nhan', verbose_name=_("Người chịu trách nhiệm chính")
    )
    nguoi_phoi_hop = models.ManyToManyField(
        NhanVien, related_name='task_phoi_hop', 
        blank=True, verbose_name=_("Nhân sự phối hợp")
    )
    
    muc_tieu = models.ForeignKey(
        MucTieu, on_delete=models.SET_NULL, 
        null=True, blank=True, verbose_name=_("Mục tiêu bảo vệ liên quan")
    )
    
    han_chot = models.DateTimeField(_("Hạn chót (Deadline)"), null=True, blank=True, db_index=True)
    uu_tien = models.CharField(
        _("Độ ưu tiên"), max_length=20, 
        choices=Priority.choices, default=Priority.TRUNG_BINH, db_index=True
    )
    trang_thai = models.CharField(
        _("Trạng thái"), max_length=20, 
        choices=Status.choices, default=Status.MOI, db_index=True
    )
    
    tien_do = models.IntegerField(
        _("Tiến độ (%)"), 
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Nhập giá trị từ 0 đến 100")
    )
    
    file_dinh_kem = models.FileField(_("Tài liệu/Báo cáo"), upload_to='tasks/%Y/%m/', null=True, blank=True)
    
    ngay_tao = models.DateTimeField(_("Ngày tạo"), auto_now_add=True)
    ngay_cap_nhat = models.DateTimeField(_("Cập nhật cuối"), auto_now=True)

    class Meta:
        verbose_name = _("Công việc")
        verbose_name_plural = _("01. Quản lý Công việc")
        ordering = ['-ngay_tao']

    def __str__(self):
        return f"[{self.get_uu_tien_display()}] {self.tieu_de}"

    def get_absolute_url(self):
        return reverse('workflow:task_detail', kwargs={'pk': self.pk})

    def clean(self):
        """Kiểm soát logic dữ liệu Task."""
        # 1. Chống lỗi thời gian
        if self.pk is None and self.han_chot and self.han_chot < timezone.now():
            raise ValidationError({'han_chot': _("Thời hạn chót không được đặt trong quá khứ.")})
        
        # 2. Ràng buộc logic trạng thái và tiến độ
        if self.trang_thai == self.Status.HOAN_THANH and self.tien_do < 100:
            raise ValidationError({'tien_do': _("Công việc 'Hoàn thành' phải đạt tiến độ 100%.")})

    def save(self, *args, **kwargs):
        """Tự động hóa luồng trạng thái dựa trên dữ liệu thực tế."""
        # Tự động nhảy trạng thái khi bắt đầu làm
        if 0 < self.tien_do < 100 and self.trang_thai == self.Status.MOI:
            self.trang_thai = self.Status.DANG_THUC_HIEN
            
        # Tự động chuyển chờ nghiệm thu khi đạt 100%
        if self.tien_do == 100 and self.trang_thai in [self.Status.MOI, self.Status.DANG_THUC_HIEN]:
            self.trang_thai = self.Status.CHO_DUYET
            
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check trạng thái trễ hạn."""
        if not self.han_chot: return False
        return timezone.now() > self.han_chot and self.trang_thai not in [self.Status.HOAN_THANH, self.Status.DA_HUY]

    @property
    def time_status(self):
        """Hỗ trợ phân loại Dashboard: Trễ, Sắp đến hạn, Còn hạn."""
        if self.is_overdue: return "OVERDUE"
        if not self.han_chot: return "NO_DEADLINE"
        delta = self.han_chot - timezone.now()
        if delta.days < 1: return "URGENT" # Còn dưới 24h
        return "ON_TRACK"


# ==============================================================================
# 2. QUẢN LÝ TỜ TRÌNH (PROPOSAL)
# ==============================================================================
class Proposal(models.Model):
    """Hồ sơ tờ trình phê duyệt kỹ thuật, tài chính và nhân sự."""
    
    class Type(models.TextChoices):
        KE_HOACH = 'KE_HOACH', _('📄 Kế hoạch KD/Vận hành')
        MUA_SAM = 'MUA_SAM', _('🛒 Mua sắm / Trang bị')
        NHAN_SU = 'NHAN_SU', _('👥 Nhân sự (Tuyển/Bổ nhiệm)')
        TAI_CHINH = 'TAI_CHINH', _('💰 Tài chính / Thanh toán')
        KHAC = 'KHAC', _('📝 Khác')

    class Status(models.TextChoices):
        NHAP = 'NHAP', _('Bản nháp')
        CHO_DUYET = 'CHO_DUYET', _('⏳ Đang trình duyệt')
        DA_DUYET = 'DA_DUYET', _('✅ Đã phê duyệt')
        TU_CHOI = 'TU_CHOI', _('❌ Đã từ chối')
        YEU_CAU_SUA = 'YEU_CAU_SUA', _('✏️ Yêu cầu chỉnh sửa')

    tieu_de = models.CharField(_("Tiêu đề tờ trình"), max_length=255, db_index=True)
    loai_de_xuat = models.CharField(
        _("Loại tờ trình"), max_length=20, 
        choices=Type.choices, default=Type.KHAC, db_index=True
    )
    noi_dung = models.TextField(_("Nội dung trình duyệt"))
    
    nguoi_de_xuat = models.ForeignKey(
        NhanVien, on_delete=models.CASCADE, 
        related_name='proposals_created', verbose_name=_("Người khởi tạo")
    )
    
    nguoi_duyet_hien_tai = models.ForeignKey(
        NhanVien, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='proposals_pending', 
        verbose_name=_("Người đang thụ lý")
    )
    
    trang_thai = models.CharField(
        _("Trạng thái duyệt"), max_length=20, 
        choices=Status.choices, default=Status.NHAP, db_index=True
    )
    file_dinh_kem = models.FileField(_("Hồ sơ đính kèm"), upload_to='proposals/%Y/%m/', null=True, blank=True)
    
    ngay_tao = models.DateTimeField(_("Ngày khởi tạo"), auto_now_add=True)
    ngay_cap_nhat = models.DateTimeField(_("Cập nhật cuối"), auto_now=True)

    class Meta:
        verbose_name = _("Tờ trình")
        verbose_name_plural = _("02. Quản lý Tờ trình")
        ordering = ['-ngay_tao']

    def __str__(self):
        return f"[{self.get_loai_de_xuat_display()}] {self.tieu_de}"

    def get_absolute_url(self):
        return reverse('workflow:proposal_detail', kwargs={'pk': self.pk})

    @transaction.atomic
    def move_to_next_step(self, handler, action, opinion="", next_approver=None):
        """
        Helper method thực hiện quy trình phê duyệt trong một Transaction duy nhất.
        Đảm bảo Log và Trạng thái luôn đồng bộ.
        """
        self.nguoi_duyet_hien_tai = next_approver
        
        if action == PheDuyetLog.Action.DUYET and next_approver is None:
            self.trang_thai = self.Status.DA_DUYET
        elif action == PheDuyetLog.Action.TU_CHOI:
            self.trang_thai = self.Status.TU_CHOI
        elif action == PheDuyetLog.Action.YEU_CAU_SUA:
            self.trang_thai = self.Status.YEU_CAU_SUA
        else:
            self.trang_thai = self.Status.CHO_DUYET
            
        self.save()
        
        # Ghi Log tự động
        return PheDuyetLog.objects.create(
            proposal=self,
            nguoi_xu_ly=handler,
            hanh_dong=action,
            y_kien=opinion,
            nguoi_nhan_tiep_theo=next_approver
        )


# ==============================================================================
# 3. NHẬT KÝ PHÊ DUYỆT (AUDIT TRAIL)
# ==============================================================================
class PheDuyetLog(models.Model):
    """Lịch sử chi tiết quá trình luân chuyển tờ trình."""
    
    class Action(models.TextChoices):
        GUI = 'GUI', _('Gửi trình')
        DUYET = 'DUYET', _('Phê duyệt')
        CHUYEN = 'CHUYEN', _('Trình lên cấp trên')
        TU_CHOI = 'TU_CHOI', _('Từ chối')
        YEU_CAU_SUA = 'YEU_CAU_SUA', _('Yêu cầu sửa lại')
    
    proposal = models.ForeignKey(
        Proposal, on_delete=models.CASCADE, 
        related_name='logs', verbose_name=_("Tờ trình")
    )
    nguoi_xu_ly = models.ForeignKey(NhanVien, on_delete=models.CASCADE, verbose_name=_("Người xử lý"))
    
    hanh_dong = models.CharField(_("Hành động"), max_length=20, choices=Action.choices)
    y_kien = models.TextField(_("Ý kiến chỉ đạo"), blank=True, null=True)
    
    nguoi_nhan_tiep_theo = models.ForeignKey(
        NhanVien, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='logs_incoming', 
        verbose_name=_("Người nhận tiếp theo")
    )
    
    thoi_gian = models.DateTimeField(_("Thời điểm xử lý"), auto_now_add=True)

    class Meta:
        verbose_name = _("Nhật ký phê duyệt")
        verbose_name_plural = _("03. Lịch sử Phê duyệt")
        ordering = ['thoi_gian']

    def __str__(self):
        return f"{self.nguoi_xu_ly} - {self.get_hanh_dong_display()} - {self.thoi_gian.strftime('%d/%m/%Y')}"