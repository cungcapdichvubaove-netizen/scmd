# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro
=======
Security Command (SCMD) System
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: inspection/models.py
Author: Mr. Anh (CTO)
Created Date: 2025-12-05
Description: Model quản lý Thanh tra, Tuần tra & Kỷ luật.
             IMPROVED: Thêm Validation logic, Properties tính toán và tối ưu Meta.
             Nâng cấp: Chuẩn hóa PEP8, tăng cường tính chuyên nghiệp cho UI.
"""

import uuid
import math
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from users.models import NhanVien
from clients.models import MucTieu
<<<<<<< HEAD
from core.managers import TenantAwareManager, TenantScopedModel
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


# ==============================================================================
# 1. MODULE TUẦN TRA (PATROL)
# ==============================================================================

<<<<<<< HEAD
class LoaiTuanTra(TenantScopedModel):
=======
class LoaiTuanTra(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Quy định tuyến tuần tra"""
    muc_tieu = models.ForeignKey(
        MucTieu, 
        on_delete=models.CASCADE, 
        verbose_name=_("Mục tiêu bảo vệ"), 
        null=True, 
        blank=True
    )
    ten_loai = models.CharField(_("Tên tuyến tuần tra"), max_length=255)
    mo_ta = models.TextField(_("Mô tả chi tiết lộ trình"), blank=True)
    thoi_gian_quy_dinh = models.IntegerField(
        _("Thời gian quy định (phút)"), 
        default=30, 
        help_text=_("Thời gian tiêu chuẩn để hoàn thành toàn bộ tuyến tuần tra")
    )
<<<<<<< HEAD
    yeu_cau_gps = models.BooleanField(
        _("Bắt buộc GPS khi tuần tra"),
        default=False,
        help_text=_("Nếu bật, mobile phải gửi tọa độ GPS hợp lệ khi quét checkpoint."),
    )

    objects = TenantAwareManager()
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    
    def __str__(self):
        return f"{self.ten_loai} ({self.muc_tieu.ten_muc_tieu if self.muc_tieu else 'Chung'})"
    
    class Meta: 
        verbose_name = _("Tuyến tuần tra")
        verbose_name_plural = _("1. Cấu hình Tuyến")
        ordering = ['muc_tieu', 'ten_loai']
<<<<<<< HEAD
        indexes = [models.Index(fields=["tenant_id", "muc_tieu", "ten_loai"], name="insp_ltt_tenant_mt_name_idx")]


class DiemTuanTra(TenantScopedModel):
=======


class DiemTuanTra(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Điểm Checkpoint kiểm soát trong tuyến"""
    loai_tuan_tra = models.ForeignKey(
        LoaiTuanTra, 
        on_delete=models.CASCADE, 
        related_name="cac_diem", 
        verbose_name=_("Thuộc tuyến")
    )
    ten_diem = models.CharField(_("Tên điểm kiểm soát"), max_length=255)
    ma_qr = models.CharField(_("Mã QR định danh"), max_length=100, unique=True)
    thu_tu = models.IntegerField(_("Thứ tự tuần tra"), default=1)
    
    vi_do = models.DecimalField(_("Vĩ độ (Latitude)"), max_digits=12, decimal_places=8, null=True, blank=True)
    kinh_do = models.DecimalField(_("Kinh độ (Longitude)"), max_digits=12, decimal_places=8, null=True, blank=True)
    ban_kinh_cho_phep = models.IntegerField(
        _("Bán kính sai lệch (m)"), 
        default=50, 
        help_text=_("Khoảng cách tối đa chấp nhận được so với tọa độ gốc")
    )

<<<<<<< HEAD
    objects = TenantAwareManager()

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    def __str__(self):
        return f"[{self.thu_tu}] {self.ten_diem}"
    
    class Meta: 
        ordering = ['loai_tuan_tra', 'thu_tu']
        verbose_name = _("Điểm kiểm soát")
        verbose_name_plural = _("Điểm kiểm soát")


<<<<<<< HEAD
class LuotTuanTra(TenantScopedModel):
=======
class LuotTuanTra(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Ghi nhận phiên thực hiện tuần tra của nhân viên"""
    TRANG_THAI = [
        ('DANG_DI', _('⏳ Đang thực hiện')), 
        ('HOAN_THANH', _('✅ Đã hoàn thành')), 
        ('BO_DO', _('❌ Bỏ dở/Không hoàn thành'))
    ]
    
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, verbose_name=_("Nhân viên thực hiện"))
    loai_tuan_tra = models.ForeignKey(LoaiTuanTra, on_delete=models.CASCADE, verbose_name=_("Tuyến tuần tra"))
    thoi_gian_bat_dau = models.DateTimeField(_("Thời điểm bắt đầu"), auto_now_add=True)
    thoi_gian_ket_thuc = models.DateTimeField(_("Thời điểm kết thúc"), null=True, blank=True)
    trang_thai = models.CharField(_("Trạng thái"), max_length=20, choices=TRANG_THAI, default='DANG_DI')
