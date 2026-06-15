# -*- coding: utf-8 -*-
"""
Application Layer: Attendance Use Cases.
Coordinates business flows for Check-in and Check-out.
Version: v2.0.1 (Hardening Phase)
"""

import logging
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.db import transaction, IntegrityError
<<<<<<< HEAD
from django.core.exceptions import ValidationError
from core.audit_context import allow_attendance_mutation
from core.domain.geo import GeofenceEvaluator
from operations.application.attendance_policies import (
    AttendancePhotoPolicy,
    AttendanceWindowPolicy,
)
from operations.analytics import calculate_swap_rate
from operations.models import ChamCong, PhanCongCaTruc, BaoCaoSuCo, KiemTraQuanSo
from datetime import timedelta, datetime
from django.db.models import Count, Q
from main.models import AuditLog
from main.constants import OPERATIONS_NOTIFICATION_GROUPS
=======
from core.domain.geo import validate_geofence
from operations.analytics import calculate_swap_rate
from operations.models import ChamCong, PhanCongCaTruc, BaoCaoSuCo, KiemTraQuanSo
from datetime import timedelta, datetime
from django.db.models import Q
from main.models import AuditLog
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from operations.tasks import process_timesheet_async
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)
<<<<<<< HEAD
DEMO_GPS_NOTE_MARKER = "[DEMO] Fake GPS Used"


def _shift_lock_queryset(tenant_id):
    """Return a minimal organization-scoped shift queryset for row locks.

    ``PhanCongCaTruc.objects`` uses an optimized read manager that joins related
    rows, including nullable reverse attendance data. PostgreSQL rejects
    ``SELECT ... FOR UPDATE`` when such nullable outer joins are present.  Lock
    the base shift row through the model base manager, keep the tenant guard, and
    let callers access related objects after the lock without weakening the
    transaction boundary.
    """
    if str(tenant_id) != str(settings.SCMD_ORGANIZATION_ID):
        return PhanCongCaTruc._base_manager.none()
    return PhanCongCaTruc._base_manager.filter(tenant_id=tenant_id)


def _lock_shift_for_update(shift_id, tenant_id):
    return _shift_lock_queryset(tenant_id).select_for_update().get(pk=shift_id)
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

class GetMobileDashboardUseCase:
    @staticmethod
    def execute(nhan_vien):
        """
        Logic xác định ca trực ưu tiên hiển thị trên Dashboard.
<<<<<<< HEAD
        Bổ sung: Lấy yêu cầu Alive Check đang chờ phản hồi.
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        """
        today = timezone.localtime(timezone.now()).date()
        yesterday = today - timedelta(days=1)
        current_dt = timezone.now()
        
