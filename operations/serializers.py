# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: operations/serializers.py
Author: Mr. Anh
Created Date: 2025-12-10
Description: Chuyển đổi dữ liệu (Serializer).
             FIXED: Thêm Alias để tương thích ngược với API Views cũ.
"""

from rest_framework import serializers
from .models import PhanCongCaTruc, ChamCong, BaoCaoSuCo, ViTriChot, CaLamViec
from clients.models import MucTieu

class MucTieuSerializer(serializers.ModelSerializer):
    class Meta:
        model = MucTieu
        fields = ['id', 'ten_muc_tieu', 'dia_chi', 'vi_do', 'kinh_do', 'ban_kinh_cho_phep']

class ViTriChotSerializer(serializers.ModelSerializer):
    muc_tieu = MucTieuSerializer(read_only=True)
    class Meta:
        model = ViTriChot
        fields = ['id', 'ten_vi_tri', 'muc_tieu']

class CaLamViecSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaLamViec
        fields = ['id', 'ten_ca', 'gio_bat_dau', 'gio_ket_thuc']

class ChamCongSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChamCong
        fields = ['thoi_gian_check_in', 'thoi_gian_check_out', 'anh_check_in', 'anh_check_out', 'location_check_in']

class PhanCongCaTrucSerializer(serializers.ModelSerializer):
    vi_tri_chot = ViTriChotSerializer(read_only=True)
    ca_lam_viec = CaLamViecSerializer(read_only=True)
    cham_cong = ChamCongSerializer(source='chamcong', read_only=True)
    trang_thai = serializers.SerializerMethodField()

    class Meta:
        model = PhanCongCaTruc
        fields = ['id', 'ngay_truc', 'vi_tri_chot', 'ca_lam_viec', 'cham_cong', 'trang_thai']

    def get_trang_thai(self, obj):
        if not hasattr(obj, 'chamcong'):
            return "CHUA_CHECKIN"
        cc = obj.chamcong
        if cc.thoi_gian_check_in and not cc.thoi_gian_check_out:
            return "DANG_LAM_VIEC"
        if cc.thoi_gian_check_out:
            return "HOAN_THANH"
        return "CHUA_CHECKIN"

class BaoCaoSuCoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaoCaoSuCo
        fields = '__all__'
        read_only_fields = ['ma_su_co', 'trang_thai', 'nguoi_xu_ly', 'created_at']

# ==============================================================================
# [QUAN TRỌNG] CẦU NỐI TƯƠNG THÍCH (ALIASES)
# ==============================================================================
# Dòng này giúp api_views.py có thể import 'MobileCaTrucSerializer' 
# mà thực chất là đang dùng 'PhanCongCaTrucSerializer' mới.
MobileCaTrucSerializer = PhanCongCaTrucSerializer
MobileBaoCaoSuCoSerializer = BaoCaoSuCoSerializer