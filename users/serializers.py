# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: users/serializers.py
Author: Mr. Anh
Created Date: 2025-12-10
Description: Serializers cho module Users (Nhân sự).
"""

from rest_framework import serializers
from .models import NhanVien, PhongBan, ChucDanh

class ChucDanhSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChucDanh
        fields = ['id', 'ten_chuc_danh']

class PhongBanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhongBan
        fields = ['id', 'ten_phong_ban']

class NhanVienSerializer(serializers.ModelSerializer):
    chuc_danh_info = ChucDanhSerializer(source='chuc_danh', read_only=True)
    phong_ban_info = PhongBanSerializer(source='phong_ban', read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = NhanVien
        fields = [
            'id', 'ma_nhan_vien', 'ho_ten', 'so_dien_thoai', 
            'anh_the', 'avatar_url',
            'chuc_danh_info', 'phong_ban_info'
        ]

    def get_avatar_url(self, obj):
        if obj.anh_the:
            return obj.anh_the.url
        return None