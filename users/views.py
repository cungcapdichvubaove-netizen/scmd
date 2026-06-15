# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: users/views.py
Author: Mr. Anh
Created Date: 2025-12-05
Updated Date: 2026-04-28
Version: v1.1.0
Description: Views xử lý logic người dùng (Nhân sự).
             UPDATED: Mobile Feature Set (Update Profile, Change Password, Salary Detail).
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from main.dashboard_router import dashboard_access_required
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from datetime import timedelta
from pathlib import Path
from weasyprint import HTML
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Count, Q
from main.dashboard_cta import admin_url_if_permitted, reverse_or_none

from main.audit_utils import export_audit_log
from main.company_info import get_company_info
from .models import (
    ACTIVE_EMPLOYEE_STATUSES,
    BangCapChungChi,
    DonNghiPhep,
    HoSoBaoHiem,
    HopDongLaoDong,
    LichSuCongTac,
    NhanVien,
    PhongBan,
    QuyetDinhNghiViec,
)
from .forms import UserProfileForm
from operations.models import PhanCongCaTruc
from accounting.models import ChiTietLuong
from clients.models import MucTieu
from inventory.application.asset_recovery_use_cases import GetEmployeeOutstandingAssetsUseCase



def _safe_reverse(viewname, *, args=None, kwargs=None):
    """Reverse URL an toàn để dashboard không crash khi admin route chưa tồn tại."""
    return reverse_or_none(viewname, args=args, kwargs=kwargs)


def _admin_url_if_permitted(user, viewname, permission_codename, *, args=None, kwargs=None):
    return admin_url_if_permitted(user, viewname, permission_codename, args=args, kwargs=kwargs)


def _admin_change_url(app_label, model_name, pk, *, user=None, permission_codename=None):
    viewname = f"admin:{app_label}_{model_name}_change"
    if user is not None and permission_codename:
        return _admin_url_if_permitted(user, viewname, permission_codename, args=[pk])
    return _safe_reverse(viewname, args=[pk])

