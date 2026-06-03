# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: mobile/serializers.py
Author: AI Assistant
Created Date: 2026-05-16
Description: Serializers for SCMD Mobile Application.
             Ensures data is formatted for mobile display and adheres to security rules.
"""

from rest_framework import serializers
from users.models import NhanVien
from operations.models import PhanCongCaTruc, ChamCong, BaoCaoSuCo, ViTriChot, CaLamViec
from clients.models import MucTieu

class MobileNhanVienSerializer(serializers.ModelSerializer):
    """
    Serializer cho thông tin nhân viên trên Mobile App.
    Loại bỏ các trường nhạy cảm theo Rule 9 của .cursorrules.
    """
    class Meta:
        model = NhanVien
        fields = [
            'id', 'ma_nhan_vien', 'ho_ten', 'anh_the', 'avatar_url',
            'chuc_danh', 'phong_ban', 'sdt_chinh',
            'ngay_vao_lam', 'trang_thai_lam_viec',
        ]
        read_only_fields = [
            'ma_nhan_vien', 'ho_ten', 'avatar_url', 'chuc_danh', 'phong_ban',
            'ngay_vao_lam', 'trang_thai_lam_viec'
        ]

class MobileMucTieuSerializer(serializers.ModelSerializer):
    """Serializer cho thông tin mục tiêu."""
    class Meta:
        model = MucTieu
        fields = ['id', 'ten_muc_tieu', 'dia_chi', 'vi_do', 'kinh_do', 'ban_kinh_cho_phep']

class MobileViTriChotSerializer(serializers.ModelSerializer):
    """Serializer cho thông tin vị trí chốt."""
    muc_tieu = MobileMucTieuSerializer(read_only=True)
    class Meta:
        model = ViTriChot
        fields = ['id', 'ten_vi_tri', 'muc_tieu']

class MobileCaLamViecSerializer(serializers.ModelSerializer):
    """Serializer cho thông tin ca làm việc."""
    class Meta:
        model = CaLamViec
        fields = ['id', 'ten_ca', 'gio_bat_dau', 'gio_ket_thuc']

class MobileChamCongSerializer(serializers.ModelSerializer):
    """
    Serializer cho dữ liệu chấm công trên Mobile App.
    Loại bỏ các trường Anti-fraud/PII kỹ thuật theo Rule 9.
    """
    class Meta:
        model = ChamCong
        fields = [
            'thoi_gian_check_in', 'thoi_gian_check_out', 'anh_check_in', 'anh_check_out',
            'location_check_in', 'location_check_out',
            'vi_tri_hop_le', 'khoang_cach_check_in',
            'thuc_lam_gio', 'di_muon_phut', 've_som_phut', 'ghi_chu'
        ]
        read_only_fields = [
            'thuc_lam_gio', 'di_muon_phut', 've_som_phut'
        ]

class MobilePhanCongCaTrucSerializer(serializers.ModelSerializer):
    """
    Serializer cho phân công ca trực trên Mobile App.
    Bao gồm các serializer lồng ghép đã được làm sạch.
    """
    nhan_vien = MobileNhanVienSerializer(read_only=True)
    vi_tri_chot = MobileViTriChotSerializer(read_only=True)
    ca_lam_viec = MobileCaLamViecSerializer(read_only=True)
    cham_cong = MobileChamCongSerializer(source='chamcong', read_only=True)
    trang_thai = serializers.SerializerMethodField()

    class Meta:
        model = PhanCongCaTruc
        fields = [
            'id', 'ngay_truc', 'nhan_vien', 'vi_tri_chot', 'ca_lam_viec',
            'cham_cong', 'trang_thai', 'da_checkin'
        ]

    def get_trang_thai(self, obj):
        if not hasattr(obj, 'chamcong'):
            return "CHUA_CHECKIN"
        cc = obj.chamcong
        if cc.thoi_gian_check_in and not cc.thoi_gian_check_out:
            return "DANG_LAM_VIEC"
        if cc.thoi_gian_check_out:
            return "HOAN_THANH"
        return "CHUA_CHECKIN"

class MobileBaoCaoSuCoSerializer(serializers.ModelSerializer):
    """
    Serializer cho báo cáo sự cố trên Mobile App.
    Loại bỏ các trường tài chính/HR nhạy cảm theo Rule 9.
    """
    nhan_vien_bao_cao = MobileNhanVienSerializer(read_only=True)
    muc_tieu = MobileMucTieuSerializer(read_only=True)
    muc_tieu_id = serializers.PrimaryKeyRelatedField(
        source='muc_tieu',
        queryset=MucTieu.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )
    ca_truc_id = serializers.PrimaryKeyRelatedField(
        source='ca_truc',
        queryset=PhanCongCaTruc.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = BaoCaoSuCo
        fields = [
            'id', 'tieu_de', 'ma_su_co', 'nhan_vien_bao_cao', 'muc_tieu',
            'muc_tieu_id', 'ca_truc_id', 'thoi_gian_phat_hien', 'mo_ta_chi_tiet', 'hinh_anh_1', 'hinh_anh_2',
            'file_ghi_am', 'muc_do', 'trang_thai',
            'nguoi_xu_ly', 'ghi_chu_quan_ly', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'ma_su_co', 'trang_thai', 'nguoi_xu_ly', 'created_at', 'updated_at',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None) or not request.user.is_authenticated:
            self.fields['muc_tieu_id'].queryset = MucTieu.objects.none()
            self.fields['ca_truc_id'].queryset = PhanCongCaTruc.objects.none()
            return

        nhan_vien = getattr(request.user, 'nhan_vien', None)
        if nhan_vien is None:
            self.fields['muc_tieu_id'].queryset = MucTieu.objects.none()
            self.fields['ca_truc_id'].queryset = PhanCongCaTruc.objects.none()
            return

        assigned_shifts = PhanCongCaTruc.objects.filter(nhan_vien=nhan_vien).select_related('vi_tri_chot__muc_tieu')
        assigned_target_ids = assigned_shifts.values_list('vi_tri_chot__muc_tieu_id', flat=True).distinct()
        self.fields['ca_truc_id'].queryset = assigned_shifts
        self.fields['muc_tieu_id'].queryset = MucTieu.objects.filter(id__in=assigned_target_ids)
