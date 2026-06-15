# -*- coding: utf-8 -*-
from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from accounting.models import PhanHoiLuong
from accounting.application.dispute_use_cases import CreateDisputeUseCase

class PhanHoiLuongSerializer(serializers.ModelSerializer):
    """
    Serializer cho tính năng phản hồi lương trên Mobile App.
    """
    trang_thai_display = serializers.CharField(source='get_trang_thai_display', read_only=True)
    ten_ky_luong = serializers.CharField(source='chi_tiet_luong.bang_luong.ten_bang_luong', read_only=True)

    class Meta:
        model = PhanHoiLuong
        fields = [
            'id', 'chi_tiet_luong', 'noi_dung', 'phan_hoi_admin', 
            'trang_thai', 'trang_thai_display', 'ten_ky_luong', 'created_at'
        ]
        read_only_fields = ['trang_thai', 'phan_hoi_admin']

class PhanHoiLuongViewSet(viewsets.ModelViewSet):
    """
    API Endpoint cho nhân viên thực hiện 'Phản hồi lương' (Dispute).
    Tuân thủ Multi-tenancy & Security boundaries.
    """
    serializer_class = PhanHoiLuongSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Chỉ trả về các phản hồi của chính nhân viên đó (Site Scoping)"""
        user = self.request.user
        if not hasattr(user, 'nhanvien'):
            return PhanHoiLuong.objects.none()
        
        return PhanHoiLuong.objects.filter(
            nhan_vien=user.nhanvien,
            tenant_id=settings.SCMD_ORGANIZATION_ID
        )

    def create(self, request, *args, **kwargs):
        """Sử dụng Use Case để thực hiện tạo khiếu nại"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        success, message = CreateDisputeUseCase.execute(
            user_nhan_vien=request.user.nhanvien,
            chi_tiet_luong_id=serializer.validated_data['chi_tiet_luong'].id,
            noi_dung=serializer.validated_data['noi_dung'],
            tenant_id=settings.SCMD_ORGANIZATION_ID
        )

        if success:
            return Response({"success": True, "message": message}, status=status.HTTP_201_CREATED)
        return Response({"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST)