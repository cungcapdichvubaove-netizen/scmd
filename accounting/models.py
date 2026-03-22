# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: accounting/models.py
Author: Mr. Anh
Created Date: 2025-11-30
Description: Model quản lý Kế toán - Tiền lương (Core Payroll Models).
             BẢN MERGE: Giữ nguyên cấu trúc legacy, tối ưu hóa logic tính toán 
             và chuẩn hóa ngôn ngữ giao diện an ninh.
"""

from django.db import models, transaction
from django.utils import timezone
from django.core.validators import MinValueValidator
from users.models import NhanVien
from decimal import Decimal, ROUND_HALF_UP


class CauHinhLuong(models.Model):
    """Hồ sơ thiết lập các tham số lương và phụ cấp cố định cho từng nhân viên an ninh"""
    nhan_vien = models.OneToOneField(
        NhanVien, 
        on_delete=models.CASCADE, 
        related_name="cau_hinh_luong", 
        verbose_name="Nhân viên thụ hưởng"
    )
    
    # --- Dữ liệu kế thừa (Legacy) ---
    luong_co_ban_ngay = models.DecimalField(
        "Mức lương đóng BHXH", 
        max_digits=12, 
        decimal_places=0, 
        default=0,
        help_text="Mức lương căn bản dùng để tính bảo hiểm và các chế độ nhà nước."
    )
    
    # --- Hệ thống phụ cấp an ninh mới ---
    phu_cap_trach_nhiem = models.DecimalField(
        "Phụ cấp trách nhiệm", 
        max_digits=12, 
        decimal_places=0, 
        default=0,
        help_text="Phụ cấp dành cho các vị trí chỉ huy, đội trưởng, hoặc mục tiêu trọng yếu."
    )
    phu_cap_xang_xe = models.DecimalField(
        "Phụ cấp đi lại/Xăng xe", 
        max_digits=12, 
        decimal_places=0, 
        default=0,
        help_text="Hỗ trợ chi phí di chuyển giữa các mục tiêu bảo vệ."
    )
    phu_cap_an_uong = models.DecimalField(
        "Phụ cấp ăn ca", 
        max_digits=12, 
        decimal_places=0, 
        default=0,
        help_text="Hỗ trợ tiền ăn trực ca theo quy định của SCMD."
    )

    class Meta: 
        verbose_name = "Hồ sơ Lương cá nhân"
        verbose_name_plural = "Hồ sơ Lương cá nhân"

    def __str__(self): 
        return f"Cấu hình lương: {self.nhan_vien.ho_ten} ({self.nhan_vien.ma_nhan_vien})"


class BangLuongThang(models.Model):
    """Quản lý các kỳ lương tổng hợp hàng tháng của toàn hệ thống SCMD"""
    TRANG_THAI = [
        ('NHAP', 'Dự thảo (Đang tính toán)'),
        ('CHO_DUYET', 'Chờ Kế toán trưởng duyệt'),
        ('DA_PHAT_HANH', 'Đã duyệt & Phát hành (Nhân viên đã xem)'),
    ]
    
    ten_bang_luong = models.CharField(
        "Tên bảng lương", 
        max_length=200, 
        default="Bảng lương tháng ...",
        help_text="Ví dụ: Bảng lương mục tiêu Vincity - Tháng 03/2026"
    )
    thang = models.IntegerField(
        "Tháng lương", 
        default=timezone.now().month,
        validators=[MinValueValidator(1)]
    )
    nam = models.IntegerField(
        "Năm quyết toán", 
        default=timezone.now().year
    )
    ngay_chot_cong = models.DateField(
        "Ngày chốt dữ liệu công", 
        default=timezone.now,
        help_text="Ngày cuối cùng hệ thống ghi nhận giờ làm việc cho kỳ lương này."
    )
    trang_thai = models.CharField(
        "Trạng thái phê duyệt", 
        max_length=20, 
        choices=TRANG_THAI, 
        default='NHAP'
    )
    
    # --- Số liệu thống kê tổng hợp ---
    tong_chi_tra = models.DecimalField(
        "Tổng ngân sách chi trả", 
        max_digits=15, 
        decimal_places=0, 
        default=0,
        help_text="Tổng số tiền thực lĩnh của toàn bộ nhân viên trong kỳ."
    )
    tong_gio_cong = models.FloatField(
        "Tổng giờ công hệ thống", 
        default=0,
        help_text="Tổng hợp toàn bộ giờ làm việc của nhân sự trong tháng."
    )

    nguoi_duyet = models.ForeignKey(
        "users.NhanVien", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Người phê duyệt (KTT/GĐ)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo bảng kê")

    class Meta: 
        verbose_name = "Kỳ lương hệ thống"
        verbose_name_plural = "1. Quản lý Kỳ lương"
        unique_together = ('thang', 'nam')
        ordering = ['-nam', '-thang']

    def update_totals(self):
        """Tính toán lại tổng chi và tổng công dựa trên các phiếu lương chi tiết"""
        stats = self.chi_tiet.aggregate(
            total_pay=models.Sum('thuc_lanh'),
            total_hours=models.Sum('tong_gio_lam')
        )
        self.tong_chi_tra = stats.get('total_pay') or 0
        self.tong_gio_cong = stats.get('total_hours') or 0
        self.save()

    def __str__(self): 
        return f"Bảng lương SCMD - Tháng {self.thang}/{self.nam}"


class ChiTietLuong(models.Model):
    """Phiếu lương chi tiết cho từng cá nhân (Payslip). Lưu trữ dữ liệu tĩnh để đối soát lịch sử."""
    bang_luong = models.ForeignKey(
        BangLuongThang, 
        on_delete=models.CASCADE, 
        related_name="chi_tiet",
        verbose_name="Thuộc kỳ lương"
    )
    nhan_vien = models.ForeignKey(
        NhanVien, 
        on_delete=models.CASCADE,
        verbose_name="Nhân sự"
    )
    
    # --- Nhóm dữ liệu Chấm công ---
    tong_gio_lam = models.FloatField("Tổng giờ làm việc", default=0)
    so_ngay_nghi = models.IntegerField("Số ngày nghỉ phép/không lương", default=0)
    
    # --- Nhóm dữ liệu Thu nhập (Earnings) ---
    luong_chinh = models.DecimalField("Lương theo công trạng", max_digits=12, decimal_places=0, default=0)
    thuong_chuyen_can = models.DecimalField("Thưởng chuyên cần", max_digits=12, decimal_places=0, default=0)
    phu_cap_khac = models.DecimalField("Tổng phụ cấp khác", max_digits=12, decimal_places=0, default=0)
    
    # --- Nhóm dữ liệu Khấu trừ (Deductions) ---
    ung_luong = models.DecimalField("Khoản tạm ứng", max_digits=12, decimal_places=0, default=0)
    phat_vi_pham = models.DecimalField("Phạt kỷ luật/Vi phạm", max_digits=12, decimal_places=0, default=0)
    tien_dong_phuc = models.DecimalField("Tiền quân trang/Đồng phục", max_digits=12, decimal_places=0, default=0)
    tien_den_bu = models.DecimalField("Bồi thường thiệt hại (nếu có)", max_digits=12, decimal_places=0, default=0)
    bao_hiem = models.DecimalField("Khấu trừ BHXH/BHYT", max_digits=12, decimal_places=0, default=0)
    phi_cong_doan = models.DecimalField("Kinh phí Công đoàn", max_digits=12, decimal_places=0, default=0)
    
    # --- Kết quả quyết toán ---
    thuc_lanh = models.DecimalField("Thực lĩnh cuối kỳ", max_digits=12, decimal_places=0, default=0)
    ghi_chu = models.TextField("Ghi chú nghiệp vụ", blank=True, help_text="Giải trình các khoản thưởng/phạt đặc thù.")

    class Meta: 
        verbose_name = "Phiếu lương cá nhân"
        verbose_name_plural = "Phiếu lương cá nhân"
        unique_together = ('bang_luong', 'nhan_vien')

    @property
    def tong_thu_nhap(self):
        """Tổng các khoản tiền được nhận trước khi trừ phí"""
        return self.luong_chinh + self.thuong_chuyen_can + self.phu_cap_khac

    @property
    def tong_khau_tru(self):
        """Tổng các khoản tiền bị trừ vào lương"""
        return (self.ung_luong + self.phat_vi_pham + 
                self.tien_dong_phuc + self.tien_den_bu + 
                self.bao_hiem + self.phi_cong_doan)

    def save(self, *args, **kwargs):
        """Ghi đè phương thức save để chuẩn hóa Decimal và tự động quyết toán thực lĩnh"""
        
        def to_decimal_safe(val): 
            """Chuyển đổi dữ liệu sang Decimal an toàn cho nghiệp vụ kế toán"""
            try:
                if val is None: return Decimal('0')
                return Decimal(str(val)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            except (ValueError, TypeError):
                return Decimal('0')

        # 1. Đồng bộ và chuẩn hóa toàn bộ các trường tiền tệ
        fields_to_clean = [
            'luong_chinh', 'thuong_chuyen_can', 'phu_cap_khac',
            'ung_luong', 'phat_vi_pham', 'tien_dong_phuc',
            'tien_den_bu', 'bao_hiem', 'phi_cong_doan'
        ]
        for field in fields_to_clean:
            current_val = getattr(self, field)
            setattr(self, field, to_decimal_safe(current_val))

        # 2. Tính toán thực lĩnh: (Thu nhập) - (Khấu trừ)
        # Sử dụng thuộc tính đã được chuẩn hóa ở bước 1
        thu_nhap_tong = self.luong_chinh + self.thuong_chuyen_can + self.phu_cap_khac
        khau_tru_tong = (self.ung_luong + self.phat_vi_pham + self.tien_dong_phuc + 
                         self.tien_den_bu + self.bao_hiem + self.phi_cong_doan)
        
        self.thuc_lanh = thu_nhap_tong - khau_tru_tong
        
        # 3. Lưu dữ liệu với tính năng transaction để đảm bảo an toàn dữ liệu
        with transaction.atomic():
            super().save(*args, **kwargs)
            # 4. Kích hoạt cập nhật lại tổng số liệu trên Bảng Lương Tháng chủ quản
            self.bang_luong.update_totals()
    
    def __str__(self): 
        return f"Phiếu lương: {self.nhan_vien.ma_nhan_vien} | Thực nhận: {self.thuc_lanh:,.0f} VNĐ"