<<<<<<< HEAD
    phan_cong_ca_truc = models.ForeignKey(
        "operations.PhanCongCaTruc",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="luot_tuan_tra_bao_ve",
        verbose_name=_("Phân công ca trực liên quan"),
        help_text=_("Liên kết lượt tuần tra bảo vệ với ca trực vận hành."),
    )
    lich_tuan_tra_van_hanh = models.ForeignKey(
        "operations.LichTuanTraVanHanh",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="luot_tuan_tra_bao_ve",
        verbose_name=_("Lịch tuần tra vận hành"),
        help_text=_("Phase 2: truy vết lượt tuần tra về lịch tuần tra do operations tạo."),
    )
    nhiem_vu_tuan_tra_ca = models.ForeignKey(
        "operations.NhiemVuTuanTraCa",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="luot_tuan_tra_bao_ve",
        verbose_name=_("Nhiệm vụ tuần tra theo ca"),
        help_text=_("Phase 2: truy vết lượt tuần tra về nhiệm vụ cụ thể trong ca trực."),
    )
    TRANG_THAI_DOI_SOAT = [
        ("IN_PROGRESS", _("Đang thực hiện")),
        ("COMPLETED_VALID", _("Hoàn thành hợp lệ")),
        ("COMPLETED_WITH_WARNINGS", _("Hoàn thành có cảnh báo")),
        ("MISSED", _("Bỏ lượt/thiếu điểm")),
        ("CANCELLED_WITH_REASON", _("Đã hủy có lý do")),
    ]
    trang_thai_doi_soat = models.CharField(
        _("Trạng thái đối soát tuần tra"),
        max_length=32,
        choices=TRANG_THAI_DOI_SOAT,
        default="IN_PROGRESS",
        db_index=True,
        help_text=_("Không dùng HOAN_THANH đơn thuần để suy ra hoàn thành hợp lệ."),
    )
    so_diem_bat_buoc = models.PositiveIntegerField(_("Số điểm bắt buộc"), default=0)
    so_diem_da_quet = models.PositiveIntegerField(_("Số điểm đã quét"), default=0)
    so_diem_canh_bao = models.PositiveIntegerField(_("Số điểm có cảnh báo"), default=0)
    
    objects = TenantAwareManager()

=======
    
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    @property
    def tien_do(self):
        """Tính % hoàn thành dựa trên số điểm đã quét thực tế"""
        try:
            tong = self.loai_tuan_tra.cac_diem.count()
            if tong == 0:
                return 0
            da_di = self.ghi_nhan.count()
            return min(int((da_di / tong) * 100), 100)
        except Exception:
            return 0

    @property
    def thoi_gian_thuc_hien(self):
        """Tính tổng thời gian thực hiện tuần tra (phút)"""
        if self.thoi_gian_ket_thuc and self.thoi_gian_bat_dau:
            delta = self.thoi_gian_ket_thuc - self.thoi_gian_bat_dau
            return round(delta.total_seconds() / 60, 1)
        return 0

    def clean(self):
        """Kiểm tra tính hợp lệ của dữ liệu thời gian"""
        if self.thoi_gian_ket_thuc and self.thoi_gian_bat_dau:
            if self.thoi_gian_ket_thuc < self.thoi_gian_bat_dau:
                raise ValidationError(_("Lỗi: Thời gian kết thúc không được trước thời gian bắt đầu."))

    def __str__(self):
        time_str = self.thoi_gian_bat_dau.astimezone().strftime('%H:%M %d/%m/%Y')
        return f"{self.nhan_vien.ho_ten} - {time_str}"

    class Meta: 
        verbose_name = _("Lượt tuần tra")
        verbose_name_plural = _("2. Nhật ký Tuần tra")
        ordering = ['-thoi_gian_bat_dau']