<<<<<<< HEAD
        def get_result(pc, status):
            alive_check = None
            if pc:
                alive_check = KiemTraQuanSo.objects.filter(ca_truc=pc, trang_thai='PENDING').first()
            return pc, status, alive_check

        # Lấy các phân công trong 2 ngày gần nhất, cưỡng chế organization scope.
        phan_congs = PhanCongCaTruc.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(
            nhan_vien=nhan_vien,
            nhan_vien__tenant_id=settings.SCMD_ORGANIZATION_ID,
=======
        # Lấy các phân công trong 2 ngày gần nhất
        phan_congs = PhanCongCaTruc.objects.filter(
            nhan_vien=nhan_vien, 
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            ngay_truc__range=[yesterday, today]
        ).select_related('vi_tri_chot__muc_tieu', 'ca_lam_viec').order_by('ngay_truc', 'ca_lam_viec__gio_bat_dau')
        
        ca_truc_uu_tien = None
        trang_thai = False # False: Chưa check-in, True: Đang trực, "DONE": Đã xong

        # 1. Ưu tiên ca đang trực (đã check-in nhưng chưa check-out)
        for pc in phan_congs:
            if hasattr(pc, 'chamcong') and pc.chamcong.thoi_gian_check_in and not pc.chamcong.thoi_gian_check_out:
<<<<<<< HEAD
                return get_result(pc, True)
=======
                return pc, True
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

        # 2. Tìm ca sắp tới (trong vòng 60p trước giờ bắt đầu) hoặc đang trong giờ trực nhưng chưa check-in
        for pc in phan_congs:
            if hasattr(pc, 'chamcong') and pc.chamcong.thoi_gian_check_out:
                continue
            
            from datetime import datetime
            # Chuyển đổi naive datetime sang aware để so sánh
            start_real = timezone.make_aware(datetime.combine(pc.ngay_truc, pc.ca_lam_viec.gio_bat_dau))
            
            if pc.ca_lam_viec.is_night_shift:
                end_real = timezone.make_aware(datetime.combine(pc.ngay_truc + timedelta(days=1), pc.ca_lam_viec.gio_ket_thuc))
            else:
                end_real = timezone.make_aware(datetime.combine(pc.ngay_truc, pc.ca_lam_viec.gio_ket_thuc))
            
            if end_real > current_dt and (start_real - timedelta(minutes=60)) <= current_dt:
<<<<<<< HEAD
                return get_result(pc, False)
=======
                return pc, False
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

        # 3. Fallback: Ca đầu tiên của hôm nay chưa check-in
        ca_hom_nay = phan_congs.filter(ngay_truc=today, chamcong__thoi_gian_check_in__isnull=True).first()
        if ca_hom_nay:
<<<<<<< HEAD
            return get_result(ca_hom_nay, False)
=======
            return ca_hom_nay, False
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            
        # 4. Cuối cùng: Ca vừa kết thúc
        last_pc = phan_congs.last()
        if last_pc and hasattr(last_pc, 'chamcong') and last_pc.chamcong.thoi_gian_check_out:
<<<<<<< HEAD
            return get_result(last_pc, "DONE")
            
        return None, False, None



def _has_gps_coordinates(lat, lng):
    """Return True when caller supplied both GPS coordinates.

    Avoid truthiness checks because valid coordinates can be numeric zero.
    Treat empty strings and literal client-side ``"null"`` as missing.
    """
    missing_values = (None, "", "null")
    return lat not in missing_values and lng not in missing_values


def _contains_demo_gps_marker(note):
    return DEMO_GPS_NOTE_MARKER in (note or "")
=======
            return last_pc, "DONE"
            
        return None, False
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

class CheckInUseCase:
    @staticmethod
    def execute(phan_cong, lat, lng, image, ip, device_info, note="", user=None) -> tuple[bool, str, dict | None, str | None]:
        """
        Thực thi quy trình Check-in.
        Logic Geofencing được tách biệt vào Domain Layer.
        """
        # 1. Domain Logic: Xác thực Geofencing (SSOT từ CRM/Target)
<<<<<<< HEAD
        is_valid_window, window_error = AttendanceWindowPolicy.validate(
            phan_cong=phan_cong,
            action=AttendanceWindowPolicy.CHECKIN,
        )
        if not is_valid_window:
            return False, window_error, None, "OUTSIDE_CHECKIN_WINDOW"

        if AttendancePhotoPolicy.is_required(
            phan_cong=phan_cong,
            action=AttendancePhotoPolicy.CHECKIN,
        ) and not image:
            return False, "Ca truc nay bat buoc anh check-in.", None, "MISSING_REQUIRED_IMAGE"

        if _contains_demo_gps_marker(note):
            return False, "Khong chap nhan GPS gia lap trong luong check-in.", None, "DEMO_GPS_FORBIDDEN"

        is_valid_location = False
        distance = 0.0
        has_gps = _has_gps_coordinates(lat, lng)
        missing_gps = not has_gps
        
        target = phan_cong.vi_tri_chot.muc_tieu # SSOT: Lấy thông tin mục tiêu từ PhanCongCaTruc
        gps_required = bool(
            getattr(target, "bat_buoc_gps_checkin", False)
            or getattr(settings, "SCMD_REQUIRE_GPS_FOR_CHECKIN", False)
        )
        if missing_gps and gps_required:
            return False, "Ca trực này bắt buộc GPS khi check-in.", None, "MISSING_REQUIRED_GPS"

        if has_gps and target.vi_do is not None and target.kinh_do is not None:
            geofence_result = GeofenceEvaluator.validate(
                user_lat=float(lat),
                user_lng=float(lng),
                target_lat=float(target.vi_do),
                target_lng=float(target.kinh_do),
                radius_m=float(target.ban_kinh_cho_phep or 100),
            )
            is_valid_location = geofence_result.is_within_radius
            distance = geofence_result.distance_meters

        # 2. Infrastructure: Lưu trữ dữ liệu vào Database
        with transaction.atomic():
            # Organization scope is derived from the assigned shift, never from request payload.
            tenant_id = phan_cong.tenant_id
            locked_shift = _lock_shift_for_update(phan_cong.pk, tenant_id)
            point = Point(float(lng), float(lat), srid=4326) if has_gps else None

            try:
                cham_cong, created = ChamCong.objects.get_or_create(
                    ca_truc=locked_shift,
                    tenant_id=tenant_id,
                    defaults={
                        'thoi_gian_check_in': timezone.now(),
                        'anh_check_in': image,
                        'location_check_in': point,
                        'ip_check_in': ip,
                        'thiet_bi_check_in': device_info,
                        'vi_tri_hop_le': is_valid_location,
                        'khoang_cach_check_in': distance,
                        'ghi_chu': note
                    }
                )
            except IntegrityError:
                cham_cong = ChamCong.objects.select_for_update().get(ca_truc=locked_shift)
                return False, "Ban da check-in ca nay roi.", {"time": cham_cong.thoi_gian_check_in}, "ALREADY_CHECKED_IN"
=======
        is_valid_location = True
        distance = 0.0
        
        target = phan_cong.vi_tri_chot.muc_tieu # SSOT: Lấy thông tin mục tiêu từ PhanCongCaTruc
        if lat and lng and target.vi_do and target.kinh_do:
            is_valid_location, distance = validate_geofence(
                float(lat),
                float(lng),
                float(target.vi_do),
                float(target.kinh_do),
                float(target.ban_kinh_cho_phep or 100)
            )

        # 2. Infrastructure: Lưu trữ dữ liệu vào Database
        with transaction.atomic():
            point = Point(float(lng), float(lat), srid=4326) if lat and lng else None
            
            # Lấy tenant_id từ phan_cong (SSOT)
            tenant_id = phan_cong.tenant_id

            cham_cong, created = ChamCong.objects.get_or_create(
                ca_truc=phan_cong,
                tenant_id=tenant_id,
                defaults={
                    'thoi_gian_check_in': timezone.now(),
                    'anh_check_in': image,
                    'location_check_in': point,
                    'ip_check_in': ip,
                    'thiet_bi_check_in': device_info,
                    'vi_tri_hop_le': is_valid_location,
                    'khoang_cach_check_in': distance,
                    'ghi_chu': note
                }
            )
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            
            if not created:
                return False, "Bạn đã check-in ca này rồi.", {"time": cham_cong.thoi_gian_check_in}, "ALREADY_CHECKED_IN"

            # 3. Security Audit Log
            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.EXECUTE,
                module="Operations",
                model_name="ChamCong",
                object_id=str(cham_cong.id),
                ip_address=ip,
                user_agent=device_info,
                note=f"Check-in tại {phan_cong.vi_tri_chot.muc_tieu.ten_muc_tieu}. Distance: {distance}m",
<<<<<<< HEAD
                tenant_id=tenant_id,
                changes={
                    "gps_present": not missing_gps,
                    "gps_required": gps_required,
                    "vi_tri_hop_le": is_valid_location,
                    "distance_meters": distance,
                },
=======
                tenant_id=tenant_id
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            )

        return True, "Check-in thành công.", {"time": cham_cong.thoi_gian_check_in, "id": cham_cong.id}, None