# ==============================================================================
# 1. DASHBOARD NHÂN SỰ (HR)
# ==============================================================================
@dashboard_access_required("users:dashboard")
def dashboard_view(request):
    """Màn hình làm việc cho Phòng Hành chính Nhân sự.

    Dashboard ưu tiên operational truth cho HR: hồ sơ nhân sự, trạng thái thử việc,
    chứng chỉ/hồ sơ sắp hết hạn, thiếu dữ liệu hồ sơ và phân bổ nhân sự theo phòng ban.
    """
    today = timezone.localdate()
    now = timezone.now()
    current_month = today.month
    current_year = today.year
    period = request.GET.get("period", "month")
    if period == "today":
        date_from = today
        period_label = "Hôm nay"
    elif period == "7d":
        date_from = today - timedelta(days=6)
        period_label = "7 ngày"
    else:
        date_from = today.replace(day=1)
        period = "month"
        period_label = "Tháng này"

    next_30_days = today + timedelta(days=30)

    active_staff = NhanVien.objects.filter(trang_thai_lam_viec__in=ACTIVE_EMPLOYEE_STATUSES)
    active_staff = active_staff.select_related("phong_ban", "chuc_danh", "user")

    total_staff = active_staff.count()
    new_staff_count = active_staff.filter(ngay_vao_lam__gte=date_from).count()
    probation_staff_count = active_staff.filter(trang_thai_lam_viec=NhanVien.TrangThaiLamViec.THU_VIEC).count()
    official_staff_count = active_staff.filter(trang_thai_lam_viec=NhanVien.TrangThaiLamViec.CHINH_THUC).count()
    left_this_month_count = NhanVien.objects.filter(
        ngay_nghi_viec__month=current_month,
        ngay_nghi_viec__year=current_year,
    ).count()

    missing_profile_q = (
        Q(sdt_chinh__isnull=True) | Q(sdt_chinh="") |
        Q(phong_ban__isnull=True) |
        Q(chuc_danh__isnull=True) |
        Q(user__isnull=True)
    )
    missing_profile_staff = active_staff.filter(missing_profile_q).distinct().order_by("ho_ten")
    missing_profile_count = missing_profile_staff.count()
    no_department_count = active_staff.filter(phong_ban__isnull=True).count()
    no_user_count = active_staff.filter(user__isnull=True).count()
    missing_bank_count = active_staff.filter(Q(so_tai_khoan__isnull=True) | Q(so_tai_khoan="")).count()

    expiring_certs_qs = (
        BangCapChungChi.objects
        .filter(ngay_het_han__range=[today, next_30_days])
        .select_related("nhan_vien", "nhan_vien__phong_ban", "nhan_vien__chuc_danh")
        .order_by("ngay_het_han")
    )
    expired_certs_qs = (
        BangCapChungChi.objects
        .filter(ngay_het_han__lt=today)
        .select_related("nhan_vien", "nhan_vien__phong_ban", "nhan_vien__chuc_danh")
        .order_by("ngay_het_han")
    )

    recent_staff = list(active_staff.order_by("-ngay_vao_lam", "ho_ten")[:8])
    birthdays = active_staff.filter(ngay_sinh__month=current_month).order_by("ngay_sinh__day", "ho_ten")
    probation_staff = active_staff.filter(trang_thai_lam_viec=NhanVien.TrangThaiLamViec.THU_VIEC).order_by("ngay_vao_lam", "ho_ten")[:8]

    dept_stats_qs = (
        PhongBan.objects
        .annotate(total=Count("cac_nhan_vien", filter=Q(cac_nhan_vien__trang_thai_lam_viec__in=ACTIVE_EMPLOYEE_STATUSES)))
        .filter(total__gt=0)
        .order_by("-total", "ten_phong_ban")
    )
    max_dept_total = max([dept.total for dept in dept_stats_qs] or [1])
    dept_stats = []
    for dept in dept_stats_qs:
        dept_stats.append({
            "name": dept.ten_phong_ban,
            "total": dept.total,
            "percent": round((dept.total / max_dept_total) * 100) if max_dept_total else 0,
        })

    current_assignments = (
        LichSuCongTac.objects
        .filter(ngay_ket_thuc__isnull=True)
        .select_related("nhan_vien", "muc_tieu", "chuc_danh_kiem_nhiem", "quan_ly_truc_tiep")
        .order_by("-ngay_bat_dau")
    )
    assigned_staff_count = active_staff.filter(cac_lich_su_cong_tac__ngay_ket_thuc__isnull=True).distinct().count()
    unassigned_staff_count = max(total_staff - assigned_staff_count, 0)

    shifts_today_count = PhanCongCaTruc.objects.filter(ngay_truc=today).count()
    staff_scheduled_today_count = PhanCongCaTruc.objects.filter(ngay_truc=today).values("nhan_vien_id").distinct().count()

    labor_contracts_active_qs = HopDongLaoDong.objects.filter(
        trang_thai__in=HopDongLaoDong.ACTIVE_CONTRACT_STATUSES,
        ngay_hieu_luc__lte=today,
    ).filter(Q(ngay_het_han__isnull=True) | Q(ngay_het_han__gte=today))
    expiring_labor_contracts_qs = (
        HopDongLaoDong.objects
        .filter(
            trang_thai__in=HopDongLaoDong.ACTIVE_CONTRACT_STATUSES,
            ngay_het_han__range=[today, next_30_days],
        )
        .select_related("nhan_vien", "nhan_vien__phong_ban", "nhan_vien__chuc_danh")
        .order_by("ngay_het_han", "nhan_vien__ho_ten")
    )
    expired_active_labor_contracts_qs = (
        HopDongLaoDong.objects
        .filter(
            trang_thai__in=(
                HopDongLaoDong.TrangThai.ACTIVE,
                HopDongLaoDong.TrangThai.EXPIRING,
                HopDongLaoDong.TrangThai.EXPIRED,
            ),
            ngay_het_han__lt=today,
            nhan_vien__trang_thai_lam_viec__in=ACTIVE_EMPLOYEE_STATUSES,
        )
        .select_related("nhan_vien", "nhan_vien__phong_ban", "nhan_vien__chuc_danh")
        .order_by("ngay_het_han", "nhan_vien__ho_ten")
    )
    official_without_active_contract_qs = (
        active_staff
        .filter(trang_thai_lam_viec=NhanVien.TrangThaiLamViec.CHINH_THUC)
        .exclude(pk__in=labor_contracts_active_qs.values("nhan_vien_id"))
        .order_by("ho_ten")
    )
    expiring_labor_contracts_count = expiring_labor_contracts_qs.count()
    expired_active_labor_contracts_count = expired_active_labor_contracts_qs.count()
    missing_active_labor_contract_count = official_without_active_contract_qs.count()

    active_bhxh_qs = HoSoBaoHiem.objects.filter(
        loai_bao_hiem=HoSoBaoHiem.LoaiBaoHiem.BHXH,
        trang_thai__in=HoSoBaoHiem.ACTIVE_STATUSES,
        ngay_tham_gia__lte=today,
    ).filter(Q(ngay_ket_thuc__isnull=True) | Q(ngay_ket_thuc__gte=today))
    official_without_active_bhxh_qs = (
        active_staff
        .filter(trang_thai_lam_viec=NhanVien.TrangThaiLamViec.CHINH_THUC)
        .exclude(pk__in=active_bhxh_qs.values("nhan_vien_id"))
        .order_by("ho_ten")
    )
    pending_leave_requests_qs = (
        DonNghiPhep.objects
        .filter(trang_thai=DonNghiPhep.TrangThai.PENDING_APPROVAL)
        .select_related("nhan_vien", "nhan_vien__phong_ban", "nhan_vien__chuc_danh")
        .order_by("tu_ngay", "nhan_vien__ho_ten")
    )
    open_offboarding_qs = (
        QuyetDinhNghiViec.objects
        .filter(
            trang_thai__in=(QuyetDinhNghiViec.TrangThai.APPROVED, QuyetDinhNghiViec.TrangThai.EFFECTIVE),
            nhan_vien__trang_thai_lam_viec__in=ACTIVE_EMPLOYEE_STATUSES,
        )
        .filter(Q(checklist_ban_giao__isnull=True) | Q(checklist_ban_giao__hoan_tat=False))
        .select_related("nhan_vien", "checklist_ban_giao")
        .order_by("ngay_hieu_luc", "nhan_vien__ho_ten")
    )
    pending_leave_requests_count = pending_leave_requests_qs.count()
    missing_active_bhxh_count = official_without_active_bhxh_qs.count()
    open_offboarding_count = open_offboarding_qs.count()
    offboarding_asset_alerts = []
    for decision in open_offboarding_qs[:20]:
        outstanding_assets = GetEmployeeOutstandingAssetsUseCase.execute(nhan_vien=decision.nhan_vien)
        unresolved_damage = GetEmployeeOutstandingAssetsUseCase.has_unresolved_damage_reports(nhan_vien=decision.nhan_vien)
        if outstanding_assets or unresolved_damage:
            offboarding_asset_alerts.append({
                "decision": decision,
                "nhan_vien": decision.nhan_vien,
                "outstanding_count": sum(item["outstanding_quantity"] for item in outstanding_assets),
                "has_unresolved_damage": unresolved_damage,
            })
    offboarding_asset_alert_count = len(offboarding_asset_alerts)

    can_view_nhanvien = request.user.has_perm("users.view_nhanvien")
    can_add_nhanvien = request.user.has_perm("users.add_nhanvien")
    can_change_nhanvien = request.user.has_perm("users.change_nhanvien")
    can_view_phongban = request.user.has_perm("users.view_phongban")
    can_view_chucdanh = request.user.has_perm("users.view_chucdanh")
    can_view_hopdong = request.user.has_perm("users.view_hopdonglaodong")
    can_change_hopdong = request.user.has_perm("users.change_hopdonglaodong")
    can_view_leave = request.user.has_perm("users.view_donnghiphep")
    can_change_leave = request.user.has_perm("users.change_donnghiphep")
    can_view_insurance = request.user.has_perm("users.view_hosobaohiem")
    can_view_offboarding = request.user.has_perm("users.view_quyetdinhnghiviec")
    can_change_offboarding = request.user.has_perm("users.change_quyetdinhnghiviec")
    can_view_schedule = request.user.has_perm("operations.view_phancongcatruc")

    employee_changelist_url = _admin_url_if_permitted(request.user, "admin:users_nhanvien_changelist", "users.view_nhanvien") if can_view_nhanvien else None
    employee_add_url = _admin_url_if_permitted(request.user, "admin:users_nhanvien_add", "users.add_nhanvien") if can_add_nhanvien else None
    department_changelist_url = _admin_url_if_permitted(request.user, "admin:users_phongban_changelist", "users.view_phongban") if can_view_phongban else None
    title_changelist_url = _admin_url_if_permitted(request.user, "admin:users_chucdanh_changelist", "users.view_chucdanh") if can_view_chucdanh else None
    employee_download_template_url = _safe_reverse("admin:nhanvien-download-template") if can_view_nhanvien else None
    labor_contract_changelist_url = _admin_url_if_permitted(request.user, "admin:users_hopdonglaodong_changelist", "users.view_hopdonglaodong") if can_view_hopdong else None
    leave_request_changelist_url = _admin_url_if_permitted(request.user, "admin:users_donnghiphep_changelist", "users.view_donnghiphep") if can_view_leave else None
    insurance_changelist_url = _admin_url_if_permitted(request.user, "admin:users_hosobaohiem_changelist", "users.view_hosobaohiem") if can_view_insurance else None
    offboarding_changelist_url = _admin_url_if_permitted(request.user, "admin:users_quyetdinhnghiviec_changelist", "users.view_quyetdinhnghiviec") if can_view_offboarding else None
    for nv in recent_staff:
        nv.dashboard_export_url = _safe_reverse("users:export-ly-lich-options", args=[nv.pk]) if can_view_nhanvien else None

    action_items = []
    for contract in expired_active_labor_contracts_qs[:3]:
        action_items.append({
            "priority": "Cao",
            "tone": "danger",
            "type": "HĐLĐ đã hết hạn",
            "title": f"{contract.so_hop_dong} đã hết hạn nhưng nhân viên vẫn active",
            "subject": contract.nhan_vien.ho_ten,
            "meta": contract.nhan_vien.ma_nhan_vien,
            "date": contract.ngay_het_han,
            "url": _admin_change_url("users", "hopdonglaodong", contract.pk, user=request.user, permission_codename="users.change_hopdonglaodong") if can_change_hopdong else None,
            "cta": "Rà soát HĐLĐ",
        })
    for contract in expiring_labor_contracts_qs[:3]:
        action_items.append({
            "priority": "Cao",
            "tone": "warning",
            "type": "HĐLĐ sắp hết hạn",
            "title": f"{contract.so_hop_dong} hết hạn trong 30 ngày",
            "subject": contract.nhan_vien.ho_ten,
            "meta": contract.nhan_vien.ma_nhan_vien,
            "date": contract.ngay_het_han,
            "url": _admin_change_url("users", "hopdonglaodong", contract.pk, user=request.user, permission_codename="users.change_hopdonglaodong") if can_change_hopdong else None,
            "cta": "Gia hạn",
        })
    for nv in official_without_active_contract_qs[:3]:
        action_items.append({
            "priority": "Cao",
            "tone": "danger",
            "type": "Thiếu HĐLĐ active",
            "title": "Nhân viên chính thức chưa có hợp đồng lao động active",
            "subject": nv.ho_ten,
            "meta": nv.ma_nhan_vien,
            "date": nv.ngay_vao_lam,
            "url": _admin_change_url("users", "nhanvien", nv.pk, user=request.user, permission_codename="users.change_nhanvien") if can_change_nhanvien else None,
            "cta": "Tạo HĐLĐ",
        })
    for leave in pending_leave_requests_qs[:3]:
        action_items.append({
            "priority": "Cao",
            "tone": "warning",
            "type": "Đơn nghỉ phép chờ duyệt",
            "title": f"{leave.get_loai_nghi_display()} từ {leave.tu_ngay:%d/%m/%Y}",
            "subject": leave.nhan_vien.ho_ten,
            "meta": leave.nhan_vien.ma_nhan_vien,
            "date": leave.tu_ngay,
            "url": _admin_change_url("users", "donnghiphep", leave.pk, user=request.user, permission_codename="users.change_donnghiphep") if can_change_leave else None,
            "cta": "Duyệt đơn",
        })
    for nv in official_without_active_bhxh_qs[:3]:
        action_items.append({
            "priority": "Vừa",
            "tone": "warning",
            "type": "Thiếu BHXH active",
            "title": "Nhân viên chính thức chưa có hồ sơ BHXH active",
            "subject": nv.ho_ten,
            "meta": nv.ma_nhan_vien,
            "date": nv.ngay_vao_lam,
            "url": _admin_change_url("users", "nhanvien", nv.pk, user=request.user, permission_codename="users.change_nhanvien") if can_change_nhanvien else None,
            "cta": "Bổ sung",
        })
    for decision in open_offboarding_qs[:3]:
        action_items.append({
            "priority": "Cao",
            "tone": "danger",
            "type": "Offboarding chưa xong",
            "title": f"{decision.so_quyet_dinh} đã duyệt nhưng checklist chưa hoàn tất",
            "subject": decision.nhan_vien.ho_ten,
            "meta": decision.nhan_vien.ma_nhan_vien,
            "date": decision.ngay_hieu_luc,
            "url": _admin_change_url("users", "quyetdinhnghiviec", decision.pk, user=request.user, permission_codename="users.change_quyetdinhnghiviec") if can_change_offboarding else None,
            "cta": "Checklist",
        })
    for item in offboarding_asset_alerts[:3]:
        decision = item["decision"]
        action_items.append({
            "priority": "Cao",
            "tone": "danger",
            "type": "Tài sản chưa thu hồi",
            "title": f"Còn {item['outstanding_count']} vật tư chưa thu hồi hoặc biên bản mất/hỏng chưa xử lý",
            "subject": item["nhan_vien"].ho_ten,
            "meta": item["nhan_vien"].ma_nhan_vien,
            "date": decision.ngay_hieu_luc,
            "url": _admin_change_url("users", "quyetdinhnghiviec", decision.pk, user=request.user, permission_codename="users.change_quyetdinhnghiviec") if can_change_offboarding else None,
            "cta": "Thu hồi tài sản",
        })
    for cert in expired_certs_qs[:4]:
        action_items.append({
            "priority": "Cao",
            "tone": "danger",
            "type": "Chứng chỉ đã hết hạn",
            "title": cert.ten_bang_cap,
            "subject": cert.nhan_vien.ho_ten if cert.nhan_vien_id else "Chưa rõ nhân viên",
            "meta": cert.nhan_vien.ma_nhan_vien if cert.nhan_vien_id else "-",
            "date": cert.ngay_het_han,
            "url": (_admin_change_url("users", "nhanvien", cert.nhan_vien_id, user=request.user, permission_codename="users.change_nhanvien") if cert.nhan_vien_id else employee_changelist_url) if can_change_nhanvien else None,
            "cta": "Cập nhật hồ sơ",
        })
    for cert in expiring_certs_qs[:4]:
        action_items.append({
            "priority": "Cao",
            "tone": "warning",
            "type": "Chứng chỉ sắp hết hạn",
            "title": cert.ten_bang_cap,
            "subject": cert.nhan_vien.ho_ten if cert.nhan_vien_id else "Chưa rõ nhân viên",
            "meta": cert.nhan_vien.ma_nhan_vien if cert.nhan_vien_id else "-",
            "date": cert.ngay_het_han,
            "url": (_admin_change_url("users", "nhanvien", cert.nhan_vien_id, user=request.user, permission_codename="users.change_nhanvien") if cert.nhan_vien_id else employee_changelist_url) if can_change_nhanvien else None,
            "cta": "Gia hạn",
        })
    for nv in missing_profile_staff[:5]:
        missing_bits = []
        if not nv.sdt_chinh:
            missing_bits.append("SĐT")
        if not nv.phong_ban_id:
            missing_bits.append("phòng ban")
        if not nv.chuc_danh_id:
            missing_bits.append("chức danh")
        if not nv.user_id:
            missing_bits.append("tài khoản")
        action_items.append({
            "priority": "Vừa",
            "tone": "info",
            "type": "Hồ sơ thiếu dữ liệu",
            "title": ", ".join(missing_bits) if missing_bits else "Cần rà soát",
            "subject": nv.ho_ten,
            "meta": nv.ma_nhan_vien,
            "date": nv.ngay_vao_lam,
            "url": _admin_change_url("users", "nhanvien", nv.pk, user=request.user, permission_codename="users.change_nhanvien") if can_change_nhanvien else None,
            "cta": "Bổ sung",
        })
    action_items = [item for item in action_items if item.get("url")][:9]

    labor_contract_alert_total = (
        expiring_labor_contracts_count
        + expired_active_labor_contracts_count
        + missing_active_labor_contract_count
    )
    certificate_alert_total = expired_certs_qs.count() + expiring_certs_qs.count()
    phase_b_alert_total = (
        pending_leave_requests_count
        + missing_active_bhxh_count
        + open_offboarding_count
        + offboarding_asset_alert_count
    )

    health_cards = [
        {
            "label": "Nhân sự đang làm",
            "value": total_staff,
            "note": f"{official_staff_count} chính thức · {probation_staff_count} thử việc",
            "icon": "fa-users",
            "tone": "blue",
            "url": employee_changelist_url,
        },
        {
            "label": "Tuyển mới",
            "value": new_staff_count,
            "note": f"Phát sinh trong kỳ {period_label.lower()}",
            "icon": "fa-user-plus",
            "tone": "green",
            "url": employee_changelist_url,
        },
        {
            "label": "Hồ sơ thiếu",
            "value": missing_profile_count,
            "note": f"{no_user_count} chưa có tài khoản · {missing_bank_count} thiếu ngân hàng",
            "icon": "fa-id-card",
            "tone": "amber",
            "url": employee_changelist_url,
        },
        {
            "label": "Nhân sự đang có mục tiêu",
            "value": assigned_staff_count,
            "note": f"{unassigned_staff_count} chưa bố trí · theo lịch sử công tác hiện hành",
            "icon": "fa-map-marker-alt",
            "tone": "slate",
            "url": employee_changelist_url,
        },
        {
            "label": "Ca trực hôm nay",
            "value": shifts_today_count,
            "note": f"{staff_scheduled_today_count} nhân sự có lịch trực hôm nay",
            "icon": "fa-calendar-check",
            "tone": "purple",
            "url": _admin_url_if_permitted(request.user, "admin:operations_phancongcatruc_changelist", "operations.view_phancongcatruc") if can_view_schedule else None,
        },
        {
            "label": "Rời việc trong tháng",
            "value": left_this_month_count,
            "note": f"{open_offboarding_count} offboarding mở · {offboarding_asset_alert_count} còn tài sản",
            "icon": "fa-user-minus",
            "tone": "danger",
            "url": offboarding_changelist_url,
        },
    ]

    control_checks = [
        {
            "label": "Thiếu BHXH active",
            "count": missing_active_bhxh_count,
            "note": "Nhân sự chính thức chưa có hồ sơ BHXH active.",
            "badge_tone": "warning",
            "url": insurance_changelist_url or employee_changelist_url,
            "cta": "Rà soát BHXH",
        },
        {
            "label": "Offboarding đang mở",
            "count": open_offboarding_count,
            "note": "Quyết định nghỉ việc đã duyệt nhưng checklist chưa hoàn tất.",
            "badge_tone": "danger",
            "url": offboarding_changelist_url,
            "cta": "Kiểm tra checklist",
        },
        {
            "label": "Tài sản chưa thu hồi",
            "count": offboarding_asset_alert_count,
            "note": "Còn vật tư hoặc biên bản mất/hỏng chưa xử lý khi offboarding.",
            "badge_tone": "danger",
            "url": offboarding_changelist_url,
            "cta": "Thu hồi tài sản",
        },
        {
            "label": "Thiếu thông tin ngân hàng",
            "count": missing_bank_count,
            "note": "Cần bổ sung trước kỳ lương và chi trả.",
            "badge_tone": "info",
            "url": employee_changelist_url,
            "cta": "Bổ sung ngân hàng",
        },
        {
            "label": "Chưa có tài khoản",
            "count": no_user_count,
            "note": "Nhân sự chưa được gắn tài khoản hệ thống để dùng mobile và phân quyền.",
            "badge_tone": "warning",
            "url": employee_changelist_url,
            "cta": "Tạo/liên kết tài khoản",
        },
    ]

    context = {
        "today": today,
        "now": now,
        "period": period,
        "period_label": period_label,
        "total_staff": total_staff,
        "new_staff_count": new_staff_count,
        "new_staff": new_staff_count,
        "probation_staff_count": probation_staff_count,
        "probation_staff": probation_staff_count,
        "official_staff_count": official_staff_count,
        "left_this_month_count": left_this_month_count,
        "missing_profile_count": missing_profile_count,
        "missing_bank_count": missing_bank_count,
        "no_user_count": no_user_count,
        "no_department_count": no_department_count,
        "expired_certs_count": expired_certs_qs.count(),
        "certificate_alert_total": certificate_alert_total,
        "expiring_certs": expiring_certs_qs[:8],
        "expired_certs": expired_certs_qs[:6],
        "expiring_labor_contracts_count": expiring_labor_contracts_count,
        "expired_active_labor_contracts_count": expired_active_labor_contracts_count,
        "missing_active_labor_contract_count": missing_active_labor_contract_count,
        "labor_contract_alert_total": labor_contract_alert_total,
        "expiring_labor_contracts": expiring_labor_contracts_qs[:8],
        "expired_active_labor_contracts": expired_active_labor_contracts_qs[:8],
        "official_without_active_contract": official_without_active_contract_qs[:8],
        "pending_leave_requests_count": pending_leave_requests_count,
        "missing_active_bhxh_count": missing_active_bhxh_count,
        "phase_b_alert_total": phase_b_alert_total,
        "missing_active_insurance_count": missing_active_bhxh_count,  # Legacy context alias; mandatory insurance means active BHXH.
        "open_offboarding_count": open_offboarding_count,
        "offboarding_asset_alert_count": offboarding_asset_alert_count,
        "offboarding_asset_alerts": offboarding_asset_alerts[:8],
        "pending_leave_requests": pending_leave_requests_qs[:8],
        "official_without_active_bhxh": official_without_active_bhxh_qs[:8],
        "official_without_active_insurance": official_without_active_bhxh_qs[:8],  # Legacy context alias; does not treat BAO_HIEM_KHAC as sufficient.
        "open_offboarding": open_offboarding_qs[:8],
        "recent_staff": recent_staff,
        "birthdays": birthdays[:8],
        "probation_staff_list": probation_staff,
        "dept_stats": dept_stats,
        "current_assignments": current_assignments[:8],
        "assigned_staff_count": assigned_staff_count,
        "unassigned_staff_count": unassigned_staff_count,
        "shifts_today_count": shifts_today_count,
        "staff_scheduled_today_count": staff_scheduled_today_count,
        "action_items": action_items,
        "health_cards": health_cards,
        "control_checks": [item for item in control_checks if item.get("url")],
        "urls": {
            "employees": employee_changelist_url,
            "add_employee": employee_add_url,
            "departments": department_changelist_url,
            "titles": title_changelist_url,
            "download_template": employee_download_template_url,
            "labor_contracts": labor_contract_changelist_url,
            "leave_requests": leave_request_changelist_url,
            "insurance_profiles": insurance_changelist_url,
            "offboarding": offboarding_changelist_url,
            "operations_schedule": _admin_url_if_permitted(request.user, "admin:operations_phancongcatruc_changelist", "operations.view_phancongcatruc") if can_view_schedule else None,
        },
    }
    return render(request, "users/dashboard_hr.html", context)