<<<<<<< HEAD
        indexes = [models.Index(fields=["tenant_id", "trang_thai", "thoi_gian_bat_dau"], name="insp_luot_tenant_state_dt_idx")]


class GhiNhanTuanTra(TenantScopedModel):
=======


class GhiNhanTuanTra(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Chi tiết từng điểm quét QR trong một lượt tuần tra"""
    KET_QUA_GPS = [
        ('HOP_LE', _('🟢 Hợp lệ')), 
        ('CANH_BAO_XA', _('🟡 Cảnh báo (Ngoài bán kính)')), 
        ('MAT_GPS', _('⚪ Không có tín hiệu GPS')), 
        ('GIAN_LAN', _('🔴 Nghi vấn gian lận'))
    ]

    luot_tuan_tra = models.ForeignKey(
        LuotTuanTra, 
        on_delete=models.CASCADE, 
        related_name="ghi_nhan",
        verbose_name=_("Lượt tuần tra")
    )
    diem_tuan_tra = models.ForeignKey(DiemTuanTra, on_delete=models.CASCADE, verbose_name=_("Điểm kiểm soát"))
    thoi_gian_quet = models.DateTimeField(_("Thời gian quét"), auto_now_add=True)
    
    lat_thuc_te = models.DecimalField(_("Vĩ độ thực tế"), max_digits=12, decimal_places=8, null=True, blank=True)
    lng_thuc_te = models.DecimalField(_("Kinh độ thực tế"), max_digits=12, decimal_places=8, null=True, blank=True)
    khoang_cach = models.FloatField(_("Độ lệch khoảng cách (m)"), default=0.0)
    ket_qua = models.CharField(_("Kết quả xác thực"), max_length=20, choices=KET_QUA_GPS, default='HOP_LE')
    
    toa_do = models.CharField(_("Chuỗi tọa độ"), max_length=100, null=True, blank=True)
    hinh_anh_xac_thuc = models.ImageField(_("Hình ảnh xác thực"), upload_to="tuan_tra/%Y/%m/", null=True, blank=True)
    ghi_chu = models.TextField(_("Ghi chú nghiệp vụ"), blank=True)

<<<<<<< HEAD
    objects = TenantAwareManager()

    class Meta: 
        ordering = ['thoi_gian_quet']
        indexes = [models.Index(fields=["tenant_id", "thoi_gian_quet"], name="insp_gn_tenant_scan_idx")]
        verbose_name = _("Chi tiết quét QR")
        verbose_name_plural = _("Chi tiết Quét QR")
        constraints = [
            models.UniqueConstraint(
                fields=["luot_tuan_tra", "diem_tuan_tra"],
                name="uq_patrol_evidence_once_per_checkpoint",
            ),
        ]
=======
    class Meta: 
        ordering = ['thoi_gian_quet']
        verbose_name = _("Chi tiết quét QR")
        verbose_name_plural = _("Chi tiết Quét QR")
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


# ==============================================================================
# 2. MODULE THANH TRA & KỶ LUẬT
# ==============================================================================

<<<<<<< HEAD
class HangMucKiemTra(TenantScopedModel):
=======
class HangMucKiemTra(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Các tiêu chí chấm điểm khi thanh tra mục tiêu"""
    ten_hang_muc = models.CharField(_("Tên hạng mục kiểm tra"), max_length=255)
    mo_ta = models.TextField(_("Tiêu chuẩn đánh giá"), blank=True)
    
<<<<<<< HEAD
    objects = TenantAwareManager()

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    def __str__(self):
        return self.ten_hang_muc

    class Meta: 
        verbose_name = _("Hạng mục kiểm tra")
        verbose_name_plural = _("Cấu hình Hạng mục Thanh tra")


<<<<<<< HEAD
class BienBanThanhTra(TenantScopedModel):
=======
class BienBanThanhTra(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Biên bản ghi lại kết quả thanh tra hiện trường"""
    thanh_tra_vien = models.ForeignKey(
        NhanVien, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_("Thanh tra viên thực hiện")
    )
    muc_tieu = models.ForeignKey(
        MucTieu, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_("Mục tiêu thanh tra")
    )
    thoi_gian = models.DateTimeField(_("Thời điểm thanh tra"), default=timezone.now)
    ket_luan = models.TextField(_("Kết luận chung của đoàn"), blank=True)
    diem_danh_gia = models.IntegerField(_("Tổng điểm đánh giá"), default=100)

<<<<<<< HEAD
    objects = TenantAwareManager()

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    def __str__(self):
        return f"BB-{self.id} ({self.muc_tieu})"

    class Meta: 
        ordering = ['-thoi_gian']
        verbose_name = _("Biên bản thanh tra")
        verbose_name_plural = _("Biên bản thanh tra")


<<<<<<< HEAD
class KetQuaKiemTra(TenantScopedModel):
=======
class KetQuaKiemTra(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Chi tiết kết quả theo từng hạng mục trong biên bản"""
    bien_ban = models.ForeignKey(BienBanThanhTra, on_delete=models.CASCADE, related_name="chi_tiet")
    hang_muc = models.ForeignKey(HangMucKiemTra, on_delete=models.CASCADE, verbose_name=_("Hạng mục"))
    dat_yeu_cau = models.BooleanField(_("Đạt yêu cầu?"), default=True)
    ghi_chu = models.TextField(_("Ghi chú chi tiết"), blank=True)

<<<<<<< HEAD
    objects = TenantAwareManager()

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    class Meta:
        verbose_name = _("Kết quả kiểm tra chi tiết")
        verbose_name_plural = _("Kết quả kiểm tra chi tiết")


<<<<<<< HEAD
class BuoiHuanLuyen(TenantScopedModel):
=======
class BuoiHuanLuyen(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Ghi nhận đào tạo nội bộ và điều lệnh"""
    chu_de = models.CharField(_("Chủ đề đào tạo"), max_length=255, null=True, blank=True)
    nguoi_dao_tao = models.ForeignKey(
        NhanVien, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name=_("Giảng viên/Người phụ trách")
    )
    thoi_gian = models.DateTimeField(_("Thời gian tổ chức"), default=timezone.now)
    dia_diem = models.CharField(_("Địa điểm huấn luyện"), max_length=255, null=True, blank=True)
    danh_sach_tham_gia = models.ManyToManyField(
        NhanVien, 
        related_name='cac_buoi_huan_luyen', 
        blank=True,
        verbose_name=_("Danh sách nhân viên tham gia")
    )
    
<<<<<<< HEAD
    objects = TenantAwareManager()

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    def __str__(self):
        return self.chu_de or "Buổi huấn luyện"

    class Meta: 
        ordering = ['-thoi_gian']
        verbose_name = _("Buổi huấn luyện")
        verbose_name_plural = _("Buổi huấn luyện")


# ==============================================================================
# 3. MODULE VI PHẠM (MOBILE APP)
# ==============================================================================

<<<<<<< HEAD
class BienBanViPham(TenantScopedModel):
=======
class BienBanViPham(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Ghi nhận các lỗi kỷ luật của nhân viên tại mục tiêu"""
    LOAI_LOI = [
        ('NGU_GAT', _('😴 Ngủ gật trong ca trực')), 
        ('ROI_VI_TRI', _('🏃 Rời bỏ vị trí không lý do')), 
        ('DUNG_DIEN_THOAI', _('📱 Sử dụng điện thoại sai quy định')), 
        ('KHONG_DONG_PHUC', _('👔 Sai quy định đồng phục/Tác phong')), 
        ('KHAC', _('📝 Các lỗi vi phạm khác'))
    ]
    TRANG_THAI_XL = [
        ('CHO_DUYET', _('⏳ Đang chờ phê duyệt')), 
        ('DA_DUYET', _('✅ Đã phê duyệt xử lý')), 
        ('TU_CHOI', _('❌ Đã hủy bỏ/Từ chối'))
    ]
    HINH_THUC = [
        ('NHAC_NHO', _('Nhắc nhở')), 
        ('CANH_CAO', _('Cảnh cáo')), 
        ('PHAT_TIEN', _('Phạt tiền (Trừ lương)')), 
        ('DINH_CHI', _('Đình chỉ công tác'))
    ]

    ma_bien_ban = models.CharField(_("Mã biên bản"), max_length=50, unique=True, editable=False)
    doi_tuong_vi_pham = models.ForeignKey(
        NhanVien, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="cac_loi_vi_pham", 
        verbose_name=_("Nhân viên vi phạm")
    )
    nguoi_lap = models.ForeignKey(
        NhanVien, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="cac_bb_da_lap", 
        verbose_name=_("Cán bộ lập biên bản")
    )
    muc_tieu = models.ForeignKey(
        MucTieu, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_("Địa điểm (Mục tiêu)")
    )
    
    ngay_vi_pham = models.DateTimeField(_("Thời điểm phát hiện vi phạm"), default=timezone.now)
    loai_loi = models.CharField(_("Hành vi vi phạm"), max_length=50, choices=LOAI_LOI, default='NGU_GAT')
    mo_ta = models.TextField(_("Mô tả diễn biến chi tiết"), blank=True)
    bang_chung_anh = models.ImageField(_("Hình ảnh bằng chứng"), upload_to="vipham/%Y/%m/", null=True, blank=True)
    
    hinh_thuc_xu_ly = models.CharField(_("Hình thức xử lý kỷ luật"), max_length=20, choices=HINH_THUC, default='PHAT_TIEN')
    so_tien_phat = models.DecimalField(
        _("Số tiền phạt dự kiến"), 
        max_digits=12, 
        decimal_places=0, 
        default=0, 
        help_text=_("Nhập số tiền áp dụng cho hình thức Phạt tiền")
    )
    trang_thai = models.CharField(_("Trạng thái hồ sơ"), max_length=20, choices=TRANG_THAI_XL, default='CHO_DUYET')
    
    created_at = models.DateTimeField(_("Ngày tạo hồ sơ"), auto_now_add=True)

<<<<<<< HEAD
    objects = TenantAwareManager()

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    def save(self, *args, **kwargs):
        """Tự động phát sinh mã biên bản theo định dạng chuẩn SCMD"""
        if not self.ma_bien_ban:
            prefix = "VP"
            date_str = timezone.now().strftime('%Y%m%d')
            unique_id = uuid.uuid4().hex[:4].upper()
            self.ma_bien_ban = f"{prefix}-{date_str}-{unique_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        name = self.doi_tuong_vi_pham.ho_ten if self.doi_tuong_vi_pham else "N/A"
        return f"{self.ma_bien_ban} - {name}"

    class Meta: 
        verbose_name = _("Biên bản Vi phạm")
        verbose_name_plural = _("4. Quản lý Vi phạm")
        ordering = ['-created_at']
<<<<<<< HEAD
        indexes = [models.Index(fields=["tenant_id", "trang_thai", "ngay_vi_pham"], name="insp_vp_tenant_state_dt_idx")]


class DotThanhTra(TenantScopedModel):
=======


class DotThanhTra(models.Model):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    """Nhật ký thanh tra nhanh qua Mobile App (Checklist thực địa)"""
    KET_QUA = [
        ('DAT', _('✅ Đạt yêu cầu vận hành')), 
        ('KHONG_DAT', _('❌ Không đạt yêu cầu'))
    ]
    
    can_bo = models.ForeignKey(NhanVien, on_delete=models.CASCADE, verbose_name=_("Cán bộ kiểm tra"))
    muc_tieu = models.ForeignKey(MucTieu, on_delete=models.CASCADE, verbose_name=_("Mục tiêu bảo vệ"))
    thoi_gian_den = models.DateTimeField(_("Thời gian bắt đầu kiểm tra"), default=timezone.now)
    
    quan_so_bao_cao = models.IntegerField(_("Quân số (Theo lịch trực)"), default=0)
    quan_so_thuc_te = models.IntegerField(_("Quân số (Thực tế có mặt)"), default=0)
    
    kiem_tra_so_sach = models.BooleanField(_("Kiểm tra Sổ sách bàn giao?"), default=True)
    kiem_tra_dong_phuc = models.BooleanField(_("Kiểm tra Đồng phục/Tác phong?"), default=True)
    kiem_tra_cong_cu = models.BooleanField(_("Kiểm tra Công cụ hỗ trợ?"), default=True)
    
    danh_gia_chung = models.TextField(_("Nhận xét/Kiến nghị"), blank=True)
    ket_qua = models.CharField(_("Kết luận thanh tra"), max_length=20, choices=KET_QUA, default='DAT')
    hinh_anh_tong_quan = models.ImageField(_("Ảnh chụp tổng quan hiện trường"), upload_to="thanhtra/%Y/%m/", null=True, blank=True)

<<<<<<< HEAD
    objects = TenantAwareManager()

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    def __str__(self):
        return f"{self.can_bo.ho_ten} kiểm tra {self.muc_tieu.ten_muc_tieu}"

    class Meta: 
        verbose_name = _("Nhật ký Thanh tra Mobile")
        verbose_name_plural = _("3. Nhật ký Thanh tra Mobile") 
        ordering = ['-thoi_gian_den']