class CheckOutUseCase:
    @staticmethod
    def execute(phan_cong, lat, lng, image, ip, device_info, note="", user=None) -> tuple[bool, str, dict | None, str | None]:
<<<<<<< HEAD
        is_valid_window, window_error = AttendanceWindowPolicy.validate(
            phan_cong=phan_cong,
            action=AttendanceWindowPolicy.CHECKOUT,
        )
        if not is_valid_window:
            return False, window_error, None, "OUTSIDE_CHECKOUT_WINDOW"

        if AttendancePhotoPolicy.is_required(
            phan_cong=phan_cong,
            action=AttendancePhotoPolicy.CHECKOUT,
        ) and not image:
            return False, "Ca truc nay bat buoc anh check-out.", None, "MISSING_REQUIRED_IMAGE"
        if _contains_demo_gps_marker(note):
            return False, "Khong chap nhan GPS gia lap trong luong check-out.", None, "DEMO_GPS_FORBIDDEN"
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        """
        Thực thi quy trình Check-out.
        """
        with transaction.atomic():
            try:
                # Rule 10: Enforce row lock to prevent race conditions during concurrent check-out attempts.
                cham_cong = ChamCong.objects.select_for_update().get(ca_truc=phan_cong)
            except ChamCong.DoesNotExist:
                return False, "Chưa tìm thấy dữ liệu Check-in.", None, "CHECKIN_DATA_NOT_FOUND"

            if cham_cong.thoi_gian_check_out:
                return False, "Ca trực này đã check-out rồi.", {"time": cham_cong.thoi_gian_check_out}, "ALREADY_CHECKED_OUT"

            cham_cong.thoi_gian_check_out = timezone.now()
            cham_cong.anh_check_out = image