# ==============================================================================
# 2. HỒ SƠ CÁ NHÂN (DESKTOP - ALL IN ONE)
# ==============================================================================
@login_required
def profile_view(request):
    try:
        nhan_vien = request.user.nhan_vien
    except AttributeError:
        messages.warning(request, "Tài khoản chưa được liên kết với hồ sơ nhân viên.")
        return redirect('main:homepage')

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=nhan_vien)
        if form.is_valid():
            form.save()
            messages.success(request, "Cập nhật hồ sơ thành công!")
            return redirect("users:profile")
    else:
        form = UserProfileForm(instance=nhan_vien)
    
    today = timezone.now().date()
    attendance_logs = PhanCongCaTruc.objects.filter(
        nhan_vien=nhan_vien,
        ngay_truc__lte=today
    ).select_related('ca_lam_viec', 'vi_tri_chot__muc_tieu', 'chamcong').order_by('-ngay_truc')[:30]

    salary_logs = ChiTietLuong.objects.filter(
        nhan_vien=nhan_vien
    ).select_related('bang_luong').order_by('-bang_luong__nam', '-bang_luong__thang')[:6]

    context = {
        "form": form,
        "nhan_vien": nhan_vien,
        "attendance_logs": attendance_logs,
        "salary_logs": salary_logs,
    }
    return render(request, "users/profile.html", context)

# ==============================================================================
# 3. MOBILE FEATURES (NÂNG CẤP)
# ==============================================================================

@login_required
def mobile_profile_view(request):
    """
    Mobile Profile: Xem & Cập nhật thông tin, Chấm công, Lương
    """
    try:
        nhan_vien = request.user.nhan_vien
    except AttributeError:
        messages.warning(request, "Tài khoản chưa liên kết hồ sơ nhân viên.")
        return redirect('operations:mobile_dashboard')

    # Xử lý Cập nhật thông tin (POST)
    if request.method == "POST" and 'update_profile' in request.POST:
        form = UserProfileForm(request.POST, request.FILES, instance=nhan_vien)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật thông tin thành công!")
            return redirect('users:mobile_profile')
        else:
            messages.error(request, "Lỗi cập nhật. Vui lòng kiểm tra lại.")
    else:
        form = UserProfileForm(instance=nhan_vien)

    today = timezone.now().date()
    ca_truc_thang = PhanCongCaTruc.objects.filter(
        nhan_vien=nhan_vien, 
        ngay_truc__month=today.month, 
        ngay_truc__year=today.year
    ).count()

    attendance_logs = PhanCongCaTruc.objects.filter(
        nhan_vien=nhan_vien, ngay_truc__lte=today
    ).select_related('ca_lam_viec', 'vi_tri_chot__muc_tieu', 'chamcong').order_by('-ngay_truc')[:30]

    salary_logs = ChiTietLuong.objects.filter(
        nhan_vien=nhan_vien
    ).select_related('bang_luong').order_by('-bang_luong__nam', '-bang_luong__thang')[:6]

    context = {
        'nhan_vien': nhan_vien,
        'form': form,
        'ca_truc_thang': ca_truc_thang,
        'attendance_logs': attendance_logs,
        'salary_logs': salary_logs,
        'now': timezone.now()
    }
    return render(request, "users/mobile/profile.html", context)

