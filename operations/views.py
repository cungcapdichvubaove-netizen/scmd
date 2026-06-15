# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: operations/views.py
Author: Mr. Anh
Created Date: 2025-12-09
Updated Date: 2026-04-28
Version: v1.1.0
Description: Views xử lý logic Vận hành.
             UPDATED: dashboard_vanhanh_view chuyển sang render Skeleton (tối ưu hiệu năng).
"""

import os
import json
import logging
from datetime import datetime, timedelta, date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from main.dashboard_router import dashboard_access_required
from django.utils import timezone
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_control
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.urls import reverse
from main.dashboard_cta import admin_url_if_permitted, dashboard_route_url, reverse_or_none
from reports.access_policies import ReportAccessPolicy

from core.policy_result import AccessScopeDenied
from main.models import AuditLog
from .models import PhanCongCaTruc, BaoCaoSuCo, ChamCong, KiemTraQuanSo, ViTriChot, CaLamViec, BaoCaoDeXuat
from inspection.models import DiemTuanTra, GhiNhanTuanTra, LuotTuanTra
from users.models import NhanVien
from clients.access_policies import SiteVisibilityPolicy
from clients.models import MucTieu
from .forms import BaoCaoSuCoForm, BaoCaoDeXuatForm
from .application.attendance_use_cases import CheckInUseCase, CheckOutUseCase, GetMobileDashboardUseCase, TriggerSOSUseCase, ConfirmAliveCheckUseCase
from .application.attendance_history_use_cases import GetAttendanceHistoryUseCase
from .application.scheduling_use_cases import ManageShiftAssignmentUseCase
from .application.weekly_schedule_use_cases import GetWeeklyScheduleUseCase
from .api_serializers import CheckInCheckOutSerializer
from .application.incident_reporting_use_cases import ReportIncidentUseCase
from .application.guard_patrol_use_cases import (
    CompleteGuardPatrolSessionUseCase,
    ListGuardPatrolTasksUseCase,
    RecordGuardPatrolCheckpointUseCase,
    StartGuardPatrolSessionUseCase,
)
from .application.proposal_management_use_cases import CreateFieldProposalUseCase
from .access_policies import ShiftAccessPolicy, ShiftAssignmentPolicy
from users.access_policies import StaffVisibilityPolicy
from rolepermissions.checkers import has_permission, has_role
from rolepermissions.decorators import has_permission_decorator

logger = logging.getLogger(__name__)


def _user_can_schedule_shifts(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and has_permission(user, "giao_ca_truc")
        and user.has_perm("operations.add_phancongcatruc")
        and user.has_perm("operations.change_phancongcatruc")
        and user.has_perm("operations.delete_phancongcatruc")
    )


def _handle_mobile_operation_error(request, message, log_message):
    logger.exception(log_message)
    messages.error(request, message)

# --- HELPER ---
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for: return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def get_mobile_context(request):
    """
    Lấy hồ sơ nhân viên một cách an toàn. 
    Chỉ bắt lỗi khi quan hệ OneToOne không tồn tại hoặc user chưa login.
    """
    try:
        return request.user.nhan_vien
    except (AttributeError, NhanVien.DoesNotExist):
        return None


def _build_schedule_dashboard_context(request):
    """
    Xây dựng context cho bảng xếp lịch tuần.
    Logic nghiệp vụ đã được chuyển sang GetWeeklyScheduleUseCase.
    """
    context = GetWeeklyScheduleUseCase.execute(
        user=request.user,
        tenant_id=settings.SCMD_ORGANIZATION_ID,
        date_str=request.GET.get('date'),
        muc_tieu_id=request.GET.get('muc_tieu'),
    )
    
    # Thêm các URL thuộc về Interface Layer; CTA chỉ có khi user được DashboardRouter cho phép.
    context.update({
        'presentation_url': dashboard_route_url(request.user, 'operations:dashboard_trinh_chieu'),
        'operations_dashboard_url': dashboard_route_url(request.user, 'operations:dashboard_vanhanh'),
        'legacy_schedule_url': dashboard_route_url(request.user, 'operations:dashboard_xep_lich'),
        'can_schedule': _user_can_schedule_shifts(request.user),
    })
    return context

@dashboard_access_required("operations:dashboard_vanhanh")
def dashboard_vanhanh_view(request):
    """
    [OPTIMIZED] Render khung bang dieu hanh van hanh.
    Dữ liệu sẽ được fetch async từ API /api/dashboard/data/
    """
    incident_report_url = (
        reverse_or_none('reports:su_co')
        if ReportAccessPolicy.can_view_incident_reports(request.user)
        else None
    )
    attendance_report_url = (
        reverse_or_none('reports:cham_cong_muc_tieu')
        if ReportAccessPolicy.can_view_attendance_reports(request.user)
        else None
    )
    schedule_url = dashboard_route_url(request.user, 'operations:dashboard_xep_lich')
    presentation_url = dashboard_route_url(request.user, 'operations:dashboard_trinh_chieu')
    target_list_url = reverse_or_none('operations:danh_sach_muc_tieu') if schedule_url else None
    incident_admin_base_url = admin_url_if_permitted(
        request.user,
        'admin:operations_baocaosuco_changelist',
        'operations.change_baocaosuco',
    )

    return render(
        request,
        "operations/dashboard_vanhanh.html",
        {
            "dashboard_api_url": reverse('operations:api_dashboard_data'),
            "presentation_url": presentation_url,
            "schedule_url": schedule_url,
            "target_list_url": target_list_url,
            "incident_report_url": incident_report_url,
            "attendance_report_url": attendance_report_url,
            "incident_admin_base_url": incident_admin_base_url,
            "map_tile_url": settings.SCMD_MAP_TILE_URL,
            "map_attribution": settings.SCMD_MAP_ATTRIBUTION,
        },
    )

@dashboard_access_required("operations:dashboard_trinh_chieu")
def dashboard_trinh_chieu_view(request):
    """
    Man hinh phu de trinh chieu tren man hinh lon cua trung tam dieu phoi.
    Giu cung nguon du lieu voi dashboard van hanh de tranh lech so.
    """
    return render(
        request,
        "operations/dashboard_trinh_chieu.html",
        {
            "dashboard_api_url": reverse('operations:api_dashboard_data'),
            "operations_dashboard_url": reverse('operations:dashboard_vanhanh'),
            "map_tile_url": settings.SCMD_MAP_TILE_URL,
            "map_attribution": settings.SCMD_MAP_ATTRIBUTION,
        },
    )

# --- MOBILE VIEWS (Giữ nguyên logic gốc) ---
@dashboard_access_required("operations:mobile_dashboard")
def mobile_dashboard(request):
    nhan_vien = get_mobile_context(request)
    if not nhan_vien:
        return render(request, "operations/mobile/error_no_profile.html")

    # SSOT: Delegate logic tìm ca trực và Alive Check sang Application Layer.
    ca_truc_hom_nay, trang_thai_checkin, alive_check_pending = GetMobileDashboardUseCase.execute(nhan_vien)

    local_now = timezone.localtime(timezone.now())
    greeting = (
        "Chào buổi sáng"
        if 5 <= local_now.hour < 11
        else "Chào buổi trưa"
        if 11 <= local_now.hour < 13
        else "Chào buổi chiều"
        if 13 <= local_now.hour < 18
        else "Chào buổi tối"
    )
    patrol_allowed = bool(
        getattr(request.user, "is_superuser", False)
        or has_permission(request.user, "thuc_hien_tuan_tra_bao_ve")
    )
    has_active_checked_in_shift = bool(ca_truc_hom_nay and trang_thai_checkin is True)

    return render(
        request,
        "operations/mobile/dashboard.html",
        {
            "nhan_vien": nhan_vien,
            "ca_truc_hom_nay": ca_truc_hom_nay,
            "greeting": greeting,
            "trang_thai_checkin": trang_thai_checkin,
            "alive_check_pending": alive_check_pending,
            "google_maps_api_key": getattr(settings, "GOOGLE_MAPS_API_KEY", ""),
            "patrol_allowed": patrol_allowed,
            "patrol_hint": (
                "Mở nhiệm vụ tuần tra theo ca trực hiện tại."
                if patrol_allowed and ca_truc_hom_nay
                else "Chưa có ca trực phù hợp để nhận nhiệm vụ tuần tra."
                if patrol_allowed
                else "Tài khoản này chưa được cấp quyền tuần tra mục tiêu."
            ),
            "incident_hint": (
                "Bạn đang trong ca trực. Có thể gửi báo cáo sự cố ngay."
                if has_active_checked_in_shift
                else "Có thể mở biểu mẫu sự cố. Khi cần nghiệp vụ khẩn, hãy check-in trước để gắn đúng ca trực."
            ),
            "proposal_hint": "Gửi đề xuất nghiệp vụ, vật tư hoặc nhu cầu hỗ trợ về văn phòng.",
            "sos_ready": has_active_checked_in_shift,
            "sos_hint": (
                "Giữ nút 2 giây để gửi cảnh báo khẩn cấp có GPS thực."
                if has_active_checked_in_shift
                else "SOS chỉ hoạt động khi bạn đang trong ca trực đã check-in."
            ),
        },
    )

@login_required
@has_permission_decorator('thuc_hien_tuan_tra_bao_ve')
def mobile_tuan_tra_list(request):
    """Canonical guard patrol task list owned by operations."""
    nhan_vien = get_mobile_context(request)
    if not nhan_vien:
        return redirect('operations:mobile_dashboard')
    context = ListGuardPatrolTasksUseCase.execute(nhan_vien, actor=request.user)
    return render(request, 'operations/mobile/tuan_tra_list.html', context)


@login_required
@has_permission_decorator('thuc_hien_tuan_tra_bao_ve')
def bat_dau_tuan_tra(request, loai_id):
    """Start patrol from the operations canonical namespace."""
    try:
        luot = StartGuardPatrolSessionUseCase.execute(get_mobile_context(request), loai_id)
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
        return redirect('operations:mobile_tuan_tra_list')
    return redirect('operations:thuc_hien_tuan_tra', luot_id=luot.id)


@login_required
@has_permission_decorator('thuc_hien_tuan_tra_bao_ve')
def thuc_hien_tuan_tra(request, luot_id):
    nhan_vien = get_mobile_context(request)
    if not nhan_vien:
        return redirect('operations:mobile_dashboard')
    luot = get_object_or_404(
        LuotTuanTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_related('loai_tuan_tra', 'phan_cong_ca_truc', 'lich_tuan_tra_van_hanh', 'nhiem_vu_tuan_tra_ca'),
        id=luot_id,
        nhan_vien=nhan_vien,
        trang_thai='DANG_DI',
    )
    points = list(
        DiemTuanTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(loai_tuan_tra=luot.loai_tuan_tra)
        .order_by('thu_tu', 'id')
    )
    scanned_ids = set(
        GhiNhanTuanTra.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(luot_tuan_tra=luot)
        .values_list('diem_tuan_tra_id', flat=True)
    )
    for point in points:
        point.da_quet = point.pk in scanned_ids
    required_photo = bool(getattr(luot.lich_tuan_tra_van_hanh, 'yeu_cau_anh', False)) if luot.lich_tuan_tra_van_hanh else bool(getattr(settings, 'GUARD_PATROL_REQUIRE_PHOTO', False))
    required_gps = bool(getattr(luot.lich_tuan_tra_van_hanh, 'yeu_cau_gps', False)) if luot.lich_tuan_tra_van_hanh else bool(getattr(luot.loai_tuan_tra, 'yeu_cau_gps', False))
    return render(request, 'operations/mobile/tuan_tra.html', {
        'luot_tuan_tra': luot,
        'danh_sach_diem': points,
        'diem_da_quet': len(scanned_ids),
        'tong_diem': len(points),
        'yeu_cau_anh_bat_buoc': required_photo,
        'yeu_cau_gps_bat_buoc': required_gps,
    })


@require_POST
@login_required
@has_permission_decorator('thuc_hien_tuan_tra_bao_ve')
def ghi_nhan_diem_tuan_tra(request):
    nhan_vien = get_mobile_context(request)
    luot_id = request.POST.get('luot_id') or request.POST.get('luot_tuan_tra_id')
    ma_qr = request.POST.get('ma_qr') or request.POST.get('qr_code')
    try:
        success, message, data = RecordGuardPatrolCheckpointUseCase.execute(
            nhan_vien=nhan_vien,
            luot_id=luot_id,
            ma_qr=ma_qr,
            lat_req=request.POST.get('lat'),
            lng_req=request.POST.get('lng'),
            hinh_anh_xac_thuc=request.FILES.get('hinh_anh_xac_thuc'),
        )
    except (PermissionDenied, ValidationError) as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=403)
    response_data = {'success': success, 'message': message}
    response_data.update(data)
    return JsonResponse(response_data)


@login_required
@has_permission_decorator('thuc_hien_tuan_tra_bao_ve')
@require_POST
def hoan_thanh_tuan_tra(request, luot_id):
    try:
        CompleteGuardPatrolSessionUseCase.execute(get_mobile_context(request), luot_id)
        messages.success(request, 'Đã hoàn thành tuần tra mục tiêu!')
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect('operations:mobile_tuan_tra_list')


@login_required
def check_in_view(request, phan_cong_id):
    if request.method == 'POST':
        data = request.POST.copy()
        data['ca_truc_id'] = phan_cong_id
        serializer = CheckInCheckOutSerializer(data=data)

        if not serializer.is_valid():
            messages.error(request, f"Du lieu khong hop le: {serializer.errors}")
            return redirect('operations:mobile_dashboard')

        try:
            pc = ShiftAccessPolicy.get_accessible_shift_for_attendance(
                user=request.user,
                shift_id=phan_cong_id,
                tenant_id=settings.SCMD_ORGANIZATION_ID,
            )
            success, msg, _, err_code = CheckInUseCase.execute(
                phan_cong=pc,
                lat=serializer.validated_data['lat'],
                lng=serializer.validated_data['lng'],
                image=request.FILES.get('anh_check_in') or serializer.validated_data.get('image'),
                ip=get_client_ip(request),
                device_info=request.META.get('HTTP_USER_AGENT', ''),
                note=serializer.validated_data.get('note', ''),
                user=request.user
            )

            if success: messages.success(request, msg)
            else: messages.error(request, msg)
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        except ValidationError as exc:
            messages.error(request, str(exc))
        except Exception:
            _handle_mobile_operation_error(
                request,
                "Khong the xu ly check-in luc nay. Vui long thu lai hoac lien he quan tri.",
                "Unexpected error while checking in from mobile web",
            )
    return redirect('operations:mobile_dashboard')

@login_required
def check_out_view(request, phan_cong_id):
    if request.method == 'POST':
        try:
            pc = ShiftAccessPolicy.get_accessible_shift_for_attendance(
                user=request.user,
                shift_id=phan_cong_id,
                tenant_id=settings.SCMD_ORGANIZATION_ID,
            )
            note = request.POST.get('note', '')

            success, msg, _, err_code = CheckOutUseCase.execute(
                phan_cong=pc,
                lat=request.POST.get('lat'),
                lng=request.POST.get('lng'),
                image=request.FILES.get('anh_check_out'),
                ip=get_client_ip(request),
                device_info=request.META.get('HTTP_USER_AGENT', ''),
                note=note,
                user=request.user
            )

            if success: messages.success(request, msg)
            else: messages.error(request, msg)
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        except ValidationError as exc:
            messages.error(request, str(exc))
        except Exception:
            _handle_mobile_operation_error(
                request,
                "Khong the xu ly check-out luc nay. Vui long thu lai hoac lien he quan tri.",
                "Unexpected error while checking out from mobile web",
            )
    return redirect('operations:mobile_dashboard')

@login_required
def trigger_sos(request):
    if request.method == "POST":
        nhan_vien = get_mobile_context(request)
        if nhan_vien:
            lat, lng = request.POST.get('lat', ''), request.POST.get('lng', '')
            # Rule 3.2: Delegated to TriggerSOSUseCase
            success, msg, _, _ = TriggerSOSUseCase.execute(nhan_vien, lat, lng)
            if success:
                messages.warning(request, msg)
            else:
                messages.error(request, msg)
    return redirect('operations:mobile_dashboard')

@login_required
def mobile_cham_cong_view(request):
    nhan_vien = get_mobile_context(request)
    if not nhan_vien:
        return redirect('operations:mobile_dashboard')

    if request.method == 'POST':
        try:
            action = request.POST.get('action') 
            lat = request.POST.get('lat')
            lng = request.POST.get('lng')
            note = request.POST.get('note', '')
            
            # DRY: Tái sử dụng logic xác định ca trực từ GetMobileDashboardUseCase
            target_pc, status_pc, alive_check_pending = GetMobileDashboardUseCase.execute(nhan_vien)
            
            if not target_pc: 
                messages.error(request, "Không tìm thấy ca trực hợp lệ!"); 
                return redirect('operations:mobile_dashboard')

            if action in ['IN', 'check_in']: 
                success, msg, _, _ = CheckInUseCase.execute(target_pc, lat, lng, request.FILES.get('anh_check_in'), get_client_ip(request), request.META.get('HTTP_USER_AGENT', ''), note=note, user=request.user)
            else: 
                success, msg, _, _ = CheckOutUseCase.execute(target_pc, lat, lng, request.FILES.get('anh_check_out'), get_client_ip(request), request.META.get('HTTP_USER_AGENT', ''), note=note, user=request.user)
            
            if success: messages.success(request, msg)
            else: messages.error(request, msg)
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        except ValidationError as exc:
            messages.error(request, str(exc))
        except Exception:
            _handle_mobile_operation_error(
                request,
                "Khong the xu ly cham cong luc nay. Vui long thu lai hoac lien he quan tri.",
                "Unexpected error while processing mobile attendance",
            )
        return redirect('operations:mobile_cham_cong')

    current_shift, status_pc, alive_check_pending = GetMobileDashboardUseCase.execute(nhan_vien)
    attendance_history = list(
        PhanCongCaTruc.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(nhan_vien=nhan_vien)
        .select_related('ca_lam_viec', 'vi_tri_chot__muc_tieu', 'chamcong')
        .order_by('-ngay_truc')[:5]
    )
    return render(
        request,
        'operations/mobile/cham_cong.html',
        {
            'nhan_vien': nhan_vien,
            'ca_truc_hom_nay': current_shift,
            'trang_thai_checkin': status_pc,
            'alive_check_pending': alive_check_pending,
            'attendance_history': attendance_history,
        },
    )

@login_required
def mobile_lich_truc_view(request):
    nhan_vien = get_mobile_context(request); 
    if not nhan_vien: return redirect('operations:mobile_dashboard')
    today = timezone.now().date()
    return render(request, 'operations/mobile/lich_truc.html', {'danh_sach_ca_truc': PhanCongCaTruc.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(nhan_vien=nhan_vien, ngay_truc__gte=today, ngay_truc__lte=today+timedelta(days=7)).select_related('ca_lam_viec', 'vi_tri_chot__muc_tieu').order_by('ngay_truc')})

@login_required
def bao_cao_su_co_mobile_view(request):
    nhan_vien = get_mobile_context(request); 
    if not nhan_vien: return redirect('operations:mobile_dashboard')
    ca_truc = PhanCongCaTruc.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(nhan_vien=nhan_vien, chamcong__thoi_gian_check_in__isnull=False, chamcong__thoi_gian_check_out__isnull=True).last()
    if request.method == "POST":
        form = BaoCaoSuCoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                ReportIncidentUseCase.execute(
                    reporter_nv=nhan_vien,
                    form_data=form.cleaned_data,
                    files_data=request.FILES
                )
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
            else:
                messages.success(request, "Đã gửi báo cáo!")
                return redirect("operations:mobile_dashboard")
    return render(request, "operations/mobile/bao_cao_su_co.html", {"form": BaoCaoSuCoForm(), "ca_truc": ca_truc})

@login_required
def xac_nhan_alive_check(request, check_id):
    if request.method == "POST":
        # Rule 3.2: Delegated to ConfirmAliveCheckUseCase
        success, msg, _, _ = ConfirmAliveCheckUseCase.execute(check_id, request.FILES.get('anh_xac_thuc'), request.user)
        if success: messages.success(request, msg)
        else: messages.error(request, msg)
    return redirect('operations:mobile_dashboard')

@login_required
def mobile_lich_su_cham_cong(request):
    nhan_vien = get_mobile_context(request); 
    if not nhan_vien: return redirect('operations:mobile_dashboard')
    
    history_data = GetAttendanceHistoryUseCase.execute(nhan_vien)
    return render(request, 'operations/mobile/lich_su_cham_cong.html', {
        'lich_su': history_data['lich_su'], 
        'tong_cong': history_data['tong_cong'], 
        'thang': history_data['month']
    })

@login_required
def mobile_de_xuat_list(request):
    nhan_vien = get_mobile_context(request); 
    if not nhan_vien: return redirect('operations:mobile_dashboard')
    return render(request, 'operations/mobile/de_xuat_list.html', {'ds_de_xuat': BaoCaoDeXuat.objects.filter(nhan_vien=nhan_vien).order_by('-ngay_gui')})

@login_required
def mobile_de_xuat_create(request):
    nhan_vien = get_mobile_context(request)
    if not nhan_vien:
        return redirect('operations:mobile_dashboard')
    form = BaoCaoDeXuatForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            CreateFieldProposalUseCase.execute(nhan_vien, form.cleaned_data)
            messages.success(request, "Đã gửi đề xuất!")
            return redirect('operations:mobile_de_xuat_list')
        messages.error(request, "Biểu mẫu đề xuất chưa hợp lệ. Vui lòng kiểm tra lại thông tin.")
    return render(request, "operations/mobile/de_xuat_form.html", {"form": form})

@login_required
def mobile_de_xuat_detail(request, pk):
    return render(request, "operations/mobile/de_xuat_detail.html", {"de_xuat": get_object_or_404(BaoCaoDeXuat, pk=pk, nhan_vien=request.user.nhan_vien)})

@login_required
def danh_sach_muc_tieu(request):
    # Rule 4.1: Thực thi Site Scoping / Organization ID
    # MucTieu chưa có tenant_id (thuộc module clients), nhưng ta có thể lọc theo logic phân vùng sau này
    muc_tieus = (
        MucTieu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .select_related('quan_ly_muc_tieu')
        .annotate(so_vi_tri=Count('cac_vi_tri_chot'))
    )
    add_muc_tieu_admin_url = admin_url_if_permitted(
        request.user,
        "admin:clients_muctieu_add",
        "clients.add_muctieu",
    )
    return render(
        request,
        "operations/danh_sach_muc_tieu.html",
        {
            'muc_tieus': muc_tieus,
            'add_muc_tieu_admin_url': add_muc_tieu_admin_url,
        },
    )

@login_required
def chi_tiet_muc_tieu(request, pk):
    # Tận dụng các related_name đã chuẩn hóa
    muc_tieu = get_object_or_404(
        MucTieu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID),
        pk=pk,
    )
    vi_tris = ViTriChot.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(muc_tieu=muc_tieu)
    nhan_viens = NhanVien.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(cac_phan_cong__vi_tri_chot__muc_tieu=muc_tieu, cac_phan_cong__ngay_truc=timezone.now().date()).distinct()
    add_vi_tri_chot_base_url = admin_url_if_permitted(
        request.user,
        "admin:operations_vitrichot_add",
        "operations.add_vitrichot",
    )
    add_vi_tri_chot_admin_url = (
        f"{add_vi_tri_chot_base_url}?muc_tieu={muc_tieu.pk}"
        if add_vi_tri_chot_base_url
        else None
    )
    su_co_list = list(
        BaoCaoSuCo.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(muc_tieu=muc_tieu)
        .select_related("nhan_vien_bao_cao")
        .order_by("-created_at")[:8]
    )
    for su_co in su_co_list:
        su_co.admin_change_url = admin_url_if_permitted(
            request.user,
            "admin:operations_baocaosuco_change",
            "operations.change_baocaosuco",
            args=[su_co.pk],
        )
    return render(
        request,
        "operations/chi_tiet_muc_tieu.html",
        {
            'muc_tieu': muc_tieu,
            'vi_tris': vi_tris,
            'nhan_viens': nhan_viens,
            'su_co_list': su_co_list,
            'add_vi_tri_chot_admin_url': add_vi_tri_chot_admin_url,
        },
    )

@dashboard_access_required("operations:dashboard_xep_lich")
def xep_lich_view(request):
    return render(request, "operations/xep_lich.html", _build_schedule_dashboard_context(request))

@login_required
@has_permission_decorator('giao_ca_truc')
def them_ca_form_view(request, vi_tri_id, ca_id, ngay):
    if not _user_can_schedule_shifts(request.user):
        return HttpResponse(
            '<div class="text-error text-[10px] leading-tight p-1">Bạn chưa có đủ quyền thêm/sửa/xóa ca trực.</div>',
            status=403,
        )
    vi_tri = get_object_or_404(
        ViTriChot.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_related("muc_tieu"),
        id=vi_tri_id,
    )
    ca = get_object_or_404(CaLamViec.objects.for_tenant(settings.SCMD_ORGANIZATION_ID), id=ca_id)
    ngay_truc = datetime.strptime(ngay, '%Y-%m-%d').date()

    # Defense-in-depth before rendering staff candidates: functional RBAC alone
    # must not reveal an add-shift form for a target outside the caller's direct
    # scheduling scope. The mutation use case remains the authoritative write
    # guard after a staff member is selected.
    if not SiteVisibilityPolicy.managed_sites(request.user, at_time=ngay_truc).filter(
        pk=vi_tri.muc_tieu_id
    ).exists():
        return HttpResponse(
            '<div class="text-error text-[10px] leading-tight p-1">Mục tiêu không thuộc phạm vi điều phối của bạn.</div>',
            status=403,
        )

    nhan_vien_list = StaffVisibilityPolicy.visible_staff_for_scheduling(
        request.user,
        vi_tri.muc_tieu,
        at_date=ngay_truc,
    )
    return render(request, "operations/partials/them_ca_form.html", {
        "vi_tri": vi_tri,
        "ca": ca,
        "ngay_truc": ngay_truc,
        "nhan_vien_list": nhan_vien_list,
    })

@login_required
@has_permission_decorator('giao_ca_truc')
def luu_ca_view(request):
    if request.method == "POST":
        try:
            cell_context = ManageShiftAssignmentUseCase.execute(
                action='SAVE',
                actor_user=request.user,
                reason=request.POST.get("reason"),
                delete_old_id=request.POST.get("delete_old"),
                nhan_vien_id=request.POST.get("nhan_vien_id"),
                vi_tri_id=request.POST.get("vi_tri_id"),
                ca_id=request.POST.get("ca_id"),
                ngay_truc=request.POST.get("ngay_truc"),
                tenant_id=settings.SCMD_ORGANIZATION_ID,
            )
            cell_context["can_schedule"] = _user_can_schedule_shifts(request.user)
            return render(request, "operations/partials/ca_truc_cell.html", cell_context)
        except AccessScopeDenied as e:
            return HttpResponse(
                f'<div class="text-error text-[10px] leading-tight p-1">{e.result.message}</div>',
                status=403,
            )
        except ValidationError as e:
            # Trả về thông báo lỗi trực tiếp cho HTMX hiển thị tại cell
            return HttpResponse(f'<div class="text-error text-[10px] leading-tight p-1">{e.message}</div>', status=422)
            
    return redirect('operations:xep_lich')

@login_required
@has_permission_decorator('giao_ca_truc')
def sua_ca_form_view(request, phan_cong_id):
    phan_cong = get_object_or_404(
        PhanCongCaTruc.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_related(
            "vi_tri_chot__muc_tieu",
            "nhan_vien",
            "ca_lam_viec",
        ),
        id=phan_cong_id,
    )
    try:
        ShiftAssignmentPolicy.can_update_shift(request.user, phan_cong).raise_if_denied()
    except AccessScopeDenied as e:
        return HttpResponse(f'<div class="text-error text-[10px] p-1">{e.result.message}</div>', status=403)

    nhan_vien_list = StaffVisibilityPolicy.visible_staff_for_scheduling(
        request.user,
        phan_cong.vi_tri_chot.muc_tieu,
        at_date=phan_cong.ngay_truc,
    )
    return render(request, "operations/partials/sua_ca_form.html", {
        "phan_cong": phan_cong,
        "nhan_vien_list": nhan_vien_list,
    })

@login_required
@has_permission_decorator('giao_ca_truc')
@require_POST
def xoa_ca_view(request, phan_cong_id):
    try:
        cell_context = ManageShiftAssignmentUseCase.execute(
            action='DELETE',
            actor_user=request.user,
            reason=request.POST.get("reason"),
            delete_old_id=phan_cong_id,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )
        cell_context["can_schedule"] = _user_can_schedule_shifts(request.user)
        return render(request, "operations/partials/ca_truc_cell.html", cell_context)
    except AccessScopeDenied as e:
        return HttpResponse(f'<div class="text-error text-[10px] p-1">{e.result.message}</div>', status=403)
    except ValidationError as e:
        return HttpResponse(f'<div class="text-error text-[10px] p-1">{e.message}</div>', status=422)
