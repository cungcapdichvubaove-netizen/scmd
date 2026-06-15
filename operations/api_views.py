# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: operations/api_views.py
Author: Mr. Anh
Created Date: 2025-12-10
Updated Date: 2026-05-16
Version: v2.1.0-strict
Description: API Views cho mobile app và bảng điều hành vận hành.
             HARDENING: Enforce for_tenant(), standardized response format, moved business logic to UseCases.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Q
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
import logging

from .models import PhanCongCaTruc, BaoCaoSuCo, ChamCong, MucTieu, ShiftChangeRequest, CaLamViec, ViTriChot
from .access_policies import IncidentVisibilityPolicy, ShiftAccessPolicy, ShiftVisibilityPolicy
from mobile.serializers import (
    MobilePhanCongCaTrucSerializer, 
    MobileBaoCaoSuCoSerializer
)
from operations.cache_utils import build_dashboard_cache_key
from .api_serializers import (
    CheckInCheckOutSerializer, 
    DashboardFilterSerializer,
    AliveCheckViolationSerializer,
    AliveCheckResponseSerializer
)
from operations.application.alive_check_use_cases import GetRecentAliveCheckViolationsUseCase, ProcessAliveCheckResponseUseCase
from operations.application.attendance_use_cases import CheckInUseCase, CheckOutUseCase, GetSwapRateReportUseCase
from main.dashboard_router import DashboardRouter
from main.utils.api_helper import api_response, error_response
from operations.application.dashboard_use_cases import GetOperationsDashboardUseCase
from operations.application.incident_reporting_use_cases import ReportIncidentUseCase
from operations.application.shift_change_use_cases import ApplyShiftChangeRequestUseCase, ApproveShiftChangeRequestUseCase
from operations.application.shift_change_permission_policy import ShiftChangePermissionPolicy

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. MOBILE APP APIS
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

        return (
            ShiftVisibilityPolicy.visible_shifts(user)
            .filter(ngay_truc__gte=timezone.now().date())
            .order_by('ngay_truc')
        )

    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        """
        API Check-out (Action custom cho Mobile App)
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

        # Refactor: Sử dụng Serializer để đồng bộ validation GPS/Ảnh (Rule 6.2)
        serializer = CheckInCheckOutSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Dữ liệu check-out không hợp lệ.",
                error_code="INVALID_PARAMS",
                errors=serializer.errors
            )
        
        valid_data = serializer.validated_data
        
        try:
            success, msg, data, err_code = CheckOutUseCase.execute(
                phan_cong=ca_truc,
                lat=valid_data.get('lat'), 
                lng=valid_data.get('lng'),
                image=valid_data.get('image'),
                ip=request.META.get('REMOTE_ADDR'),
                device_info=request.META.get('HTTP_USER_AGENT', ''),
                user=request.user
            )
        except Exception:
            logger.exception("Unexpected error while executing mobile checkout action")
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
    Giu nguyen contract router `mobile/su-co`.
    """
    serializer_class = MobileBaoCaoSuCoSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return (
            IncidentVisibilityPolicy.visible_incidents(self.request.user)
            .select_related('nhan_vien_bao_cao', 'muc_tieu', 'ca_truc')
            .order_by('-created_at')
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except ValidationError as exc:
            return error_response(
                message=" ".join(exc.messages),
                error_code="INCIDENT_REPORT_INVALID",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        nhan_vien = getattr(self.request.user, 'nhan_vien', None)
        ca_truc = ReportIncidentUseCase.resolve_active_shift_or_raise(nhan_vien)
        muc_tieu = ca_truc.vi_tri_chot.muc_tieu
        requested_shift = serializer.validated_data.get('ca_truc')
        requested_site = serializer.validated_data.get('muc_tieu')

        if requested_shift is not None and requested_shift.pk != ca_truc.pk:
            raise ValidationError("Ca trực gửi kèm không khớp với ca trực đang check-in.")
        if requested_site is not None and requested_site.pk != muc_tieu.pk:
            raise ValidationError("Mục tiêu gửi kèm không khớp với ca trực đang check-in.")

        serializer.save(
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            nhan_vien_bao_cao=nhan_vien,
            muc_tieu=muc_tieu,
            ca_truc=ca_truc,
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

        serializer = CheckInCheckOutSerializer(
            data=request.data,
            context={
                "phan_cong": phan_cong,
                "request": request,
                "attendance_action": "check_in",
            },
        )
        if not serializer.is_valid():
            return error_response(
                message="Du lieu check-in khong hop le.",
                error_code="INVALID_PARAMS",
                status_code=status.HTTP_400_BAD_REQUEST,
                errors=serializer.errors
            )
        data = serializer.validated_data

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

        serializer = CheckInCheckOutSerializer(
            data=request.data,
            context={
                "phan_cong": phan_cong,
                "request": request,
                "attendance_action": "check_out",
            },
        )
        if not serializer.is_valid():
            return error_response(
                message="Du lieu check-out khong hop le.",
                error_code="INVALID_PARAMS",
                status_code=status.HTTP_400_BAD_REQUEST,
                errors=serializer.errors
            )
        data = serializer.validated_data

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
        serializer = AliveCheckResponseSerializer(data=request.data, context={'request': request})
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
            user=request.user,
            anh_selfie=data.get('anh_selfie'),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        if success:
            return api_response(message=msg)
        return error_response(message=msg, error_code="ALIVE_CHECK_FAILED")



class MobileShiftChangeRequestAPIView(APIView):
    """Mobile endpoint for creating shift-change requests.

    This replaces the frozen legacy doi-ca endpoint and writes to
    ``ShiftChangeRequest`` as the SSOT. It does not mutate ``PhanCongCaTruc``.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        staff = getattr(request.user, "nhan_vien", None)
        if staff is None:
            return error_response(
                message="Tài khoản chưa liên kết hồ sơ nhân viên.",
                error_code="NO_EMPLOYEE_PROFILE",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        data = request.data
        try:
            original = None
            original_id = data.get("phan_cong_id") or data.get("ca_truc_id")
            if original_id:
                original = ShiftAccessPolicy.get_accessible_shift_for_attendance(
                    user=request.user,
                    shift_id=original_id,
                    tenant_id=settings.SCMD_ORGANIZATION_ID,
                )
            desired_shift = None
            if data.get("ca_mong_muon_id"):
                desired_shift = CaLamViec.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).get(pk=data.get("ca_mong_muon_id"))
            desired_post = None
            if data.get("vi_tri_mong_muon_id"):
                desired_post = ViTriChot.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).get(pk=data.get("vi_tri_mong_muon_id"))
            replacement = None
            if data.get("nhan_vien_thay_the_id"):
                from users.models import NhanVien
                replacement = NhanVien.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).get(pk=data.get("nhan_vien_thay_the_id"))

            ShiftChangePermissionPolicy.enforce_create(request.user, original_assignment=original, requester=staff)

            request_obj = ShiftChangeRequest(
                tenant_id=settings.SCMD_ORGANIZATION_ID,
                ma_yeu_cau=data.get("ma_yeu_cau") or f"SCR-{timezone.now():%Y%m%d%H%M%S}-{staff.pk}",
                nguoi_yeu_cau=staff,
                phan_cong_goc=original,
                loai_yeu_cau=data.get("loai_yeu_cau") or ShiftChangeRequest.LoaiYeuCau.CHANGE_SHIFT,
                ngay_mong_muon=data.get("ngay_mong_muon") or None,
                ca_mong_muon=desired_shift,
                vi_tri_mong_muon=desired_post,
                nhan_vien_thay_the=replacement,
                trang_thai=ShiftChangeRequest.TrangThai.PENDING_APPROVAL,
                ly_do=data.get("ly_do") or "",
            )
            request_obj.full_clean()
            request_obj.save()
        except PermissionDenied as exc:
            return error_response(
                message=str(exc),
                error_code="SHIFT_CHANGE_FORBIDDEN",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        except Exception as exc:
            logger.exception("Failed to create mobile shift-change request")
            return error_response(
                message=str(exc),
                error_code="SHIFT_CHANGE_REQUEST_INVALID",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return api_response(
            message="Đã gửi yêu cầu đổi ca/tăng ca.",
            data={"id": request_obj.pk, "ma_yeu_cau": request_obj.ma_yeu_cau, "trang_thai": request_obj.trang_thai},
            status_code=status.HTTP_201_CREATED,
        )


class MobileShiftChangeApproveAPIView(APIView):
    """Approve and optionally apply a shift-change request from mobile/API."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request_id = request.data.get("id") or request.data.get("request_id")
        if not request_id:
            return error_response("Thiếu request_id.", error_code="MISSING_REQUEST_ID", status_code=status.HTTP_400_BAD_REQUEST)
        try:
            shift_request = ShiftChangeRequest.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).get(pk=request_id)
            ShiftChangePermissionPolicy.enforce_approve(request.user, shift_request)
            if shift_request.trang_thai == ShiftChangeRequest.TrangThai.PENDING_APPROVAL:
                ApproveShiftChangeRequestUseCase.execute(
                    shift_request.pk,
                    actor=request.user,
                    tenant_id=settings.SCMD_ORGANIZATION_ID,
                    note="Mobile/API approval",
                )
                shift_request.refresh_from_db()
            apply_now = str(request.data.get("apply", "false")).lower() in {"1", "true", "yes"}
            payload = {"id": shift_request.pk, "trang_thai": shift_request.trang_thai}
            if apply_now:
                result = ApplyShiftChangeRequestUseCase.execute(
                    shift_request.pk,
                    actor=request.user,
                    tenant_id=settings.SCMD_ORGANIZATION_ID,
                )
                shift_request.refresh_from_db()
                payload.update({"applied": True, "assignment_id": result.assignment_id, "action": result.action, "trang_thai": shift_request.trang_thai})
        except PermissionDenied as exc:
            return error_response(str(exc), error_code="SHIFT_CHANGE_FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            logger.exception("Failed to approve/apply mobile shift-change request")
            return error_response(str(exc), error_code="SHIFT_CHANGE_APPROVAL_FAILED", status_code=status.HTTP_400_BAD_REQUEST)
        return api_response(message="Đã xử lý yêu cầu đổi ca.", data=payload)

# ==============================================================================
# 3. DASHBOARD & MAP APIS (OPERATIONS COCKPIT DATA)
# ==============================================================================



class SwapRateReportAPIView(APIView):
    """Operations swap-rate report sourced from ShiftChangeRequest.

    Phase D: authentication alone is not enough. The use case receives the
    request user and resolves target scope through ShiftChangePermissionPolicy.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        try:
            month = int(request.query_params.get("month") or today.month)
            year = int(request.query_params.get("year") or today.year)
            result = GetSwapRateReportUseCase.execute(
                month=month,
                year=year,
                tenant_id=settings.SCMD_ORGANIZATION_ID,
                user=request.user,
            )
        except (TypeError, ValueError):
            return error_response("Tháng/năm không hợp lệ.", error_code="INVALID_PERIOD", status_code=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as exc:
            return error_response(str(exc), error_code="SWAP_RATE_REPORT_FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)
        result["source_model"] = "operations.ShiftChangeRequest"
        return Response(result)


class DashboardDataAPIView(APIView):
    """
    API cung cấp dữ liệu tổng hợp cho Dashboard bản đồ.
    Trả về cấu trúc chuẩn: { stats, markers, incidents, last_activity }
    """
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _no_store(response):
        response["Cache-Control"] = "no-store"
        return response

    def get(self, request):
        """
        Xu ly yeu cau lay du lieu bang dieu hanh van hanh.
        Thực thi Site Scoping và Tenant Isolation qua Use Case.
        """
        if not DashboardRouter.user_can_access(request.user, "operations:dashboard_vanhanh"):
            return self._no_store(error_response(
                message="Bạn không có quyền xem dữ liệu vận hành.",
                error_code="permission_denied",
                status_code=status.HTTP_403_FORBIDDEN,
            ))

        filter_serializer = DashboardFilterSerializer(data=request.query_params, context={'request': request})
        if not filter_serializer.is_valid():
            return self._no_store(error_response(
                message=filter_serializer.errors, 
                error_code="INVALID_PARAMS", 
                status_code=status.HTTP_400_BAD_REQUEST
            ))
        
        params = filter_serializer.validated_data
        target_date = params.get('date') or timezone.now().date()
        muc_tieu_id = params.get('muc_tieu_id')
        
        # SSOT: cache key theo organization + quyền/scope đã resolve; không nhận tenant từ request.
        cache_key = build_dashboard_cache_key(
            user=request.user,
            target_date=target_date,
            muc_tieu_id=muc_tieu_id,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            dashboard_name="operations",
        )
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return self._no_store(Response(cached_data))

        # 2. Gọi Use Case để lấy dữ liệu đã được lọc theo quyền hạn (Site Scoping)
        # Use Case này đã xử lý phân quyền cho BGĐ, Quản lý vùng và Đội trưởng.
        result = GetOperationsDashboardUseCase.execute(
            user=request.user,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
            target_date=target_date,
            muc_tieu_id=muc_tieu_id
        )

        if "error" in result:
            return self._no_store(error_response(
                message=result["error"], 
                error_code="UNAUTHORIZED_ACCESS", 
                status_code=status.HTTP_403_FORBIDDEN
            ))

        response_data = result

        # Server-side cache ngắn hạn; HTTP response vẫn no-store để tránh stale PWA/browser cache.
        cache.set(cache_key, response_data, 60)

        return self._no_store(Response(response_data))

class AliveCheckViolationAPIView(APIView):
    """
    API trả về danh sách các vi phạm Alive Check mới nhất cho Dashboard.
    Rule 12: Operational Visibility.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        # SCMD Pro - Single-organization guard (WHITEPAPER.md 9).
        # Enforce organization scope from settings SSOT to ensure data isolation integrity.
        tenant_id = settings.SCMD_ORGANIZATION_ID
        
        violations = GetRecentAliveCheckViolationsUseCase.execute(tenant_id)
        serializer = AliveCheckViolationSerializer(violations, many=True)
        
        return api_response(data=serializer.data)