<<<<<<< HEAD
            if _has_gps_coordinates(lat, lng):
=======
            if lat and lng:
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                cham_cong.location_check_out = Point(float(lng), float(lat), srid=4326)
            cham_cong.ip_check_out = ip
            cham_cong.thiet_bi_check_out = device_info
            if note:
                cham_cong.ghi_chu = (cham_cong.ghi_chu or "") + " | " + note
<<<<<<< HEAD
            with allow_attendance_mutation("ATTENDANCE_CHECKOUT_USE_CASE"):
                cham_cong.save()
=======
            cham_cong.save()
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            phan_cong.da_checkin = False # Reset flag if model has it
            
            # 3. Security Audit Log
            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.EXECUTE,
                module="Operations",
                model_name="ChamCong",
                object_id=str(cham_cong.id),
                ip_address=ip,
                user_agent=device_info,
                note=f"Check-out thành công cho ca ID: {phan_cong.id}",
                tenant_id=phan_cong.tenant_id
            )
            
            # 4. Async Task: Trigger tính lương ngay lập tức (SSOT Section 7)
            transaction.on_commit(lambda: process_timesheet_async.delay(cham_cong.id))

        return True, "Check-out thành công.", {"time": cham_cong.thoi_gian_check_out, "id": cham_cong.id}, None

class CalculateWorkHoursUseCase:
    @staticmethod
    def execute(cham_cong):
        """
        Tính toán tổng giờ làm việc thực tế dựa trên dữ liệu chấm công.
        Business Rule: Chỉ tính khi có đủ In/Out.
        """
        if not cham_cong.thoi_gian_check_in or not cham_cong.thoi_gian_check_out:
            return 0.0
        
        delta = cham_cong.thoi_gian_check_out - cham_cong.thoi_gian_check_in
        total_seconds = delta.total_seconds()
        
        # Anti-fraud: Kiểm tra thời gian âm (Check-out trước Check-in)
        if total_seconds < 0:
            logger.error(
                f"CRITICAL: Negative work hours detected for ChamCong ID {cham_cong.id}. "
                f"In: {cham_cong.thoi_gian_check_in}, Out: {cham_cong.thoi_gian_check_out}"
            )
            return 0.0
            
        return round(total_seconds / 3600, 2)

