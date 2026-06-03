# -*- coding: utf-8 -*-
from rest_framework import serializers
from operations.models import PhanCongCaTruc

class MobileWeeklyScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer cho lịch trực tuần trên Mobile.
    """
    ten_ca = serializers.CharField(source='ca_lam_viec.ten_ca', read_only=True)
    thoi_gian = serializers.SerializerMethodField()
    ten_muc_tieu = serializers.CharField(source='vi_tri_chot.muc_tieu.ten_muc_tieu', read_only=True)
    ten_vi_tri = serializers.CharField(source='vi_tri_chot.ten_vi_tri', read_only=True)
    is_today = serializers.SerializerMethodField()

    class Meta:
        model = PhanCongCaTruc
        fields = [
            'id', 'ngay_truc', 'ten_ca', 'thoi_gian', 
            'ten_muc_tieu', 'ten_vi_tri', 'is_today'
        ]

    def get_thoi_gian(self, obj):
        if not obj.ca_lam_viec: return ""
        return f"{obj.ca_lam_viec.gio_bat_dau.strftime('%H:%M')} - {obj.ca_lam_viec.gio_ket_thuc.strftime('%H:%M')}"

    def get_is_today(self, obj):
        from django.utils import timezone
        return obj.ngay_truc == timezone.now().date()

class MobileShiftSwapSerializer(serializers.Serializer):
    """
    Serializer cho yêu cầu đổi ca trực từ nhân viên.
    """
    ca_truc_id = serializers.IntegerField(required=True)
    ly_do = serializers.CharField(required=True, min_length=10, max_length=1000)

    def validate_ca_truc_id(self, value):
        if value <= 0:
            raise serializers.ValidationError("ID ca trực không hợp lệ.")
        return value

class ProcessShiftSwapSerializer(serializers.Serializer):
    """
    Serializer cho Đội trưởng xử lý phê duyệt đơn.
    """
    request_id = serializers.IntegerField(required=True)
    action = serializers.ChoiceField(choices=['APPROVE', 'REJECT'], required=True)
    nhan_vien_moi_id = serializers.IntegerField(required=False)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)