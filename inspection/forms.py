# -*- coding: utf-8 -*-
from django import forms
from .models import BienBanViPham, DotThanhTra

class BienBanViPhamForm(forms.ModelForm):
    class Meta:
        model = BienBanViPham
        fields = ['doi_tuong_vi_pham', 'loai_loi', 'hinh_thuc_xu_ly', 'so_tien_phat', 'mo_ta', 'bang_chung_anh']
        widgets = {
            'doi_tuong_vi_pham': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'loai_loi': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'hinh_thuc_xu_ly': forms.Select(attrs={'class': 'select select-bordered w-full', 'onchange': 'toggleTienPhat(this)'}),
            'so_tien_phat': forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'Nhập số tiền (nếu phạt)'}),
            'mo_ta': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3, 'placeholder': 'Mô tả chi tiết...'}),
            'bang_chung_anh': forms.FileInput(attrs={'class': 'file-input file-input-bordered w-full'}),
        }

class DotThanhTraForm(forms.ModelForm):
    class Meta:
        model = DotThanhTra
        fields = ['quan_so_thuc_te', 'kiem_tra_so_sach', 'kiem_tra_dong_phuc', 'kiem_tra_cong_cu', 'ket_qua', 'danh_gia_chung', 'hinh_anh_tong_quan']
        widgets = {
            'quan_so_thuc_te': forms.NumberInput(attrs={'class': 'input input-bordered w-full font-bold text-center text-lg'}),
            'danh_gia_chung': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'ket_qua': forms.Select(attrs={'class': 'select select-bordered w-full font-bold'}),
            'hinh_anh_tong_quan': forms.FileInput(attrs={'class': 'file-input file-input-bordered w-full'}),
        }