class TriggerSOSUseCase:
<<<<<<< HEAD
    OUTSIDE_SHIFT_MESSAGE = "Chỉ có thể gửi SOS vận hành khi đang trong ca trực đã check-in."

    @staticmethod
    def execute(nhan_vien, lat, lng) -> tuple[bool, str, any, str | None]:
        """Send an emergency SOS linked to the active shift and target.

        SOS is intentionally kept, but it must not create an orphan operational
        incident. If the business later accepts off-shift SOS, that workflow must
        be represented by a separate incident origin/state instead of silently
        creating ``muc_tieu=None`` / ``ca_truc=None`` records.
        """
        if not _has_gps_coordinates(lat, lng):
            return False, "Khong the gui SOS khi thieu GPS thuc. Vui long bat dinh vi va thu lai.", None, "MISSING_REQUIRED_GPS"

        from operations.application.incident_reporting_use_cases import ReportIncidentUseCase

        try:
            ca_truc = ReportIncidentUseCase.resolve_active_shift_or_raise(nhan_vien)
        except ValidationError as exc:
            logger.warning("Blocked orphan SOS for employee=%s: %s", getattr(nhan_vien, "pk", None), exc)
            return False, TriggerSOSUseCase.OUTSIDE_SHIFT_MESSAGE, None, "NO_ACTIVE_SHIFT"

        with transaction.atomic():
            ca_truc = _lock_shift_for_update(ca_truc.pk, settings.SCMD_ORGANIZATION_ID)
            muc_tieu = ca_truc.vi_tri_chot.muc_tieu if ca_truc.vi_tri_chot else None
            if muc_tieu is None:
                return False, ReportIncidentUseCase.ACTIVE_SHIFT_SITE_REQUIRED_MESSAGE, None, "SHIFT_WITHOUT_SITE"

=======
    @staticmethod
    def execute(nhan_vien, lat, lng) -> tuple[bool, str, any, str | None]:
        """Logic gửi tín hiệu SOS khẩn cấp."""
        ca_truc = PhanCongCaTruc.objects.filter(
            nhan_vien=nhan_vien, 
            chamcong__thoi_gian_check_in__isnull=False, 
            chamcong__thoi_gian_check_out__isnull=True
        ).last()
        muc_tieu = ca_truc.vi_tri_chot.muc_tieu if ca_truc else None
        
        with transaction.atomic():
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            su_co = BaoCaoSuCo.objects.create(
                tenant_id=settings.SCMD_ORGANIZATION_ID,
                tieu_de=f"🆘 CẤP CỨU: {nhan_vien.ho_ten.upper()}",
                nhan_vien_bao_cao=nhan_vien,
                muc_do='NGUY_HIEM',
                trang_thai='CHO_XU_LY',
                thoi_gian_phat_hien=timezone.now(),
                muc_tieu=muc_tieu,
                ca_truc=ca_truc,
<<<<<<< HEAD
                mo_ta_chi_tiet=f"SOS từ Mobile Web. Vị trí GPS: {lat}, {lng}",
            )
            AuditLog.objects.create(
                user=getattr(nhan_vien, "user", None),
                action=AuditLog.Action.CREATE,
                module="operations",
                model_name="BaoCaoSuCo",
                object_id=str(su_co.pk),
                tenant_id=settings.SCMD_ORGANIZATION_ID,
                note=f"Gửi SOS trong ca trực {ca_truc.pk} tại mục tiêu {muc_tieu.pk}.",
                changes={
                    "origin": "mobile_sos",
                    "shift_id": ca_truc.pk,
                    "site_id": muc_tieu.pk,
                    "muc_do": su_co.muc_do,
                    "trang_thai": su_co.trang_thai,
                },
=======
                mo_ta_chi_tiet=f"SOS từ Mobile Web. Vị trí GPS: {lat}, {lng}"
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            )
        return True, "ĐÃ GỬI TÍN HIỆU KHẨN CẤP!", su_co, None

class ConfirmAliveCheckUseCase:
    @staticmethod
    def execute(check_id, image, user) -> tuple[bool, str, any, str | None]:
        """Logic xác nhận điểm danh Alive Check."""
<<<<<<< HEAD
        with transaction.atomic():
            # Rule 4.3: Enforce row lock to prevent race conditions with overdue tasks.
            alive = (
                KiemTraQuanSo.objects
                .for_tenant(settings.SCMD_ORGANIZATION_ID)
                .select_for_update()
                .filter(id=check_id)
                .first()
            )
            
            if not alive:
                return False, "Yêu cầu kiểm tra không tồn tại.", None, "NOT_FOUND"
            
            # State Guard: Nếu đã xử lý (OK/MISSED/LATE), chặn ghi đè để bảo vệ integrity.
            if alive.trang_thai != 'PENDING':
                return False, f"Yêu cầu đã kết thúc (Trạng thái: {alive.get_trang_thai_display()}).", None, "ALREADY_PROCESSED"

            if alive.ca_truc.nhan_vien.user != user:
                return False, "Bạn không có quyền xác nhận yêu cầu này.", None, "FORBIDDEN"

