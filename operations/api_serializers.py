# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: operations/api_serializers.py
Author: Principal Software Architect
Version: v2.0.0.1
Description: Serializers chuyên dụng cho các API Check-in/Check-out mới.
             Đảm bảo Input Validation tại API Entry Points theo DOCUMENTATION.md Section 12.
"""

from decimal import Decimal
from rest_framework import serializers
from operations.models_alive_check import KiemTraQuanSo
from django.utils.translation import gettext_lazy as _

class CheckInCheckOutSerializer(serializers.Serializer):
    """
    Serializer để validate dữ liệu đầu vào cho API Check-in và Check-out.
    Đảm bảo tính toàn vẹn và bảo mật dữ liệu GPS.
    """
    ca_truc_id = serializers.IntegerField(
        help_text=_("ID của phiên phân công ca trực"),
        error_messages={'required': _("Thiếu ID ca trực.")}
    )
    lat = serializers.DecimalField(
        max_digits=9, decimal_places=6,
        min_value=Decimal('-90'), max_value=Decimal('90'),
        help_text=_("Vĩ độ (Latitude) của vị trí chấm công"),
        error_messages={'required': _("Thiếu vĩ độ GPS."), 'min_value': _("Vĩ độ không hợp lệ."), 'max_value': _("Vĩ độ không hợp lệ.")}
    )
    lng = serializers.DecimalField(
        max_digits=9, decimal_places=6,
        min_value=Decimal('-180'), max_value=Decimal('180'),
        help_text=_("Kinh độ (Longitude) của vị trí chấm công"),
        error_messages={'required': _("Thiếu kinh độ GPS."), 'min_value': _("Kinh độ không hợp lệ."), 'max_value': _("Kinh độ không hợp lệ.")}
    )
    image = serializers.ImageField(
        required=False, allow_null=True,
        help_text=_("Ảnh xác thực (selfie)")
    )
    note = serializers.CharField(
        max_length=500, required=False, allow_blank=True,
        help_text=_("Ghi chú thêm cho lần chấm công")
    )

class DashboardFilterSerializer(serializers.Serializer):
    """
    Serializer để validate các tham số lọc cho Dashboard.
    """
    date = serializers.DateField(
        required=False, 
        help_text=_("Ngày cần xem dữ liệu (mặc định là hôm nay)")
    )
    muc_tieu_id = serializers.IntegerField(
        required=False, 
        help_text=_("Lọc theo mục tiêu cụ thể")
    )

class AliveCheckViolationSerializer(serializers.ModelSerializer):
    """
    Serializer hiển thị thông tin vi phạm Alive Check trên Dashboard War Room.
    """
    nhan_vien = serializers.CharField(source='ca_truc.nhan_vien.ho_ten', read_only=True)
    ma_nv = serializers.CharField(source='ca_truc.nhan_vien.ma_nhan_vien', read_only=True)
    muc_tieu = serializers.CharField(source='ca_truc.vi_tri_chot.muc_tieu.ten_muc_tieu', read_only=True)
    trang_thai_hien_thi = serializers.CharField(source='get_trang_thai_display', read_only=True)
    thoi_gian = serializers.DateTimeField(source='thoi_gian_gui_yeu_cau', format="%H:%M %d/%m/%Y", read_only=True)

    class Meta:
        model = KiemTraQuanSo
        fields = [
            'id', 'nhan_vien', 'ma_nv', 'muc_tieu', 
            'trang_thai', 'trang_thai_hien_thi', 
            'thoi_gian'
        ]

class AliveCheckResponseSerializer(serializers.Serializer):
    """
    Serializer để validate phản hồi Alive Check từ Mobile App.
    """
    check_id = serializers.UUIDField(
        error_messages={'required': _("Thiếu ID yêu cầu kiểm tra.")}
    )
    lat = serializers.FloatField(
        error_messages={'required': _("Thiếu tọa độ vĩ độ.")}
    )
    lon = serializers.FloatField(
        error_messages={'required': _("Thiếu tọa độ kinh độ.")}
    )
    device_id = serializers.CharField(max_length=255)
    anh_selfie = serializers.ImageField(required=False, allow_null=True)
