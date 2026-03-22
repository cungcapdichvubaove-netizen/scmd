# file: accounting/models_soquy.py
# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: accounting/models_soquy.py
Author: Mr. Anh
Created Date: 2025-11-30
Description: Model quản lý Sổ Quỹ (Thu/Chi) với quy trình Duyệt.
"""

from django.db import models
from django.utils import timezone
from users.models import NhanVien
from clients.models import HopDong

class SoQuy(models.Model):
    LOAI_PHIEU = [('THU', 'Phiếu Thu'), ('CHI', 'Phiếu Chi')]
    HANG_MUC = [
        ('TAM_UNG', 'Chi tạm ứng lương'),
        ('LUONG', 'Chi trả lương tháng'),
        ('PHI_DV', 'Thu phí dịch vụ (Khách hàng)'),
        ('MUA_SAM', 'Chi mua sắm vật tư'),
        ('KHAC', 'Thu chi khác'),
    ]
    # TRẠNG THÁI DUYỆT
    TRANG_THAI = [
        ('NHAP', 'Bản nháp'),
        ('CHO_DUYET', 'Chờ KTT duyệt'),
        ('DA_DUYET', 'Đã duyệt'),
        ('TU_CHOI', 'Từ chối'),
    ]

    ma_phieu = models.CharField("Mã phiếu", max_length=50, unique=True)
    loai_phieu = models.CharField("Loại", max_length=10, choices=LOAI_PHIEU)
    hang_muc = models.CharField("Hạng mục", max_length=20, choices=HANG_MUC)
    so_tien = models.DecimalField("Số tiền", max_digits=15, decimal_places=0)
    ngay_lap = models.DateTimeField("Ngày lập", default=timezone.now)
    
    # Đối tượng
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Nhân viên")
    hop_dong = models.ForeignKey(HopDong, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Hợp đồng KH")
    
    dien_giai = models.TextField("Diễn giải")
    chung_tu_goc = models.ImageField("Ảnh chứng từ", upload_to="ketoan/chungtu/", null=True, blank=True)
    
    # Thông tin phê duyệt
    trang_thai = models.CharField("Trạng thái", max_length=20, choices=TRANG_THAI, default='NHAP')
    nguoi_lap = models.ForeignKey("users.NhanVien", on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_phieu_lap", verbose_name="Người lập")
    nguoi_duyet = models.ForeignKey("users.NhanVien", on_delete=models.SET_NULL, null=True, blank=True, related_name="cac_phieu_duyet", verbose_name="Kế toán trưởng duyệt")

    class Meta: verbose_name = "Sổ Thu Chi"; verbose_name_plural = "Sổ Quỹ Tiền Mặt/Ngân Hàng"; ordering = ['-ngay_lap']
    def __str__(self): return f"{self.ma_phieu} - {self.so_tien:,.0f}"