=======
        # Rule 4.1: Enforce tenant isolation
        alive = KiemTraQuanSo.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(id=check_id).first()
        
        if not alive:
            return False, "Yêu cầu kiểm tra không tồn tại.", None, "NOT_FOUND"
        
        if alive.ca_truc.nhan_vien.user != user:
            return False, "Bạn không có quyền xác nhận yêu cầu này.", None, "FORBIDDEN"

        with transaction.atomic():
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            alive.anh_xac_thuc = image
            alive.thoi_gian_phan_hoi = timezone.now()
            alive.trang_thai = 'OK'
            alive.save()
            
        return True, "Xác nhận điểm danh thành công!", alive, None

class GetSwapRateReportUseCase:
    """
    Application Layer: Báo cáo tỷ lệ đổi ca theo Mục tiêu.
    Phân tích độ ổn định nhân sự (Personnel Stability).
<<<<<<< HEAD

    Phase D hardening: callers must pass ``user`` so the use case can derive an
    operations scope, pass an already-scoped ``allowed_targets_qs`` from a trusted
    workflow, or explicitly opt into full-tenant scheduled-job scope with
    ``system_context=True``. API callers must never query all targets with
    authentication alone or by accidentally omitting user context.
    """
    @staticmethod
    def execute(month: int, year: int, tenant_id: str, *, user=None, allowed_targets_qs=None, system_context=False):
        from django.core.exceptions import PermissionDenied
        from clients.models import MucTieu
        from operations.application.shift_change_permission_policy import ShiftChangePermissionPolicy
        from operations.models import ShiftChangeRequest

        if allowed_targets_qs is None and user is not None:
            allowed_targets_qs = ShiftChangePermissionPolicy.allowed_sites_for_swap_rate_report(user)

        # Phase D v2: full-tenant report scope must be explicit. This prevents
        # future API/UI callers from accidentally omitting ``user`` and exposing
        # all targets. Scheduled/internal jobs may still opt in by passing
        # ``system_context=True``.
        if allowed_targets_qs is None:
            if not system_context:
                raise PermissionDenied(
                    "Swap-rate report requires a user-scoped queryset or explicit system_context=True."
                )
            muc_tieus = MucTieu.objects.for_tenant(tenant_id)
            scope = "system_all_targets"
        else:
            muc_tieus = allowed_targets_qs.filter(tenant_id=tenant_id).distinct()
            scope = "user_allowed_targets"

        target_list = list(muc_tieus)
        target_ids = [mt.id for mt in target_list]

        period_start = datetime(year, month, 1).date()
        if month == 12:
            period_end = datetime(year + 1, 1, 1).date()
        else:
            period_end = datetime(year, month + 1, 1).date()

        planned_counts = {
            row["vi_tri_chot__muc_tieu_id"]: row["total"]
            for row in (
                PhanCongCaTruc.objects.for_tenant(tenant_id)
                .filter(
                    vi_tri_chot__muc_tieu_id__in=target_ids,
                    ngay_truc__gte=period_start,
                    ngay_truc__lt=period_end,
                )
                .values("vi_tri_chot__muc_tieu_id")
                .annotate(total=Count("id"))
            )
        }

        request_counts = {
            row["phan_cong_goc__vi_tri_chot__muc_tieu_id"]: row
            for row in (
                ShiftChangeRequest.objects.for_tenant(tenant_id)
                .filter(
                    phan_cong_goc__vi_tri_chot__muc_tieu_id__in=target_ids,
                    loai_yeu_cau__in=[
                        ShiftChangeRequest.LoaiYeuCau.CHANGE_SHIFT,
                        ShiftChangeRequest.LoaiYeuCau.SWAP_STAFF,
                        ShiftChangeRequest.LoaiYeuCau.OVERTIME,
                    ],
                    phan_cong_goc__ngay_truc__gte=period_start,
                    phan_cong_goc__ngay_truc__lt=period_end,
                )
                .values("phan_cong_goc__vi_tri_chot__muc_tieu_id")
                .annotate(
                    requested=Count("id"),
                    approved=Count("id", filter=Q(trang_thai=ShiftChangeRequest.TrangThai.APPROVED)),
                    applied=Count("id", filter=Q(trang_thai=ShiftChangeRequest.TrangThai.APPLIED)),
                )
            )
        }

        report_data = []

        for mt in target_list:
            total_planned = planned_counts.get(mt.id, 0)
            request_stat = request_counts.get(mt.id, {})
            shift_change_requested = request_stat.get("requested", 0)
            shift_change_approved = request_stat.get("approved", 0)
            shift_change_applied = request_stat.get("applied", 0)

            # 3. Tính toán qua Domain Logic trên số đã áp dụng thật
            rate = calculate_swap_rate(shift_change_applied, total_planned)
