# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: clients/models.py
Author: Mr. Anh
Created Date: 2025-11-30
Description: Model quản lý Khách hàng, Hợp đồng & Mục tiêu.
             Đã nâng cấp: Cấu hình Lương ĐỘNG theo số ngày thực tế của tháng.

NOTICE: This file is part of a proprietary system. 
Unauthorized copying of this file, via any medium is strictly prohibited.
"""

import calendar  # Thư viện để tính ngày trong tháng
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator


class KhachHangTiemNang(models.Model):
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

    def __str__(self):
        return f"{self.ten_cong_ty} ({self.get_trang_thai_display()})"

    class Meta:
        verbose_name = "Khách hàng & Leads"
        verbose_name_plural = "1. Danh sách Khách hàng"
        ordering = ['-ngay_tao']


class CoHoiKinhDoanh(models.Model):
    """Quản lý Pipeline cơ hội kinh doanh từ khách hàng tiềm năng"""
    class TrangThai(models.TextChoices):
        MOI = "MOI", "Mới tiếp nhận"
        LIEN_HE = "LIENHE", "Đang liên hệ"
        GUI_BAO_GIA = "BAOGIA", "Đã báo giá"
        THUONG_LUONG = "THUONGLUONG", "Đang thương thảo"
        THANH_CONG = "THANHCONG", "Chốt hợp đồng (Thắng)"
        THAT_BAI = "THATBAI", "Thất bại (Thua)"

    khach_hang_tiem_nang = models.ForeignKey(
        KhachHangTiemNang, 
        on_delete=models.CASCADE, 
        verbose_name="Khách hàng liên quan"
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
        verbose_name="Nhân viên Sales phụ trách"
    )
    ngay_tao = models.DateTimeField(
        "Ngày tạo cơ hội",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Cơ hội Kinh doanh"
        verbose_name_plural = "2. Pipeline (Cơ hội)"

    def __str__(self):
        return f"{self.ten_co_hoi} - {self.get_trang_thai_display()}"


class HopDong(models.Model):
    """Quản lý hợp đồng dịch vụ bảo vệ chính thức của SCMD"""
    TRANG_THAI_HD = [
        ('HIEU_LUC', 'Đang hiệu lực'),
        ('SAP_HET_HAN', 'Sắp hết hạn (Dưới 30 ngày)'),
        ('DA_THANH_LY', 'Đã thanh lý/Hết hạn'),
    ]
    
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

    class Meta:
        verbose_name = "Hợp đồng Dịch vụ"
        verbose_name_plural = "3. Quản lý Hợp đồng"

    def save(self, *args, **kwargs):
        """Tự động cập nhật trạng thái hợp đồng dựa trên ngày hết hạn thực tế"""
        try:
            today = timezone.now().date()
            if self.trang_thai != 'DA_THANH_LY':
                if self.ngay_het_han < today:
                    self.trang_thai = 'DA_THANH_LY'
                elif self.ngay_het_han <= today + timedelta(days=30):
                    self.trang_thai = 'SAP_HET_HAN'
                else:
                    self.trang_thai = 'HIEU_LUC'
        except Exception:
            pass  # Đảm bảo phương thức save gốc vẫn chạy nếu có lỗi tính toán ngày
        super().save(*args, **kwargs)

    def __str__(self):
        return f"HĐ: {self.so_hop_dong}"


class MucTieu(models.Model):
    """Điểm trực và cấu hình nghiệp vụ tại mục tiêu bảo vệ cụ thể"""
    hop_dong = models.ForeignKey(
        HopDong,
        on_delete=models.CASCADE,
        related_name="muc_tieu",
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
    so_gio_mot_ngay = models.FloatField(
        "Định mức giờ trực/ngày", 
        default=12.0, 
        help_text="Số giờ ca trực tiêu chuẩn. Hệ thống sẽ tự nhân với số ngày trong tháng (28/30/31)."
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

    class Meta:
        verbose_name = "Mục tiêu Bảo vệ"
        verbose_name_plural = "4. Danh sách Mục tiêu"

    def __str__(self):
        return self.ten_muc_tieu
    
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