# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: operations/models.py
Author: Mr. Anh (CTO) & AI Assistant
Created Date: 2025-12-10
Updated Date: 2026-03-21
Description: Model quản lý Vận hành, Chấm công và Xử lý sự cố.
             UPGRADE PHASE 2: Chuyển đổi sang GeoDjango (PostGIS).
             - Tích hợp PointField cho định vị chính xác cao.
             - Gia cố Anti-fraud và GEOFENCING logic.
             - FIXED: Lỗi Migration ma_su_co (non-nullable error).
             - FIXED: Chuẩn hóa toàn bộ verbose_name_plural trong class Meta.
"""

import uuid
import logging
from datetime import datetime, timedelta
from django.contrib.gis.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from users.models import NhanVien
from clients.models import MucTieu

# Logger cho hệ thống vận hành SCMD
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. CẤU HÌNH VỊ TRÍ & CA TRỰC
# ==============================================================================

class ViTriChot(models.Model):
    """Định nghĩa các vị trí trực cụ thể tại mục tiêu (Cổng chính, Tuần tra, Giám sát...)"""
    muc_tieu = models.ForeignKey(
        MucTieu, 
        on_delete=models.CASCADE, 
        related_name="vi_tri_chot", 
        verbose_name=_("Mục tiêu bảo vệ"),
        help_text=_("Chọn khách hàng/mục tiêu quản lý vị trí trực này")
    )
    ten_vi_tri = models.CharField(
        _("Tên vị trí trực"), 
        max_length=255,
        help_text=_("VD: Cổng chính, Kho A, Tuần tra vòng ngoài")
    )

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
    ten_ca = models.CharField(
        _("Tên ca trực"), 
        max_length=100,
        help_text=_("VD: Ca 1 (06h-18h), Ca hành chính")
    )
    gio_bat_dau = models.TimeField(_("Giờ bắt đầu"))
    gio_ket_thuc = models.TimeField(_("Giờ kết thúc"))

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


class PhanCongManager(models.Manager):
    """Tối ưu hóa truy vấn bảng phân công nhằm giảm thiểu N+1 Query"""
    def get_queryset(self):
        return super().get_queryset().select_related(
            'nhan_vien', 
            'ca_lam_viec', 
            'vi_tri_chot__muc_tieu'
        )


class PhanCongCaTruc(models.Model):
    """Lịch trình phân công nhân sự cụ thể theo ngày và vị trí"""
    vi_tri_chot = models.ForeignKey(
        ViTriChot, 
        on_delete=models.CASCADE, 
        verbose_name=_("Vị trí chốt")
    )
    nhan_vien = models.ForeignKey(
        NhanVien, 
        on_delete=models.CASCADE, 
        verbose_name=_("Nhân viên thực hiện")
    )
    ca_lam_viec = models.ForeignKey(
        CaLamViec, 
        on_delete=models.CASCADE, 
        verbose_name=_("Ca trực")
    )
    ngay_truc = models.DateField(
        _("Ngày thực hiện"), 
        db_index=True,
        help_text=_("Định dạng chuẩn: Ngày/Tháng/Năm")
    )

    objects = PhanCongManager()

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

    # GEOFENCING VALIDATION
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

    ghi_chu = models.TextField(_("Ghi chú chấm công"), blank=True)

    class Meta:
        verbose_name = _("Dữ liệu Chấm công")
        verbose_name_plural = _("4. Dữ liệu Chấm công")

    # API Compatibility Helpers
    @property
    def lat_check_in(self):
        """Lấy vĩ độ từ PointField check-in"""
        try:
            return self.location_check_in.y if self.location_check_in else None
        except Exception:
            return None

    @property
    def long_check_in(self):
        """Lấy kinh độ từ PointField check-in"""
        try:
            return self.location_check_in.x if self.location_check_in else None
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

    tieu_de = models.CharField(
        _("Tiêu đề sự cố"), 
        max_length=200,
        help_text=_("Tóm tắt ngắn gọn sự việc xảy ra")
    )
    
    # FIXED: Bổ sung default và blank để vượt qua lỗi migration nullable
    ma_su_co = models.CharField(
        _("Mã vụ việc"), 
        max_length=50, 
        unique=True, 
        editable=False,
        default='PENDING',
        blank=True
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
        null=True, blank=True
    )
    ca_truc = models.ForeignKey(
        PhanCongCaTruc, 
        on_delete=models.SET_NULL, 
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

    def save(self, *args, **kwargs):
        """Tự động sinh mã sự cố định dạng chuẩn SCMD: SC-YYYYMMDD-HEX"""
        try:
            if not self.ma_su_co or self.ma_su_co == 'PENDING':
                date_part = timezone.now().strftime('%Y%m%d')
                unique_part = uuid.uuid4().hex[:6].upper()
                self.ma_su_co = f"SC-{date_part}-{unique_part}"
                
            if self.phai_thu_nhan_vien > 0 and self.trang_thai == 'DA_XU_LY':
                self.trang_thai = 'CHO_DEN_BU'
        except Exception as e:
            logger.error(f"Error in BaoCaoSuCo.save: {str(e)}")
            
        super().save(*args, **kwargs)

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

    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, verbose_name=_("Nhân viên đề xuất"))
    muc_tieu = models.ForeignKey(MucTieu, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Tại mục tiêu"))
    
    loai_de_xuat = models.CharField(_("Loại đề xuất"), max_length=20, choices=LoaiDeXuat.choices, default=LoaiDeXuat.KHAC)
    tieu_de = models.CharField(_("Tiêu đề ngắn gọn"), max_length=255)
    noi_dung = models.TextField(_("Nội dung trình bày chi tiết"))
    hinh_anh = models.ImageField(_("Hình ảnh/Tài liệu đính kèm"), upload_to="de_xuat/%Y/%m/", null=True, blank=True)
    
    trang_thai = models.CharField(_("Trạng thái phê duyệt"), max_length=20, choices=TrangThai.choices, default=TrangThai.CHO_CHI_HUY)
    ngay_gui = models.DateTimeField(_("Ngày gửi đề xuất"), default=timezone.now, db_index=True)
    
    chi_huy_duyet = models.ForeignKey(
        NhanVien, on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name="de_xuat_chi_huy_duyet", 
        verbose_name=_("Chỉ huy duyệt")
    )
    y_kien_chi_huy = models.TextField(_("Ý kiến của Chỉ huy"), blank=True, null=True)
    thoi_gian_chi_huy_duyet = models.DateTimeField(_("Thời điểm CH duyệt"), null=True, blank=True)
    
    nguoi_duyet_nghiep_vu = models.ForeignKey(
        NhanVien, on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name="de_xuat_nghiep_vu_duyet", 
        verbose_name=_("Nghiệp vụ duyệt")
    )
    y_kien_nghiep_vu = models.TextField(_("Ý kiến của Phòng nghiệp vụ"), blank=True, null=True)
    thoi_gian_nghiep_vu_duyet = models.DateTimeField(_("Thời điểm NV duyệt"), null=True, blank=True)

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

    class Meta:
        verbose_name = _("Kiểm tra quân số")
        verbose_name_plural = _("7. Lịch sử Alive Check")
        ordering = ['-created_at']

    def __str__(self): 
        try:
            return f"Alive Check: {self.ca_truc.nhan_vien.ho_ten} - {self.get_trang_thai_display()}"
        except Exception:
            return f"Alive Check {self.id}"