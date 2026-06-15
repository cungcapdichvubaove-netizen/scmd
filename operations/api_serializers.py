# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: operations/api_serializers.py
Author: Principal Software Architect
Version: v2.0.0.1
Description: Serializers chuyên dụng cho các API Check-in/Check-out mới.
             Đảm bảo Input Validation tại API Entry Points theo DOCUMENTATION.md Section 12.
"""

from decimal import Decimal
from django.conf import settings
from rest_framework import serializers
from operations.application.attendance_policies import AttendancePhotoPolicy
from operations.models import KiemTraQuanSo, PhanCongCaTruc, MucTieu
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

    def validate(self, attrs):
        phan_cong = self.context.get("phan_cong")
        attendance_action = self.context.get("attendance_action")
        if not phan_cong or not attendance_action:
            return attrs

        if AttendancePhotoPolicy.is_required(
            phan_cong=phan_cong,
            action=attendance_action,
        ) and not attrs.get("image"):
            raise serializers.ValidationError(
                {"image": _("Ca trực này bắt buộc ảnh xác thực.")}
            )
        return attrs

    def validate_ca_truc_id(self, value):
        """Cưỡng chế scoping ca trực theo request user và organization (Rule 9)."""
        request = self.context.get('request')
        if not request:
            return value

        user = request.user
        qs = PhanCongCaTruc.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)

        if not user.is_superuser:
            if hasattr(user, 'nhan_vien'):
                qs = qs.filter(nhan_vien=user.nhan_vien)
            elif not user.is_staff:
                raise serializers.ValidationError(_("Tài khoản chưa được liên kết với hồ sơ nhân sự."))

        if not qs.filter(id=value).exists():
            raise serializers.ValidationError(_("Ca trực không hợp lệ hoặc bạn không có quyền thao tác."))
        return value

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

    def validate_muc_tieu_id(self, value):
        """Cưỡng chế scoping mục tiêu theo organization (Rule 9)."""
        if value:
            if not MucTieu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(id=value).exists():
                raise serializers.ValidationError(_("Mục tiêu không tồn tại hoặc không thuộc tổ chức này."))
        return value

class AliveCheckViolationSerializer(serializers.ModelSerializer):
    """
    Serializer hien thi thong tin vi pham Alive Check tren bang dieu hanh van hanh.
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
    check_id = serializers.IntegerField(
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

    def validate_check_id(self, value):
        """Cưỡng chế scoping yêu cầu Alive Check theo user và organization."""
        request = self.context.get('request')
        if not request:
            return value

        user = request.user
        qs = KiemTraQuanSo.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)

        if not user.is_superuser:
            if hasattr(user, 'nhan_vien'):
                qs = qs.filter(ca_truc__nhan_vien=user.nhan_vien)
            else:
                raise serializers.ValidationError(_("Tài khoản chưa liên kết hồ sơ nhân sự."))

        if not qs.filter(id=value).exists():
            raise serializers.ValidationError(_("Yêu cầu kiểm tra không hợp lệ hoặc không dành cho bạn."))
        return value
