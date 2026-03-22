# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: operations/forms.py
Author: Mr. Anh
Created Date: 2025-12-01
Description: Cập nhật BaoCaoSuCoForm để tiêu đề linh hoạt hơn.

NOTICE: This file is part of a proprietary system.
"""

from django import forms
from .models import BaoCaoSuCo, BaoCaoDeXuat

class BaoCaoSuCoForm(forms.ModelForm):
    class Meta:
        model = BaoCaoSuCo
        fields = ['tieu_de', 'muc_tieu', 'muc_do', 'mo_ta_chi_tiet', 'hinh_anh_1', 'hinh_anh_2', 'file_ghi_am']
        widgets = {
            'tieu_de': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'Tiêu đề (Tự động điền...)'}),
            'muc_tieu': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'muc_do': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'mo_ta_chi_tiet': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 4, 'placeholder': 'Mô tả chi tiết (Bấm micro để nói)...'}),
            'hinh_anh_1': forms.FileInput(attrs={'class': 'file-input file-input-bordered w-full'}),
            'hinh_anh_2': forms.FileInput(attrs={'class': 'file-input file-input-bordered w-full'}),
            'file_ghi_am': forms.FileInput(attrs={'class': 'hidden'}),
        }

    def __init__(self, *args, **kwargs):
        super(BaoCaoSuCoForm, self).__init__(*args, **kwargs)
        # Giảm bớt ràng buộc để Frontend tự xử lý logic điền
        self.fields['muc_do'].required = False
        self.fields['muc_tieu'].required = False
        self.fields['mo_ta_chi_tiet'].required = False
        self.fields['file_ghi_am'].required = False
        # V2.3: Cho phép tiêu đề để trống (Backend sẽ tự xử lý nếu thiếu)
        self.fields['tieu_de'].required = False 

class BaoCaoDeXuatForm(forms.ModelForm):
    class Meta:
        model = BaoCaoDeXuat
        fields = ['tieu_de', 'noi_dung']
        widgets = {
            'tieu_de': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'noi_dung': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full h-32'}),
        }