=======
    """
    @staticmethod
    def execute(month: int, year: int, tenant_id: str):
        from clients.models import MucTieu
        from operations.models import BaoCaoDeXuat

        # 1. Lấy danh sách mục tiêu đang hoạt động
        muc_tieus = MucTieu.objects.all()
        report_data = []

        for mt in muc_tieus:
            # 2. Tổng số ca trực đã xếp trong kỳ (SSOT: PhanCongCaTruc)
            total_planned = PhanCongCaTruc.objects.filter(
                vi_tri_chot__muc_tieu=mt,
                ngay_truc__month=month,
                ngay_truc__year=year,
                tenant_id=tenant_id
            ).count()

            # 3. Số ca đã thực hiện đổi thành công (SSOT: BaoCaoDeXuat[DOI_CA])
            swaps_approved = BaoCaoDeXuat.objects.filter(
                ca_truc__vi_tri_chot__muc_tieu=mt,
                loai_de_xuat='DOI_CA',
                trang_thai='DA_XU_LY', # Trạng thái đã phê duyệt thành công
                ca_truc__ngay_truc__month=month,
                ca_truc__ngay_truc__year=year,
                tenant_id=tenant_id
            ).count()

            # 4. Tính toán qua Domain Logic
            rate = calculate_swap_rate(swaps_approved, total_planned)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

            report_data.append({
                "muc_tieu_id": mt.id,
                "ten_muc_tieu": mt.ten_muc_tieu,
                "total_shifts": total_planned,
<<<<<<< HEAD
                "swap_count": shift_change_applied,
                "swap_rate": rate,
                "shift_change_requested_count": shift_change_requested,
                "shift_change_approved_count": shift_change_approved,
                "shift_change_applied_count": shift_change_applied,
                "metric_basis": "APPLIED",
                "scope": scope,
=======
                "swap_count": swaps_approved,
                "swap_rate": rate,
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                "stability_index": "STABLE" if rate < 10 else "MODERATE" if rate < 25 else "UNSTABLE"
            })

        # Sắp xếp theo tỷ lệ đổi ca giảm dần để Ban Giám đốc nhận diện điểm nóng
        report_data.sort(key=lambda x: x['swap_rate'], reverse=True)

<<<<<<< HEAD
        return {"month": month, "year": year, "scope": scope, "results": report_data}
=======
        return {"month": month, "year": year, "results": report_data}
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

class MonitorWeeklySwapRateUseCase:
    """
    Application Layer: Giám sát tỷ lệ đổi ca tự động.
    Tần suất check: Định kỳ (qua Celery).
    Ngưỡng cảnh báo: 30% trong 7 ngày.
    """
    @staticmethod
    def execute(tenant_id: str):
        from clients.models import MucTieu
<<<<<<< HEAD
        from operations.models import ShiftChangeRequest
=======
        from operations.models import BaoCaoDeXuat
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

        # 1. Thiết lập khoảng thời gian: 7 ngày qua
        today = timezone.now().date()
        start_date = today - timedelta(days=7)
        
<<<<<<< HEAD
        muc_tieus = list(MucTieu.objects.for_tenant(tenant_id))
        target_ids = [mt.id for mt in muc_tieus]
        alerts_triggered = 0

        planned_counts = {
            row["vi_tri_chot__muc_tieu_id"]: row["total"]
            for row in (
                PhanCongCaTruc.objects.for_tenant(tenant_id)
                .filter(
                    vi_tri_chot__muc_tieu_id__in=target_ids,
                    ngay_truc__range=[start_date, today],
                )
                .values("vi_tri_chot__muc_tieu_id")
                .annotate(total=Count("id"))
            )
        }
        applied_counts = {
            row["phan_cong_goc__vi_tri_chot__muc_tieu_id"]: row["total"]
            for row in (
                ShiftChangeRequest.objects.for_tenant(tenant_id)
                .filter(
                    phan_cong_goc__vi_tri_chot__muc_tieu_id__in=target_ids,
                    loai_yeu_cau__in=[
                        ShiftChangeRequest.LoaiYeuCau.CHANGE_SHIFT,
                        ShiftChangeRequest.LoaiYeuCau.SWAP_STAFF,
                        ShiftChangeRequest.LoaiYeuCau.OVERTIME,
                    ],
                    trang_thai=ShiftChangeRequest.TrangThai.APPLIED,
                    phan_cong_goc__ngay_truc__range=[start_date, today],
                )
                .values("phan_cong_goc__vi_tri_chot__muc_tieu_id")
                .annotate(total=Count("id"))
            )
        }

        for mt in muc_tieus:
            total_planned = planned_counts.get(mt.id, 0)
            swaps_applied = applied_counts.get(mt.id, 0)

            rate = calculate_swap_rate(swaps_applied, total_planned)

            # 2. Kiểm tra ngưỡng (Threshold: 30%)
            if rate >= 30.0:
                # 3. Gui thong bao WebSocket toi bang dieu hanh van hanh (Dual-broadcast for migration)
                channel_layer = get_channel_layer()
                if channel_layer:
                    for group in OPERATIONS_NOTIFICATION_GROUPS:
                        async_to_sync(channel_layer.group_send)(
                            group,
                            {
                                "type": "operational.alert",
                                "payload": {
                                    "title": "Cảnh báo Độ ổn định nhân sự",
                                    "message": f"Mục tiêu '{mt.ten_muc_tieu}' có tỷ lệ đổi ca cao bất thường ({rate}%).",
                                    "target_id": mt.id,
                                    "swap_rate": rate,
                                    "severity": "CRITICAL" if rate > 50 else "WARNING"
                                }
                            }
                        )
=======
        muc_tieus = MucTieu.objects.all()
        alerts_triggered = 0

        for mt in muc_tieus:
            total_planned = PhanCongCaTruc.objects.filter(
                vi_tri_chot__muc_tieu=mt,
                ngay_truc__range=[start_date, today],
                tenant_id=tenant_id
            ).count()

            swaps_approved = BaoCaoDeXuat.objects.filter(
                ca_truc__vi_tri_chot__muc_tieu=mt,
                loai_de_xuat='DOI_CA',
                trang_thai='DA_XU_LY',
                ca_truc__ngay_truc__range=[start_date, today],
                tenant_id=tenant_id
            ).count()

            rate = calculate_swap_rate(swaps_approved, total_planned)

            # 2. Kiểm tra ngưỡng (Threshold: 30%)
            if rate >= 30.0:
                # 3. Gửi thông báo WebSocket tới War Room
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "war_room_staff",
                    {
                        "type": "operational.alert",
                        "payload": {
                            "title": "Cảnh báo Độ ổn định nhân sự",
                            "message": f"Mục tiêu '{mt.ten_muc_tieu}' có tỷ lệ đổi ca cao bất thường ({rate}%).",
                            "target_id": mt.id,
                            "swap_rate": rate,
                            "severity": "CRITICAL" if rate > 50 else "WARNING"
                        }
                    }
                )
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                logger.warning(f"[Stability Alert] Target: {mt.ten_muc_tieu} - Rate: {rate}%")
                alerts_triggered += 1

        return alerts_triggered