@login_required
def mobile_password_change_view(request):
    """
    View đổi mật khẩu dành riêng cho Mobile
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Giữ đăng nhập
            messages.success(request, 'Đổi mật khẩu thành công!')
            return redirect('users:mobile_profile')
        else:
            messages.error(request, 'Mật khẩu không khớp hoặc quá yếu.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'users/mobile/password_change.html', {'form': form})

@login_required
def mobile_salary_detail_view(request, luong_id):
    """
    View xem chi tiết phiếu lương Mobile
    """
    salary = get_object_or_404(ChiTietLuong, id=luong_id, nhan_vien__user=request.user)
    return render(request, 'users/mobile/salary_detail.html', {'salary': salary})

# ==============================================================================
# 4. EXPORT PDF
# ==============================================================================
@login_required
@permission_required('users.view_nhanvien', raise_exception=True)
def export_ly_lich_options_view(request, nhan_vien_id):
    nhan_vien = get_object_or_404(
        NhanVien.objects.for_tenant(settings.SCMD_ORGANIZATION_ID),
        pk=nhan_vien_id,
    )
    return render(request, "users/ly_lich_options.html", {"nhan_vien": nhan_vien})

@login_required
@permission_required('users.view_nhanvien', raise_exception=True)
@export_audit_log(
    module="users",
    model_name="NhanVien",
    note="Export PDF ly lich nhan vien",
    object_id_resolver=lambda request, nhan_vien_id: nhan_vien_id,
    changes_resolver=lambda request, nhan_vien_id: {
        "bao_gom_anh_the": request.POST.get("bao_gom_anh_the") == "on",
        "bao_gom_thong_tin_ca_nhan": request.POST.get("bao_gom_thong_tin_ca_nhan") == "on",
        "bao_gom_bang_cap": request.POST.get("bao_gom_bang_cap") == "on",
        "bao_gom_lich_su_cong_tac": request.POST.get("bao_gom_lich_su_cong_tac") == "on",
    },
)
def export_ly_lich_pdf(request, nhan_vien_id):
    nhan_vien = get_object_or_404(
        NhanVien.objects.for_tenant(settings.SCMD_ORGANIZATION_ID),
        pk=nhan_vien_id,
    )
    options = {
        "bao_gom_anh_the": request.POST.get("bao_gom_anh_the") == "on",
        "bao_gom_thong_tin_ca_nhan": request.POST.get("bao_gom_thong_tin_ca_nhan") == "on",
        "bao_gom_bang_cap": request.POST.get("bao_gom_bang_cap") == "on",
        "bao_gom_lich_su_cong_tac": request.POST.get("bao_gom_lich_su_cong_tac") == "on",
    }
    avatar_uri = ""
    if options["bao_gom_anh_the"] and nhan_vien.anh_the:
        try:
            avatar_path = Path(nhan_vien.anh_the.path)
            if avatar_path.exists(): avatar_uri = avatar_path.as_uri()
        except: pass
    
    html_string = render_to_string("users/ly_lich_pdf.html", {
        "nhan_vien": nhan_vien,
        "options": options,
        "avatar_uri": avatar_uri,
        "COMPANY": get_company_info(),
    })
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="ly_lich_{nhan_vien.ma_nhan_vien}.pdf"'
    return response

@login_required
@permission_required('users.view_nhanvien', raise_exception=True)
@export_audit_log(
    module="users",
    model_name="NhanVien",
    note="Export PDF the ten nhan vien",
    object_id_resolver=lambda request, nhan_vien_id: nhan_vien_id,
    changes_resolver=lambda request, nhan_vien_id: {},
)
def export_the_ten_pdf(request, nhan_vien_id):
    """Xuất file PDF thẻ tên nhân viên chuyên nghiệp (Standard ID Card)"""
    nhan_vien = get_object_or_404(
        NhanVien.objects.for_tenant(settings.SCMD_ORGANIZATION_ID),
        pk=nhan_vien_id,
    )
    
    html_string = render_to_string("users/pdf/the_ten.html", {
        "nv": nhan_vien,
        "now": timezone.now(),
    })
    
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="the_ten_{nhan_vien.ma_nhan_vien}.pdf"'
    return response

@login_required
@permission_required('users.view_nhanvien', raise_exception=True)
@export_audit_log(
    module="users",
    model_name="MucTieu",
    note="Export PDF danh sach nhan su muc tieu",
    object_id_resolver=lambda request, muc_tieu_id: muc_tieu_id,
    changes_resolver=lambda request, muc_tieu_id: {},
)
def export_danh_sach_nhan_su_muc_tieu_pdf(request, muc_tieu_id):
    """Xuất danh sách nhân sự đang công tác tại một mục tiêu cụ thể (Site Personnel)"""
    muc_tieu = get_object_or_404(
        MucTieu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID),
        pk=muc_tieu_id,
    )
    
    # SSOT: Lấy từ lịch sử công tác đang hoạt động
    nhan_su = LichSuCongTac.objects.filter(
        muc_tieu=muc_tieu,
        nhan_vien__tenant_id=settings.SCMD_ORGANIZATION_ID,
        ngay_ket_thuc__isnull=True,
    ).select_related('nhan_vien', 'nhan_vien__chuc_danh')

    html_string = render_to_string("users/pdf/danh_sach_muc_tieu.html", {
        "muc_tieu": muc_tieu,
        "nhan_su": nhan_su,
        "now": timezone.now()
    })

    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="danh_sach_nhan_su_{muc_tieu.id}.pdf"'
    return response
