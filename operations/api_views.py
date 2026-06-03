# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: operations/api_views.py
Author: Mr. Anh
Created Date: 2025-12-10
Updated Date: 2026-05-16
Version: v2.1.0-strict
Description: API Views cho Mobile App & Dashboard War Room.
             HARDENING: Enforce for_tenant(), standardized response format, moved business logic to UseCases.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Q
from rolepermissions.checkers import has_role
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
import logging

from .models import PhanCongCaTruc, BaoCaoSuCo, ChamCong, MucTieu
from .access_policies import ShiftAccessPolicy
from mobile.serializers import (
    MobilePhanCongCaTrucSerializer, 
    MobileBaoCaoSuCoSerializer
)
from .api_serializers import (
    CheckInCheckOutSerializer, 
    DashboardFilterSerializer,
    AliveCheckViolationSerializer,
    AliveCheckResponseSerializer
)
from operations.application.alive_check_use_cases import GetRecentAliveCheckViolationsUseCase, ProcessAliveCheckResponseUseCase
from operations.application.attendance_use_cases import CheckInUseCase, CheckOutUseCase
from main.utils.api_helper import api_response, error_response
from operations.application.dashboard_use_cases import GetWarRoomDashboardUseCase

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. MOBILE APP APIS (LEGACY NAMES PRESERVED)
# ==============================================================================

class MobileCaTrucViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API xem lịch trực của nhân viên (Tên cũ: MobileCaTrucViewSet)
    """
    serializer_class = MobilePhanCongCaTrucSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'nhan_vien'):
            return PhanCongCaTruc.objects.none()
        
        nv = user.nhan_vien
        # Rule 4.1: BẮT BUỘC sử dụng for_tenant()
        qs = PhanCongCaTruc.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)

        # 1. Ban Giám đốc & Kế toán: Thấy toàn bộ
        if has_role(user, ['ban_giam_doc', 'ke_toan']):
            return qs.filter(ngay_truc__gte=timezone.now().date()).order_by('ngay_truc')

        # 2. Quản lý vùng: Lọc theo danh sách mục tiêu quản lý
        # Giả định NhanVien có quan hệ m2m hoặc field phụ trách mục tiêu
        if has_role(user, 'quan_ly_vung'):
            # Logic: Lấy các mục tiêu mà NV này được phân quyền quản lý
            # (Cần cập nhật model MucTieu để có field quanly_vung hoặc tương đương)
            return qs.filter(
                vi_tri_chot__muc_tieu__quan_ly_vung=nv,
                ngay_truc__gte=timezone.now().date()
            ).order_by('ngay_truc')

        # 3. Đội trưởng: Thấy toàn bộ quân số tại mục tiêu mình đang trực
        if has_role(user, 'doi_truong'):
            # Lấy mục tiêu hiện tại của Đội trưởng
            current_target_ids = PhanCongCaTruc.objects.filter(
                nhan_vien=nv, 
                ngay_truc=timezone.now().date()
            ).values_list('vi_tri_chot__muc_tieu_id', flat=True)
            
            return qs.filter(
                vi_tri_chot__muc_tieu_id__in=current_target_ids,
                ngay_truc__gte=timezone.now().date()
            ).order_by('ngay_truc')

        # 4. Bảo vệ: Chỉ thấy lịch của chính mình
        return qs.filter(nhan_vien=nv, ngay_truc__gte=timezone.now().date()).order_by('ngay_truc')

    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        """
        API Check-out (Action custom cho Mobile App cũ)
        """
        try:
            ca_truc = self.get_object()
        except Http404:
            return error_response("Không tìm thấy ca trực", error_code="NOT_FOUND")
        except PermissionDenied:
            return error_response(
                "Khong co quyen thao tac ca truc nay.",
                error_code="SHIFT_ACCESS_DENIED",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        anh = request.FILES.get('image')
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        
        try:
            success, msg, data, err_code = CheckOutUseCase.execute(
                phan_cong=ca_truc,
                lat=lat, lng=lng,
                image=anh,
                ip=request.META.get('REMOTE_ADDR'),
                device_info=request.META.get('HTTP_USER_AGENT', ''),
                user=request.user
            )
        except Exception:
            logger.exception("Unexpected error while executing legacy mobile checkout action")
            return error_response(
                "Khong the xu ly check-out luc nay. Vui long thu lai hoac lien he quan tri.",
                error_code="INTERNAL_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if success:
            return api_response(message=msg, data=data)
        return error_response(msg, error_code=err_code or "CHECKOUT_FAILED")


class MobileBaoCaoSuCoViewSet(viewsets.ModelViewSet):
    """
    API danh sach/tao bao cao su co cho mobile app.
    Giu nguyen contract router legacy `mobile/su-co`.
    """
    serializer_class = MobileBaoCaoSuCoSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = (
            BaoCaoSuCo.objects
            .for_tenant(settings.SCMD_ORGANIZATION_ID)
            .select_related('nhan_vien_bao_cao', 'muc_tieu', 'ca_truc')
            .order_by('-created_at')
        )
        user = self.request.user
        if has_role(user, ['ban_giam_doc', 'ke_toan']):
            return qs
        if not hasattr(user, 'nhan_vien'):
            return qs.none()
        return qs.filter(nhan_vien_bao_cao=user.nhan_vien)

    def perform_create(self, serializer):
        nhan_vien = getattr(self.request.user, 'nhan_vien', None)
        serializer.save(
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            nhan_vien_bao_cao=nhan_vien
        )


class CheckInAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckInCheckOutSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Du lieu check-in khong hop le.",
                error_code="INVALID_PARAMS",
                status_code=status.HTTP_400_BAD_REQUEST,
                errors=serializer.errors
            )

        data = serializer.validated_data
        try:
            phan_cong = ShiftAccessPolicy.get_accessible_shift_for_attendance(
                user=request.user,
                shift_id=data['ca_truc_id'],
                tenant_id=settings.SCMD_ORGANIZATION_ID,
            )
        except PermissionDenied as exc:
            return error_response(
                message=str(exc),
                error_code="SHIFT_ACCESS_DENIED",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        try:
            success, msg, payload, err_code = CheckInUseCase.execute(
                phan_cong=phan_cong,
                lat=data['lat'],
                lng=data['lng'],
                image=data.get('image'),
                ip=request.META.get('REMOTE_ADDR'),
                device_info=request.META.get('HTTP_USER_AGENT', ''),
                note=data.get('note', ''),
                user=request.user
            )
        except Exception:
            logger.exception("Unexpected error while executing check-in API")
            return error_response(
                message="Khong the xu ly check-in luc nay. Vui long thu lai hoac lien he quan tri.",
                error_code="INTERNAL_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        if success:
            return api_response(message=msg, data=payload, status_code=status.HTTP_200_OK)
        return error_response(message=msg, error_code=err_code or "CHECKIN_FAILED")


class CheckOutAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckInCheckOutSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Du lieu check-out khong hop le.",
                error_code="INVALID_PARAMS",
                status_code=status.HTTP_400_BAD_REQUEST,
                errors=serializer.errors
            )

        data = serializer.validated_data
        try:
            phan_cong = ShiftAccessPolicy.get_accessible_shift_for_attendance(
                user=request.user,
                shift_id=data['ca_truc_id'],
                tenant_id=settings.SCMD_ORGANIZATION_ID,
            )
        except PermissionDenied as exc:
            return error_response(
                message=str(exc),
                error_code="SHIFT_ACCESS_DENIED",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        try:
            success, msg, payload, err_code = CheckOutUseCase.execute(
                phan_cong=phan_cong,
                lat=data['lat'],
                lng=data['lng'],
                image=data.get('image'),
                ip=request.META.get('REMOTE_ADDR'),
                device_info=request.META.get('HTTP_USER_AGENT', ''),
                note=data.get('note', ''),
                user=request.user
            )
        except Exception:
            logger.exception("Unexpected error while executing check-out API")
            return error_response(
                message="Khong the xu ly check-out luc nay. Vui long thu lai hoac lien he quan tri.",
                error_code="INTERNAL_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        if success:
            return api_response(message=msg, data=payload, status_code=status.HTTP_200_OK)
        return error_response(message=msg, error_code=err_code or "CHECKOUT_FAILED")


class MobileAliveCheckResponseAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AliveCheckResponseSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Du lieu alive check khong hop le.",
                error_code="INVALID_PARAMS",
                status_code=status.HTTP_400_BAD_REQUEST,
                errors=serializer.errors
            )

        data = serializer.validated_data
        success, msg = ProcessAliveCheckResponseUseCase.execute(
            check_id=str(data['check_id']),
            lat=data['lat'],
            lon=data['lon'],
            device_id=data['device_id'],
            anh_selfie=data.get('anh_selfie')
        )
        if success:
            return api_response(message=msg)
        return error_response(message=msg, error_code="ALIVE_CHECK_FAILED")

# ==============================================================================
# 3. DASHBOARD & MAP APIS (WAR ROOM DATA)
# ==============================================================================

class DashboardDataAPIView(APIView):
    """
    API cung cấp dữ liệu tổng hợp cho Dashboard bản đồ.
    Trả về cấu trúc chuẩn: { stats, markers, incidents, last_activity }
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        """
        Xử lý yêu cầu lấy dữ liệu War Room Dashboard.
        Thực thi Site Scoping và Tenant Isolation qua Use Case.
        """
        filter_serializer = DashboardFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return error_response(
                message=filter_serializer.errors, 
                error_code="INVALID_PARAMS", 
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        params = filter_serializer.validated_data
        target_date = params.get('date') or timezone.now().date()
        muc_tieu_id = params.get('muc_tieu_id')
        
        # SSOT: Thiết lập Cache Key dựa trên User và Params (Tenant Isolation)
        cache_key = f"dashboard_data_u{request.user.id}_d{target_date}_m{muc_tieu_id or 'all'}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)

        # 2. Gọi Use Case để lấy dữ liệu đã được lọc theo quyền hạn (Site Scoping)
        # Use Case này đã xử lý phân quyền cho BGĐ, Quản lý vùng và Đội trưởng.
        result = GetWarRoomDashboardUseCase.execute(
            user=request.user,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            target_date=target_date,
            muc_tieu_id=muc_tieu_id
        )

        if "error" in result:
            return error_response(
                message=result["error"], 
                error_code="UNAUTHORIZED_ACCESS", 
                status_code=status.HTTP_403_FORBIDDEN
            )

        response_data = result

        # Lưu vào Redis với TTL 60 giây (Cân bằng giữa hiệu năng và tính real-time)
        cache.set(cache_key, response_data, 60)

        return Response(response_data)

class AliveCheckViolationAPIView(APIView):
    """
    API trả về danh sách các vi phạm Alive Check mới nhất cho Dashboard.
    Rule 12: Operational Visibility.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        # Rule 4.1: Lấy tenant_id từ Auth Context
        tenant_id = getattr(request.user, 'tenant_id', settings.SCMD_ORGANIZATION_ID)
        
        violations = GetRecentAliveCheckViolationsUseCase.execute(tenant_id)
        serializer = AliveCheckViolationSerializer(violations, many=True)
        
        return api_response(data=serializer.data)
