# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: users/forms.py
Author: Mr. Anh
Created Date: 2025-12-05
Description: Form xử lý dữ liệu người dùng.
             UPDATED: Bổ sung các trường định danh (CCCD, Ngày sinh, Giới tính) 
             để khắc phục lỗi hiển thị trên trang Profile Desktop.
"""

from django import forms
from .models import NhanVien

class UserProfileForm(forms.ModelForm):
    """Form cập nhật thông tin cá nhân"""
    class Meta:
        model = NhanVien
        # FIX: Bổ sung đầy đủ các trường cần hiển thị trên form
        fields = [
            'anh_the', 
            'sdt_chinh', 'email', 
            'ngay_sinh', 'gioi_tinh', 'so_cccd', 
            'dia_chi_thuong_tru', 'dia_chi_tam_tru', 
            'nguoi_lien_he_khan_cap', 'sdt_khan_cap', 
            'so_tai_khoan', 'ngan_hang'
        ]
        
        widgets = {
            # --- Nhóm Liên hệ ---
            'sdt_chinh': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'Nhập số điện thoại...'}),
            'email': forms.EmailInput(attrs={'class': 'input input-bordered w-full'}),
            
            # --- Nhóm Định danh (MỚI) ---
            # DateInput type='date' sẽ hiện lịch chọn ngày trên trình duyệt
            'ngay_sinh': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'gioi_tinh': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'so_cccd': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            
            # --- Nhóm Địa chỉ ---
            'dia_chi_thuong_tru': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'dia_chi_tam_tru': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            
            # --- Nhóm Khẩn cấp ---
            'nguoi_lien_he_khan_cap': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'sdt_khan_cap': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            
            # --- Nhóm Tài chính ---
            'so_tai_khoan': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'ngan_hang': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            
            # --- Ảnh thẻ ---
            'anh_the': forms.FileInput(attrs={'class': 'file-input file-input-bordered w-full'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Khóa trường Email (Không cho sửa)
        if 'email' in self.fields:
            self.fields['email'].disabled = True
            self.fields['email'].help_text = "Email là định danh hệ thống, không thể tự thay đổi."
            
        # 2. Khóa trường CCCD (Không cho sửa)
        if 'so_cccd' in self.fields:
            self.fields['so_cccd'].disabled = True
            self.fields['so_cccd'].help_text = "Vui lòng liên hệ bộ phận Nhân sự nếu cần cập nhật CCCD."