# -*- coding: utf-8 -*-
"""
Application Layer: Dashboard use cases.

Contract:
- Interface layer imports use cases from this module.
- Organization scope must be enforced before dashboard aggregation.
- The official dashboard use-case name is `GetOperationsDashboardUseCase`.
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.utils import timezone
from django.db.models import Count, Q
from rolepermissions.checkers import has_role

from clients.access_policies import SiteVisibilityPolicy
from clients.models import MucTieu
from operations.models import BaoCaoSuCo, ChamCong, PhanCongCaTruc
from operations.application.shift_change_use_cases import LeaveScheduleConflictUseCase
from operations.application.guard_patrol_use_cases import GuardPatrolComplianceUseCase

logger = logging.getLogger(__name__)


MAX_ACTIVE_MARKERS = 300
MAX_INCIDENT_MARKERS = 100
MAX_RECENT_ACTIVITY = 20
MAX_LEAVE_CONFLICTS = 50
MAX_SCOPE_IDS_FOR_IN_FILTER = 2000


@dataclass(frozen=True)
class TargetScope:
    """Resolved target scope for dashboard queries.

    Small scopes use an id list to avoid repeating expensive parent queryset
    subqueries. Large scopes keep the queryset/subquery to avoid huge IN lists.
    """

    queryset: object
    target_ids: tuple[int, ...] | None
    count: int


class GetOperationsDashboardUseCase:
    """Permission-aware dashboard aggregation for the operations cockpit."""

    @staticmethod
    def _truncate_text(value, limit=160):
        if not value:
            return ""
        normalized = " ".join(str(value).split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[: limit - 1].rstrip()}…"

    @staticmethod
    def _safe_localtime(value):
        if not isinstance(value, datetime):
            return None
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        return timezone.localtime(value)

    @staticmethod
    def _day_bounds(target_date):
        """Return timezone-aware [start, end) bounds for the operations day."""

        current_tz = timezone.get_current_timezone()
        if isinstance(target_date, datetime):
            start_at = target_date
            if timezone.is_naive(start_at):
                start_at = timezone.make_aware(start_at, current_tz)
            start_at = timezone.localtime(start_at, current_tz).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            start_at = timezone.make_aware(datetime.combine(target_date, time.min), current_tz)
        return start_at, start_at + timedelta(days=1)

    @staticmethod
    def _coerce_coordinate(value, *, minimum, maximum):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(numeric) or numeric < minimum or numeric > maximum:
            return None
        return numeric

    @staticmethod
    def _valid_lat_lng(lat_value, lng_value):
        lat = GetOperationsDashboardUseCase._coerce_coordinate(lat_value, minimum=-90, maximum=90)
        lng = GetOperationsDashboardUseCase._coerce_coordinate(lng_value, minimum=-180, maximum=180)
        if lat is None or lng is None:
            return None
        return lat, lng

    @staticmethod
    def _is_technical_admin(user):
        return bool(getattr(user, "is_superuser", False) or getattr(user, "is_staff", False))

    @staticmethod
    def _get_allowed_targets_queryset(user, tenant_id):
        if GetOperationsDashboardUseCase._is_technical_admin(user):
            return MucTieu.objects.for_tenant(tenant_id)

        if not hasattr(user, "nhan_vien"):
            return MucTieu.objects.none()

        muc_tieu_qs = MucTieu.objects.for_tenant(tenant_id)

        if has_role(user, "ban_giam_doc") or has_role(user, "ke_toan"):
            return muc_tieu_qs
        if has_role(user, "quan_ly_vung") or has_role(user, "doi_truong"):
            return SiteVisibilityPolicy.managed_sites(user)
        return MucTieu.objects.none()

    @staticmethod
    def _resolve_target_scope(target_scope_qs):
        try:
            scoped_ids = list(
                target_scope_qs.order_by("id").values_list("id", flat=True)[: MAX_SCOPE_IDS_FOR_IN_FILTER + 1]
            )
        except Exception:
            # Defensive fallback for non-standard querysets/mocks; production ORM
            # querysets follow the optimized path above.
            return TargetScope(queryset=target_scope_qs, target_ids=None, count=target_scope_qs.count())

        if len(scoped_ids) <= MAX_SCOPE_IDS_FOR_IN_FILTER:
            return TargetScope(
                queryset=target_scope_qs,
                target_ids=tuple(scoped_ids),
                count=len(scoped_ids),
            )
        return TargetScope(queryset=target_scope_qs, target_ids=None, count=target_scope_qs.count())

    @staticmethod
    def _filter_by_target_scope(qs, scope, *, relation_path):
        """Apply target scope to a queryset using ids for small scopes."""

        if scope.target_ids is not None:
            return qs.filter(**{f"{relation_path}_id__in": scope.target_ids})
        return qs.filter(**{f"{relation_path}__in": scope.queryset})

    @staticmethod
    def _append_event(event_stream, event):
        """Collect events before global merge/sort.

        Do not cap here: check-in and incident streams are merged first, sorted by
        timestamp, and only then trimmed to MAX_RECENT_ACTIVITY. Early capping can
        hide newer incidents when the check-in loop fills the buffer first.
        """

        event_stream.append(event)

    @staticmethod
    def execute(user, tenant_id, target_date, muc_tieu_id=None):
        technical_admin_mode = GetOperationsDashboardUseCase._is_technical_admin(user)
        if not technical_admin_mode and not hasattr(user, "nhan_vien"):
            return {}

        start_at, end_at = GetOperationsDashboardUseCase._day_bounds(target_date)
        allowed_targets_qs = GetOperationsDashboardUseCase._get_allowed_targets_queryset(
            user=user,
            tenant_id=tenant_id,
        )

        target_scope_qs = allowed_targets_qs
        if muc_tieu_id:
            try:
                requested_id = int(muc_tieu_id)
            except (ValueError, TypeError):
                requested_id = None

            if requested_id is not None:
                requested_target_qs = allowed_targets_qs.filter(id=requested_id)
                if requested_target_qs.exists():
                    target_scope_qs = requested_target_qs
                else:
                    logger.warning(
                        "SECURITY: user %s attempted to access unauthorized site %s",
                        user.id,
                        requested_id,
                    )
                    return {"error": "Unauthorized site access"}

        scope = GetOperationsDashboardUseCase._resolve_target_scope(target_scope_qs)

        active_ccs_base_qs = ChamCong.objects.for_tenant(tenant_id).filter(
            thoi_gian_check_in__gte=start_at,
            thoi_gian_check_in__lt=end_at,
            thoi_gian_check_out__isnull=True,
        )
        active_ccs_base_qs = GetOperationsDashboardUseCase._filter_by_target_scope(
            active_ccs_base_qs,
            scope,
            relation_path="ca_truc__vi_tri_chot__muc_tieu",
        )

        active_count = active_ccs_base_qs.count()
        active_ccs_qs = active_ccs_base_qs.filter(location_check_in__isnull=False).select_related(
            "ca_truc__nhan_vien",
            "ca_truc__vi_tri_chot",
            "ca_truc__vi_tri_chot__muc_tieu",
            "ca_truc__ca_lam_viec",
        ).only(
            "thoi_gian_check_in",
            "location_check_in",
            "ca_truc__nhan_vien__id",
            "ca_truc__nhan_vien__ho_ten",
            "ca_truc__nhan_vien__ma_nhan_vien",
            "ca_truc__nhan_vien__sdt_chinh",
            "ca_truc__vi_tri_chot__ten_vi_tri",
            "ca_truc__vi_tri_chot__muc_tieu__ten_muc_tieu",
            "ca_truc__vi_tri_chot__muc_tieu__nguoi_lien_he",
            "ca_truc__vi_tri_chot__muc_tieu__sdt_lien_he",
            "ca_truc__ca_lam_viec__ten_ca",
            "ca_truc__ca_lam_viec__gio_bat_dau",
            "ca_truc__ca_lam_viec__gio_ket_thuc",
        ).order_by("-thoi_gian_check_in")[:MAX_ACTIVE_MARKERS]

        total_shifts_qs = PhanCongCaTruc.objects.for_tenant(tenant_id).filter(
            ngay_truc=target_date,
        )
        total_shifts_qs = GetOperationsDashboardUseCase._filter_by_target_scope(
            total_shifts_qs,
            scope,
            relation_path="vi_tri_chot__muc_tieu",
        )
        total_shifts = total_shifts_qs.count()

        incidents_base_qs = BaoCaoSuCo.objects.for_tenant(tenant_id).filter(
            trang_thai__in=["CHO_XU_LY", "DANG_XU_LY", "CHO_DEN_BU"],
        )
        incidents_base_qs = GetOperationsDashboardUseCase._filter_by_target_scope(
            incidents_base_qs,
            scope,
            relation_path="muc_tieu",
        )
        incident_stats = incidents_base_qs.aggregate(
            total=Count("id"),
            severe=Count("id", filter=Q(muc_do__in=["CAO", "NGUY_HIEM"])),
        )
        incident_count = incident_stats["total"] or 0
        severe_incident_count = incident_stats["severe"] or 0
        incidents_qs = incidents_base_qs.filter(
            muc_tieu__vi_do__isnull=False,
            muc_tieu__kinh_do__isnull=False,
        ).select_related("muc_tieu", "nhan_vien_bao_cao", "nguoi_xu_ly").only(
            "id",
            "ma_su_co",
            "tieu_de",
            "muc_do",
            "trang_thai",
            "created_at",
            "mo_ta_chi_tiet",
            "muc_tieu__ten_muc_tieu",
            "muc_tieu__vi_do",
            "muc_tieu__kinh_do",
            "nhan_vien_bao_cao__ho_ten",
            "nhan_vien_bao_cao__sdt_chinh",
            "nguoi_xu_ly__ho_ten",
        ).order_by("-created_at")[:MAX_INCIDENT_MARKERS]

        checkin_rate = int((active_count / total_shifts) * 100) if total_shifts > 0 else 0

        markers_data = []
        event_stream = []
        skipped_invalid_coordinates = 0

        for cc in active_ccs_qs:
            point = cc.location_check_in
            coords = GetOperationsDashboardUseCase._valid_lat_lng(
                getattr(point, "y", None),
                getattr(point, "x", None),
            )
            if not coords:
                skipped_invalid_coordinates += 1
                continue
            lat, lng = coords

            check_in_at = GetOperationsDashboardUseCase._safe_localtime(cc.thoi_gian_check_in)
            check_in_time = check_in_at.strftime("%H:%M") if check_in_at else "--:--"
            ca_truc = cc.ca_truc
            nhan_vien = ca_truc.nhan_vien
            vi_tri_chot = ca_truc.vi_tri_chot
            muc_tieu = vi_tri_chot.muc_tieu
            ca_lam_viec = ca_truc.ca_lam_viec

            markers_data.append(
                {
                    "id": nhan_vien.id,
                    "name": nhan_vien.ho_ten,
                    "employee_code": nhan_vien.ma_nhan_vien,
                    "phone": nhan_vien.sdt_chinh or "",
                    "avatar": getattr(nhan_vien, "avatar_url", "/static/img/default_avatar.png"),
                    "lat": lat,
                    "lng": lng,
                    "target": muc_tieu.ten_muc_tieu,
                    "target_contact": getattr(muc_tieu, "nguoi_lien_he", "") or "",
                    "target_contact_phone": getattr(muc_tieu, "sdt_lien_he", "") or "",
                    "post_name": vi_tri_chot.ten_vi_tri,
                    "shift_name": getattr(ca_lam_viec, "ten_ca", ""),
                    "shift_window": (
                        f"{ca_lam_viec.gio_bat_dau:%H:%M} - {ca_lam_viec.gio_ket_thuc:%H:%M}"
                        if ca_lam_viec and ca_lam_viec.gio_bat_dau and ca_lam_viec.gio_ket_thuc
                        else ""
                    ),
                    "status": "active",
                    "check_in_time": check_in_time,
                }
            )
            if check_in_at:
                GetOperationsDashboardUseCase._append_event(
                    event_stream,
                    {
                        "kind": "checkin",
                        "label": "Check-in mới",
                        "user": nhan_vien.ho_ten,
                        "time": check_in_time,
                        "timestamp": check_in_at.isoformat(),
                        "target": muc_tieu.ten_muc_tieu,
                        "lat": lat,
                        "lng": lng,
                        "summary": f"{nhan_vien.ho_ten} vừa check-in tại {muc_tieu.ten_muc_tieu}.",
                        "post_name": vi_tri_chot.ten_vi_tri,
                    },
                )

        incidents_data = []
        for incident in incidents_qs:
            if not incident.muc_tieu:
                skipped_invalid_coordinates += 1
                continue
            coords = GetOperationsDashboardUseCase._valid_lat_lng(
                incident.muc_tieu.vi_do,
                incident.muc_tieu.kinh_do,
            )
            if not coords:
                skipped_invalid_coordinates += 1
                continue
            lat, lng = coords

            created_at = GetOperationsDashboardUseCase._safe_localtime(
                getattr(incident, "created_at", None)
            )
            incidents_data.append(
                {
                    "id": incident.id,
                    "code": incident.ma_su_co,
                    "title": incident.tieu_de,
                    "level": incident.muc_do,
                    "level_label": incident.get_muc_do_display(),
                    "status": incident.trang_thai,
                    "status_label": incident.get_trang_thai_display(),
                    "lat": lat,
                    "lng": lng,
                    "muc_tieu": incident.muc_tieu.ten_muc_tieu,
                    "thoi_gian": created_at.strftime("%H:%M") if created_at else "--:--",
                    "nguoi_bao_cao": getattr(incident.nhan_vien_bao_cao, "ho_ten", "Chưa xác định"),
                    "so_dien_thoai": getattr(incident.nhan_vien_bao_cao, "sdt_chinh", "") or "",
                    "nguoi_xu_ly": getattr(incident.nguoi_xu_ly, "ho_ten", "") or "",
                    "mo_ta_ngan": GetOperationsDashboardUseCase._truncate_text(
                        incident.mo_ta_chi_tiet,
                        limit=180,
                    ),
                }
            )
            if created_at:
                GetOperationsDashboardUseCase._append_event(
                    event_stream,
                    {
                        "kind": "incident",
                        "label": "Sự cố mới",
                        "user": getattr(incident.nhan_vien_bao_cao, "ho_ten", "Chưa xác định"),
                        "time": created_at.strftime("%H:%M"),
                        "timestamp": created_at.isoformat(),
                        "target": incident.muc_tieu.ten_muc_tieu,
                        "lat": lat,
                        "lng": lng,
                        "summary": f"{incident.tieu_de} tại {incident.muc_tieu.ten_muc_tieu}.",
                        "incident_id": incident.id,
                        "incident_code": incident.ma_su_co,
                        "incident_level": incident.muc_do,
                    },
                )

        event_stream.sort(key=lambda item: item["timestamp"], reverse=True)
        recent_activity = event_stream[:MAX_RECENT_ACTIVITY]

        last_activity = None
        if recent_activity:
            latest_event = recent_activity[0]
            last_activity = {
                "kind": latest_event["kind"],
                "label": latest_event["label"],
                "user": latest_event["user"],
                "time": latest_event["time"],
                "target": latest_event["target"],
                "summary": latest_event["summary"],
                "lat": latest_event["lat"],
                "lng": latest_event["lng"],
            }

        leave_conflicts = LeaveScheduleConflictUseCase.execute(
            tenant_id=tenant_id,
            target_date=target_date,
            target_scope_qs=target_scope_qs,
            max_results=MAX_LEAVE_CONFLICTS,
        )
        guard_patrol_compliance = GuardPatrolComplianceUseCase.execute(
            tenant_id=tenant_id,
            target_date=target_date,
            target_scope_qs=target_scope_qs,
        )

        return {
            "stats": {
                "tong_ca": total_shifts,
                "da_checkin": active_count,
                "vang_mat": total_shifts - active_count,
                "tong_muc_tieu": scope.count,
                "tong_su_co": incident_count,
                "su_co_nghiem_trong": severe_incident_count,
                "ti_le_phu_ca": checkin_rate,
                "leave_schedule_conflicts": len(leave_conflicts),
                "guard_patrol_total": guard_patrol_compliance["stats"]["total"],
                "guard_patrol_in_progress": guard_patrol_compliance["stats"]["in_progress"],
                "guard_patrol_completed_valid": guard_patrol_compliance["stats"]["completed_valid"],
                "guard_patrol_completed_with_warnings": guard_patrol_compliance["stats"]["completed_with_warnings"],
                "guard_patrol_missed": guard_patrol_compliance["stats"]["missed"],
            },
            "leave_schedule_conflicts": leave_conflicts,
            "guard_patrol_compliance": guard_patrol_compliance,
            "markers": markers_data,
            "incidents": incidents_data,
            "last_activity": last_activity,
            "recent_activity": recent_activity,
            "diagnostics": {
                "caps": {
                    "active_markers": MAX_ACTIVE_MARKERS,
                    "incident_markers": MAX_INCIDENT_MARKERS,
                    "recent_activity": MAX_RECENT_ACTIVITY,
                },
                "skipped_invalid_coordinates": skipped_invalid_coordinates,
            },
            "diagnostic_mode": technical_admin_mode and not hasattr(user, "nhan_vien"),
        }
