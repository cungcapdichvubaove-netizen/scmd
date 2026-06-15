# -*- coding: utf-8 -*-
"""Application layer for guard patrol operations.

Domain decision:
- Guard Patrol / tuần tra bảo vệ tại mục tiêu is owned by operations.
- The legacy persistence tables still live in ``inspection`` during the
  transition phase to avoid unsafe app-label/table migrations.
- ``inspection.application.patrol_use_cases`` must remain a compatibility
  wrapper only; canonical business orchestration lives here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.domain.geo import GeofenceEvaluator
from inspection.models import DiemTuanTra, GhiNhanTuanTra, LoaiTuanTra, LuotTuanTra
from main.models import AuditLog
from operations.models import ChamCong, LichTuanTraVanHanh, NhiemVuTuanTraCa, PhanCongCaTruc

MAX_GUARD_PATROL_TASKS = 50
MAX_COMPLIANCE_ITEMS = 50
MAX_PATROL_SCHEDULES_PER_SHIFT = 20
MAX_SHIFTS_TO_MATERIALIZE_PATROL_TASKS = 300
MAX_TASKS_TO_MARK_MISSED = 500
GUARD_PATROL_SHIFT_WINDOW_GRACE_MINUTES = 30
SYSTEM_MATERIALIZATION_REASON = "SYSTEM_MATERIALIZATION_JOB"
SYSTEM_MARK_MISSED_REASON = "SYSTEM_MARK_MISSED_JOB"


@dataclass(frozen=True)
class GuardPatrolShiftContext:
    """Shift context used to prove patrol ownership for scheduled guard patrol."""

    shift: PhanCongCaTruc

    @property
    def site_id(self):
        return self.shift.vi_tri_chot.muc_tieu_id if self.shift and self.shift.vi_tri_chot_id else None


def _organization_id():
    return settings.SCMD_ORGANIZATION_ID


def _has_gps_coordinates(lat, lng):
    missing_values = (None, "", "null")
    return lat not in missing_values and lng not in missing_values


def _require_employee(nhan_vien):
    if not nhan_vien:
        raise PermissionDenied("Không tìm thấy hồ sơ nhân viên hợp lệ.")
    return nhan_vien


def _active_day_bounds(target_date=None):
    target_date = target_date or timezone.localdate()
    current_tz = timezone.get_current_timezone()
    start_at = timezone.make_aware(datetime.combine(target_date, time.min), current_tz)
    return start_at, start_at + timedelta(days=1)


def _candidate_shift_queryset(nhan_vien, *, at=None):
    """Return guard shifts that can overlap ``at``, including cross-midnight shifts.

    We intentionally include yesterday because night shifts can start on the
    previous date and continue into the current business day. The final current
    shift selection is done with timezone-aware datetime windows, not by taking
    the first assignment for a calendar date.
    """

    at = at or timezone.now()
    local_date = timezone.localtime(at).date()
    candidate_dates = [local_date, local_date - timedelta(days=1)]
    return (
        PhanCongCaTruc.objects.for_tenant(_organization_id())
        .filter(nhan_vien=nhan_vien, ngay_truc__in=candidate_dates)
        .select_related("vi_tri_chot", "vi_tri_chot__muc_tieu", "ca_lam_viec", "chamcong")
        .order_by("ngay_truc", "ca_lam_viec__gio_bat_dau", "id")
    )


def _aware_datetime(raw_dt):
    if raw_dt is None:
        return None
    if timezone.is_aware(raw_dt):
        return raw_dt
    return timezone.make_aware(raw_dt, timezone.get_current_timezone())


def _shift_window(shift, *, grace_minutes=None):
    if not shift:
        return None, None
    start_at = _aware_datetime(shift.get_thoi_gian_bat_dau_thuc_te())
    end_at = _aware_datetime(shift.get_thoi_gian_ket_thuc_thuc_te())
    if start_at and end_at and end_at <= start_at:
        end_at = end_at + timedelta(days=1)
    grace_minutes = GUARD_PATROL_SHIFT_WINDOW_GRACE_MINUTES if grace_minutes is None else grace_minutes
    if start_at:
        start_at = start_at - timedelta(minutes=grace_minutes)
    if end_at:
        end_at = end_at + timedelta(minutes=grace_minutes)
    return start_at, end_at


def _is_shift_checked_in(shift):
    try:
        attendance = shift.chamcong
    except ChamCong.DoesNotExist:
        return False
    return bool(attendance.thoi_gian_check_in and not attendance.thoi_gian_check_out)


def _require_audit_actor_context(*, actor=None, system_actor_label=None, reason=None):
    if actor is not None:
        return {
            "user": actor if getattr(actor, "is_authenticated", False) else None,
            "actor_type": "user",
            "actor_label": (
                actor.get_username()
                if hasattr(actor, "get_username")
                else getattr(actor, "username", None) or str(actor)
            ),
            "reason": reason or "USER_TRIGGERED",
        }
    if system_actor_label:
        return {
            "user": None,
            "actor_type": "system",
            "actor_label": system_actor_label,
            "reason": reason or "SYSTEM_TRIGGERED",
        }
    raise ValidationError("Materialize/MISSED job phải có actor hoặc system_actor_label để audit.")


def _current_shift_contexts(nhan_vien, *, at=None, route=None):
    """Select current shift(s) by time window and attendance state.

    Multiple shifts in a day are common. This helper never picks an arbitrary
    ``.first()`` assignment for the day; it filters by the active time window,
    supports cross-midnight shifts, and prioritizes checked-in shifts.
    """

    at = at or timezone.now()
    contexts = []
    for shift in _candidate_shift_queryset(nhan_vien, at=at):
        if route and route.muc_tieu_id and (not shift.vi_tri_chot_id or shift.vi_tri_chot.muc_tieu_id != route.muc_tieu_id):
            continue
        start_at, end_at = _shift_window(shift)
        if start_at and end_at and start_at <= at <= end_at:
            contexts.append(GuardPatrolShiftContext(shift=shift))

    def _sort_key(context):
        shift = context.shift
        checked_rank = 0 if _is_shift_checked_in(shift) else 1
        start_at, _ = _shift_window(shift)
        distance = abs((at - start_at).total_seconds()) if start_at else 0
        return (checked_rank, distance, shift.ngay_truc, shift.pk)

    return sorted(contexts, key=_sort_key)


def _current_shift_context(nhan_vien, *, at=None, route=None):
    contexts = _current_shift_contexts(nhan_vien, at=at, route=route)
    return contexts[0] if contexts else None

def _guard_shift_for_route(nhan_vien, loai_tuan_tra):
    """Return the current assigned shift that authorizes this guard route."""

    return _current_shift_context(nhan_vien, route=loai_tuan_tra)

def _task_queryset():
    return NhiemVuTuanTraCa.objects.for_tenant(_organization_id())


def _schedule_queryset():
    return LichTuanTraVanHanh.objects.for_tenant(_organization_id())


def _datetime_on_shift_date(shift, raw_time):
    if not shift or raw_time is None:
        return None
    current_tz = timezone.get_current_timezone()
    return timezone.make_aware(datetime.combine(shift.ngay_truc, raw_time), current_tz)


def _matching_schedules_for_shift(shift):
    if not shift or not shift.vi_tri_chot_id:
        return LichTuanTraVanHanh.objects.none()
    return (
        _schedule_queryset()
        .filter(
            trang_thai=LichTuanTraVanHanh.TrangThai.ACTIVE,
            muc_tieu_id=shift.vi_tri_chot.muc_tieu_id,
        )
        .filter(Q(vi_tri_chot__isnull=True) | Q(vi_tri_chot=shift.vi_tri_chot))
        .filter(Q(ca_lam_viec__isnull=True) | Q(ca_lam_viec=shift.ca_lam_viec))
        .select_related("muc_tieu", "vi_tri_chot", "ca_lam_viec", "tuyen_tuan_tra")
        .order_by("vi_tri_chot_id", "ca_lam_viec_id", "tuyen_tuan_tra__ten_loai")[:MAX_PATROL_SCHEDULES_PER_SHIFT]
    )



def _active_schedules_exist_for_shift(shift):
    return bool(list(_matching_schedules_for_shift(shift)[:1]))


class MaterializeGuardPatrolTasksUseCase:
    """Explicit command boundary for creating scheduled guard patrol tasks."""

    @staticmethod
    def execute_for_shift(*, shift, actor=None, system_actor_label=None):
        if not shift:
            return []
        audit_context = _require_audit_actor_context(
            actor=actor,
            system_actor_label=system_actor_label,
            reason=SYSTEM_MATERIALIZATION_REASON if system_actor_label else "USER_CURRENT_SHIFT_MATERIALIZATION",
        )
        return _ensure_shift_patrol_tasks(shift, audit_context=audit_context, audit=True)

    @staticmethod
    def execute_for_date(*, target_date=None, actor=None, system_actor_label=None):
        target_date = target_date or timezone.localdate()
        audit_context = _require_audit_actor_context(
            actor=actor,
            system_actor_label=system_actor_label,
            reason=SYSTEM_MATERIALIZATION_REASON if system_actor_label else "USER_TRIGGERED",
        )
        shifts = (
            PhanCongCaTruc.objects.for_tenant(_organization_id())
            .filter(ngay_truc=target_date)
            .select_related("vi_tri_chot", "vi_tri_chot__muc_tieu", "ca_lam_viec", "nhan_vien")
            .order_by("ngay_truc", "ca_lam_viec__gio_bat_dau", "id")[:MAX_SHIFTS_TO_MATERIALIZE_PATROL_TASKS]
        )

        eligible_shift_count = 0
        created_task_count = 0
        touched_task_count = 0
        for shift in shifts:
            if not _active_schedules_exist_for_shift(shift):
                continue
            eligible_shift_count += 1
            before_ids = set(_task_queryset().filter(phan_cong_ca_truc=shift).values_list("id", flat=True))
            tasks = _ensure_shift_patrol_tasks(shift, audit_context=audit_context, audit=True)
            touched_task_count += len(tasks)
            created_task_count += len({task.pk for task in tasks} - before_ids)

        _audit(
            user=audit_context["user"],
            action=AuditLog.Action.EXECUTE,
            model_name="GuardPatrolMaterializationJob",
            note=f"Materialize nhiệm vụ tuần tra cho ngày {target_date:%d/%m/%Y}.",
            changes={
                "domain_owner": "operations.guard_patrol",
                "actor_type": audit_context["actor_type"],
                "actor_label": audit_context["actor_label"],
                "reason": audit_context["reason"],
                "target_date": target_date.isoformat(),
                "eligible_shift_count": eligible_shift_count,
                "created_task_count": created_task_count,
                "touched_task_count": touched_task_count,
            },
        )
        return {
            "target_date": target_date,
            "eligible_shift_count": eligible_shift_count,
            "created_task_count": created_task_count,
            "touched_task_count": touched_task_count,
        }


def _ensure_shift_patrol_tasks(shift, *, audit_context, audit=True):
    """Materialize planned patrol tasks for a shift from active schedules.

    This is intentionally idempotent and capped. It lets operations create a
    schedule once, while guards only see concrete tasks assigned to their shift.
    Read-only dashboard paths must not call this helper.
    """

    if not shift:
        return []

    tasks = []
    with transaction.atomic():
        for schedule in _matching_schedules_for_shift(shift):
            required_count = _checkpoint_queryset().filter(loai_tuan_tra=schedule.tuyen_tuan_tra).count()
            start_expected = _datetime_on_shift_date(shift, schedule.khung_gio_bat_dau)
            end_expected = _datetime_on_shift_date(shift, schedule.khung_gio_ket_thuc)
            if start_expected and end_expected and end_expected <= start_expected:
                end_expected = end_expected + timedelta(days=1)
            grace_base = end_expected or start_expected
            grace_deadline = grace_base + timedelta(minutes=schedule.grace_minutes) if grace_base else None

            for order in range(1, schedule.tan_suat_luot_bat_buoc + 1):
                task, created = _task_queryset().get_or_create(
                    lich_tuan_tra=schedule,
                    phan_cong_ca_truc=shift,
                    thu_tu_luot=order,
                    defaults={
                        "tuyen_tuan_tra": schedule.tuyen_tuan_tra,
                        "trang_thai": NhiemVuTuanTraCa.TrangThai.PLANNED,
                        "thoi_gian_bat_dau_du_kien": start_expected,
                        "thoi_gian_ket_thuc_du_kien": end_expected,
                        "grace_deadline": grace_deadline,
                        "so_diem_bat_buoc": required_count,
                        "tenant_id": _organization_id(),
                    },
                )
                update_fields = []
                if task.tuyen_tuan_tra_id != schedule.tuyen_tuan_tra_id:
                    task.tuyen_tuan_tra = schedule.tuyen_tuan_tra
                    update_fields.append("tuyen_tuan_tra")
                if task.so_diem_bat_buoc != required_count:
                    task.so_diem_bat_buoc = required_count
                    update_fields.append("so_diem_bat_buoc")
                if task.thoi_gian_bat_dau_du_kien != start_expected:
                    task.thoi_gian_bat_dau_du_kien = start_expected
                    update_fields.append("thoi_gian_bat_dau_du_kien")
                if task.thoi_gian_ket_thuc_du_kien != end_expected:
                    task.thoi_gian_ket_thuc_du_kien = end_expected
                    update_fields.append("thoi_gian_ket_thuc_du_kien")
                if task.grace_deadline != grace_deadline:
                    task.grace_deadline = grace_deadline
                    update_fields.append("grace_deadline")
                if update_fields:
                    update_fields.append("updated_at")
                    task.save(update_fields=update_fields)
                tasks.append(task)
                if created and audit:
                    _audit(
                        user=audit_context["user"],
                        action=AuditLog.Action.CREATE,
                        model_name="NhiemVuTuanTraCa",
                        object_id=task.pk,
                        note="Tự động tạo nhiệm vụ tuần tra theo lịch vận hành.",
                        changes={
                            "domain_owner": "operations.guard_patrol",
                            "actor_type": audit_context["actor_type"],
                            "actor_label": audit_context["actor_label"],
                            "reason": audit_context["reason"],
                            "lich_tuan_tra_id": schedule.pk,
                            "phan_cong_ca_truc_id": shift.pk,
                            "tuyen_tuan_tra_id": schedule.tuyen_tuan_tra_id,
                            "thu_tu_luot": order,
                        },
                    )
    return tasks


def _task_for_guard_selection(nhan_vien, selected_id, *, at=None):
    """Resolve selected mobile id as a scheduled task for the current shift only."""

    current_shift_ids = [ctx.shift.pk for ctx in _current_shift_contexts(nhan_vien, at=at)]
    if not current_shift_ids:
        return None
    return (
        _task_queryset()
        .select_related(
            "lich_tuan_tra",
            "tuyen_tuan_tra",
            "phan_cong_ca_truc",
            "phan_cong_ca_truc__vi_tri_chot",
            "phan_cong_ca_truc__vi_tri_chot__muc_tieu",
            "phan_cong_ca_truc__ca_lam_viec",
        )
        .filter(
            pk=selected_id,
            phan_cong_ca_truc_id__in=current_shift_ids,
            phan_cong_ca_truc__nhan_vien=nhan_vien,
            trang_thai__in=[
                NhiemVuTuanTraCa.TrangThai.PLANNED,
                NhiemVuTuanTraCa.TrangThai.IN_PROGRESS,
            ],
        )
        .order_by("phan_cong_ca_truc__ngay_truc", "phan_cong_ca_truc__ca_lam_viec__gio_bat_dau", "id")
        .first()
    )

def _patrol_queryset():
    return LuotTuanTra.objects.for_tenant(_organization_id())


def _checkpoint_queryset():
    return DiemTuanTra.objects.for_tenant(_organization_id())


def _route_queryset():
    return LoaiTuanTra.objects.for_tenant(_organization_id())


def _evidence_queryset():
    return GhiNhanTuanTra.objects.for_tenant(_organization_id())


def _audit(*, user, action, model_name, object_id=None, note="", changes=None):
    AuditLog.objects.create(
        user=user,
        action=action,
        module="operations",
        model_name=model_name,
        object_id=str(object_id) if object_id is not None else "",
        tenant_id=_organization_id(),
        note=note,
        changes=changes or {},
    )


class ListGuardPatrolTasksUseCase:
    """List concrete guard patrol tasks for the authenticated guard's current shift."""

    @staticmethod
    def execute(nhan_vien, *, actor=None, at=None):
        nhan_vien = _require_employee(nhan_vien)
        current_contexts = _current_shift_contexts(nhan_vien, at=at)
        shift = current_contexts[0].shift if current_contexts else None
        tasks = []
        fallback_routes = LoaiTuanTra.objects.none()
        schedule_configured = False

        if shift and shift.vi_tri_chot_id and shift.vi_tri_chot.muc_tieu_id:
            schedule_configured = _active_schedules_exist_for_shift(shift)
            if schedule_configured:
                # Controlled mobile materialization: only for the authenticated
                # guard's current shift, idempotent, and actor-bound. Dashboard
                # summary never calls this path.
                MaterializeGuardPatrolTasksUseCase.execute_for_shift(shift=shift, actor=actor)
                tasks = list(
                    _task_queryset()
                    .filter(phan_cong_ca_truc=shift)
                    .select_related("lich_tuan_tra", "tuyen_tuan_tra", "tuyen_tuan_tra__muc_tieu", "phan_cong_ca_truc", "phan_cong_ca_truc__ca_lam_viec", "phan_cong_ca_truc__vi_tri_chot")
                    .prefetch_related("tuyen_tuan_tra__cac_diem")
                    .order_by("thu_tu_luot", "thoi_gian_bat_dau_du_kien", "id")[:MAX_GUARD_PATROL_TASKS]
                )
            else:
                fallback_routes = (
                    _route_queryset()
                    .filter(muc_tieu_id=shift.vi_tri_chot.muc_tieu_id)
                    .prefetch_related("cac_diem")
                    .order_by("ten_loai")[:MAX_GUARD_PATROL_TASKS]
                )

        active_session = (
            _patrol_queryset()
            .filter(nhan_vien=nhan_vien, trang_thai="DANG_DI")
            .select_related(
                "loai_tuan_tra",
                "loai_tuan_tra__muc_tieu",
                "phan_cong_ca_truc",
                "lich_tuan_tra_van_hanh",
                "nhiem_vu_tuan_tra_ca",
            )
            .first()
        )
        return {
            "ca_hien_tai": shift,
            "cac_ca_hien_tai": [ctx.shift for ctx in current_contexts],
            "nhiem_vu_tuan_tra": tasks,
            "lo_trinhs": list(fallback_routes),  # legacy template compatibility only
            "luot_dang_di": active_session,
            "uses_operations_schedule": schedule_configured,
            "legacy_fallback_allowed": bool(not schedule_configured and fallback_routes),
        }


class StartGuardPatrolSessionUseCase:
    """Start or resume a guard patrol session from an operations scheduled task."""

    @staticmethod
    def execute(nhan_vien, loai_id):
        nhan_vien = _require_employee(nhan_vien)
        task = _task_for_guard_selection(nhan_vien, loai_id)
        if task:
            loai = task.tuyen_tuan_tra
            shift_context = GuardPatrolShiftContext(shift=task.phan_cong_ca_truc)
        else:
            # Legacy transition: route id is allowed only when Operations has no
            # active schedule for the current shift. If a schedule exists and all
            # tasks are completed/missed/warning, fallback must stay locked.
            loai = get_object_or_404(_route_queryset(), id=loai_id)
            shift_context = _guard_shift_for_route(nhan_vien, loai)
            if not shift_context:
                raise PermissionDenied("Bạn không có ca trực hợp lệ trong khung giờ hiện tại cho tuyến tuần tra này.")
            if _active_schedules_exist_for_shift(shift_context.shift):
                raise ValidationError("Ca trực này đã có lịch tuần tra vận hành. Không thể bắt đầu tuyến legacy ngoài kế hoạch.")

        required_photo = bool(getattr(task.lich_tuan_tra, "yeu_cau_anh", False)) if task else bool(getattr(settings, "GUARD_PATROL_REQUIRE_PHOTO", False))
        required_gps = bool(getattr(task.lich_tuan_tra, "yeu_cau_gps", False)) if task else bool(getattr(loai, "yeu_cau_gps", False))

        with transaction.atomic():
            luot = (
                _patrol_queryset()
                .select_for_update()
                .filter(nhan_vien=nhan_vien, trang_thai="DANG_DI")
                .select_related("loai_tuan_tra", "nhiem_vu_tuan_tra_ca")
                .first()
            )
            created = False

            if luot and luot.loai_tuan_tra_id != loai.id:
                raise ValidationError(
                    "Bạn đang có lượt tuần tra chưa hoàn thành. "
                    "Hãy hoàn thành hoặc đóng lượt hiện tại trước khi bắt đầu tuyến khác."
                )
            if task and luot and luot.nhiem_vu_tuan_tra_ca_id and luot.nhiem_vu_tuan_tra_ca_id != task.pk:
                raise ValidationError("Bạn đang thực hiện nhiệm vụ tuần tra khác trong ca này.")

            if not luot:
                required_count = _checkpoint_queryset().filter(loai_tuan_tra=loai).count()
                luot = _patrol_queryset().create(
                    nhan_vien=nhan_vien,
                    loai_tuan_tra=loai,
                    phan_cong_ca_truc=shift_context.shift,
                    lich_tuan_tra_van_hanh=task.lich_tuan_tra if task else None,
                    nhiem_vu_tuan_tra_ca=task if task else None,
                    trang_thai="DANG_DI",
                    trang_thai_doi_soat="IN_PROGRESS",
                    so_diem_bat_buoc=required_count,
                    so_diem_da_quet=0,
                    so_diem_canh_bao=0,
                )
                created = True
            else:
                update_fields = []
                if not luot.phan_cong_ca_truc_id:
                    luot.phan_cong_ca_truc = shift_context.shift
                    update_fields.append("phan_cong_ca_truc")
                if task and not luot.nhiem_vu_tuan_tra_ca_id:
                    luot.nhiem_vu_tuan_tra_ca = task
                    luot.lich_tuan_tra_van_hanh = task.lich_tuan_tra
                    update_fields.extend(["nhiem_vu_tuan_tra_ca", "lich_tuan_tra_van_hanh"])
                if luot.trang_thai_doi_soat != "IN_PROGRESS":
                    luot.trang_thai_doi_soat = "IN_PROGRESS"
                    update_fields.append("trang_thai_doi_soat")
                required_count = _checkpoint_queryset().filter(loai_tuan_tra=luot.loai_tuan_tra).count()
                if luot.so_diem_bat_buoc != required_count:
                    luot.so_diem_bat_buoc = required_count
                    update_fields.append("so_diem_bat_buoc")
                if update_fields:
                    luot.save(update_fields=update_fields)

            if task:
                task.trang_thai = NhiemVuTuanTraCa.TrangThai.IN_PROGRESS
                task.luot_tuan_tra = luot
                task.so_diem_bat_buoc = luot.so_diem_bat_buoc
                task.save(update_fields=["trang_thai", "luot_tuan_tra", "so_diem_bat_buoc", "updated_at"])

            _audit(
                user=getattr(nhan_vien, "user", None),
                action=AuditLog.Action.EXECUTE,
                model_name="LuotTuanTra",
                object_id=luot.pk,
                note=f"Bắt đầu/tiếp tục lượt tuần tra vận hành: {luot.loai_tuan_tra.ten_loai}",
                changes={
                    "domain_owner": "operations.guard_patrol",
                    "requested_id": loai_id,
                    "requested_type": "operations.NhiemVuTuanTraCa" if task else "inspection.LoaiTuanTra.LEGACY_FALLBACK",
                    "active_loai_tuan_tra_id": luot.loai_tuan_tra_id,
                    "lich_tuan_tra_van_hanh_id": task.lich_tuan_tra_id if task else None,
                    "nhiem_vu_tuan_tra_ca_id": task.pk if task else None,
                    "phan_cong_ca_truc_id": shift_context.shift.pk,
                    "muc_tieu_id": loai.muc_tieu_id,
                    "vi_tri_chot_id": shift_context.shift.vi_tri_chot_id,
                    "required_gps": required_gps,
                    "required_photo": required_photo,
                    "trang_thai": luot.trang_thai,
                    "created": created,
                },
            )
        return luot


class RecordGuardPatrolCheckpointUseCase:
    """Record QR/GPS/photo evidence for a guard patrol checkpoint."""

    @staticmethod
    def execute(nhan_vien, luot_id, ma_qr, lat_req, lng_req, hinh_anh_xac_thuc=None):
        nhan_vien = _require_employee(nhan_vien)
        if not ma_qr:
            raise ValidationError("Thiếu mã QR điểm tuần tra.")

        luot = get_object_or_404(
            _patrol_queryset().select_related(
                "loai_tuan_tra",
                "loai_tuan_tra__muc_tieu",
                "phan_cong_ca_truc",
                "lich_tuan_tra_van_hanh",
                "nhiem_vu_tuan_tra_ca",
            ),
            id=luot_id,
            nhan_vien=nhan_vien,
            trang_thai="DANG_DI",
        )
        if luot.phan_cong_ca_truc_id:
            shift_context = GuardPatrolShiftContext(shift=luot.phan_cong_ca_truc)
        else:
            shift_context = _guard_shift_for_route(nhan_vien, luot.loai_tuan_tra)
        if not shift_context:
            raise PermissionDenied("Bạn không có ca trực hợp lệ để ghi nhận tuần tra tuyến này.")

        task = luot.nhiem_vu_tuan_tra_ca
        schedule = luot.lich_tuan_tra_van_hanh or (task.lich_tuan_tra if task else None)
        required_photo = bool(getattr(schedule, "yeu_cau_anh", False)) if schedule else bool(getattr(settings, "GUARD_PATROL_REQUIRE_PHOTO", False))
        required_gps = bool(getattr(schedule, "yeu_cau_gps", False)) if schedule else bool(getattr(luot.loai_tuan_tra, "yeu_cau_gps", False))

        diem = _checkpoint_queryset().filter(
            loai_tuan_tra=luot.loai_tuan_tra,
            ma_qr=ma_qr,
        ).first()
        if not diem:
            return False, "Mã QR không thuộc tuyến/mục tiêu của ca trực này.", {"error_code": "CHECKPOINT_OUT_OF_ROUTE"}

        if _evidence_queryset().filter(luot_tuan_tra=luot, diem_tuan_tra=diem).exists():
            return False, "Đã quét điểm này rồi!", {}

        if required_photo and not hinh_anh_xac_thuc:
            _audit(
                user=getattr(nhan_vien, "user", None),
                action=AuditLog.Action.EXECUTE,
                model_name="GhiNhanTuanTra",
                note=f"Từ chối ghi nhận checkpoint {diem.ten_diem}: thiếu ảnh bắt buộc.",
                changes={
                    "domain_owner": "operations.guard_patrol",
                    "luot_tuan_tra_id": luot.pk,
                    "diem_tuan_tra_id": diem.pk,
                    "phan_cong_ca_truc_id": shift_context.shift.pk,
                    "reason": "MISSING_REQUIRED_PHOTO",
                },
            )
            return False, "Tuyến tuần tra này bắt buộc ảnh xác thực. Vui lòng chụp ảnh và quét lại.", {"error_code": "MISSING_REQUIRED_PHOTO"}

        trang_thai = "HOP_LE"
        khoang_cach = 0.0
        msg_warning = ""

        has_gps = _has_gps_coordinates(lat_req, lng_req)
        missing_gps = not has_gps
        if missing_gps and required_gps:
            _audit(
                user=getattr(nhan_vien, "user", None),
                action=AuditLog.Action.EXECUTE,
                model_name="GhiNhanTuanTra",
                note=f"Từ chối ghi nhận checkpoint {diem.ten_diem}: thiếu GPS bắt buộc.",
                changes={
                    "domain_owner": "operations.guard_patrol",
                    "luot_tuan_tra_id": luot.pk,
                    "diem_tuan_tra_id": diem.pk,
                    "phan_cong_ca_truc_id": shift_context.shift.pk,
                    "reason": "MISSING_REQUIRED_GPS",
                },
            )
            return False, "Tuyến tuần tra này bắt buộc GPS. Vui lòng bật định vị và quét lại.", {"error_code": "MISSING_REQUIRED_GPS"}

        if missing_gps:
            trang_thai = "MAT_GPS"
            msg_warning = " (Mất GPS - Đã ghi nhận cảnh báo)"
        else:
            eval_result = GeofenceEvaluator.validate(
                user_lat=float(lat_req),
                user_lng=float(lng_req),
                target_lat=float(diem.vi_do),
                target_lng=float(diem.kinh_do),
                radius_m=float(diem.ban_kinh_cho_phep),
            )
            khoang_cach = eval_result.distance_meters
            if eval_result.is_within_radius:
                trang_thai = "HOP_LE"
            elif khoang_cach <= 200:
                trang_thai = "CANH_BAO_XA"
                msg_warning = f" (Hơi xa {int(khoang_cach)}m - Đã ghi nhận cảnh báo)"
            else:
                _audit(
                    user=getattr(nhan_vien, "user", None),
                    action=AuditLog.Action.EXECUTE,
                    model_name="GhiNhanTuanTra",
                    note=f"Từ chối checkpoint {diem.ten_diem}: GPS ngoài bán kính cho phép.",
                    changes={
                        "domain_owner": "operations.guard_patrol",
                        "luot_tuan_tra_id": luot.pk,
                        "diem_tuan_tra_id": diem.pk,
                        "phan_cong_ca_truc_id": shift_context.shift.pk,
                        "distance_meters": khoang_cach,
                        "reason": "GPS_OUT_OF_RADIUS",
                    },
                )
                return False, f"Vị trí quá xa ({int(khoang_cach)}m)! Hãy lại gần điểm quét.", {"error_code": "GPS_OUT_OF_RADIUS"}

        try:
            with transaction.atomic():
                ghi_nhan = _evidence_queryset().create(
                    luot_tuan_tra=luot,
                    diem_tuan_tra=diem,
                    lat_thuc_te=lat_req if has_gps else None,
                    lng_thuc_te=lng_req if has_gps else None,
                    khoang_cach=khoang_cach,
                    ket_qua=trang_thai,
                    ghi_chu=msg_warning.strip(),
                    hinh_anh_xac_thuc=hinh_anh_xac_thuc,
                )
                _audit(
                    user=getattr(nhan_vien, "user", None),
                    action=AuditLog.Action.CREATE,
                    model_name="GhiNhanTuanTra",
                    object_id=ghi_nhan.pk,
                    note=f"Ghi nhận bằng chứng tuần tra vận hành tại {diem.ten_diem}. Kết quả: {trang_thai}.",
                    changes={
                        "domain_owner": "operations.guard_patrol",
                        "luot_tuan_tra_id": luot.pk,
                        "diem_tuan_tra_id": diem.pk,
                        "phan_cong_ca_truc_id": shift_context.shift.pk,
                        "ket_qua": trang_thai,
                        "khoang_cach": khoang_cach,
                        "has_photo": bool(hinh_anh_xac_thuc),
                    },
                )
                evidence_qs = _evidence_queryset().filter(luot_tuan_tra=luot)
                luot.so_diem_bat_buoc = _checkpoint_queryset().filter(loai_tuan_tra=luot.loai_tuan_tra).count()
                luot.so_diem_da_quet = evidence_qs.values("diem_tuan_tra_id").distinct().count()
                luot.so_diem_canh_bao = evidence_qs.exclude(ket_qua="HOP_LE").count()
                luot.trang_thai_doi_soat = "IN_PROGRESS"
                luot.save(update_fields=[
                    "so_diem_bat_buoc",
                    "so_diem_da_quet",
                    "so_diem_canh_bao",
                    "trang_thai_doi_soat",
                ])
                if task:
                    task.trang_thai = NhiemVuTuanTraCa.TrangThai.IN_PROGRESS
                    task.luot_tuan_tra = luot
                    task.so_diem_bat_buoc = luot.so_diem_bat_buoc
                    task.so_diem_da_quet = luot.so_diem_da_quet
                    task.so_diem_canh_bao = luot.so_diem_canh_bao
                    task.save(update_fields=[
                        "trang_thai",
                        "luot_tuan_tra",
                        "so_diem_bat_buoc",
                        "so_diem_da_quet",
                        "so_diem_canh_bao",
                        "updated_at",
                    ])
        except IntegrityError:
            return False, "Đã quét điểm này rồi!", {}

        return True, "Thành công" + msg_warning, {"ten_diem": diem.ten_diem}


class CompleteGuardPatrolSessionUseCase:
    """Complete a patrol only when all required checkpoints have evidence."""

    @staticmethod
    def execute(nhan_vien, luot_id):
        nhan_vien = _require_employee(nhan_vien)
        with transaction.atomic():
            luot = get_object_or_404(
                _patrol_queryset().select_for_update().select_related(
                    "loai_tuan_tra",
                    "loai_tuan_tra__muc_tieu",
                    "phan_cong_ca_truc",
                    "lich_tuan_tra_van_hanh",
                    "nhiem_vu_tuan_tra_ca",
                ),
                id=luot_id,
                nhan_vien=nhan_vien,
            )
            if luot.trang_thai == "HOAN_THANH":
                return luot
            if luot.trang_thai != "DANG_DI":
                raise ValidationError("Chỉ có thể hoàn thành lượt tuần tra đang thực hiện.")

            if luot.phan_cong_ca_truc_id:
                shift_context = GuardPatrolShiftContext(shift=luot.phan_cong_ca_truc)
            else:
                shift_context = _guard_shift_for_route(nhan_vien, luot.loai_tuan_tra)
            if not shift_context:
                raise PermissionDenied("Bạn không có ca trực hợp lệ để hoàn thành tuần tra tuyến này.")
            task = luot.nhiem_vu_tuan_tra_ca

            required_checkpoint_ids = set(
                _checkpoint_queryset()
                .filter(loai_tuan_tra=luot.loai_tuan_tra)
                .values_list("id", flat=True)
            )
            if not required_checkpoint_ids:
                raise ValidationError("Tuyến tuần tra chưa có điểm bắt buộc nên không thể hoàn thành hợp lệ.")

            scanned_rows = list(
                _evidence_queryset()
                .filter(luot_tuan_tra=luot)
                .values("diem_tuan_tra_id", "ket_qua")
            )
            scanned_checkpoint_ids = {row["diem_tuan_tra_id"] for row in scanned_rows}
            missing_checkpoint_ids = sorted(required_checkpoint_ids - scanned_checkpoint_ids)
            if missing_checkpoint_ids:
                raise ValidationError("Chưa quét đủ điểm tuần tra bắt buộc nên chưa thể hoàn thành hợp lệ.")

            warning_count = sum(1 for row in scanned_rows if row["ket_qua"] != "HOP_LE")
            completion_quality = "COMPLETED_WITH_WARNINGS" if warning_count else "COMPLETED_VALID"

            luot.trang_thai = "HOAN_THANH"
            luot.thoi_gian_ket_thuc = timezone.now()
            luot.phan_cong_ca_truc = shift_context.shift
            luot.trang_thai_doi_soat = completion_quality
            luot.so_diem_bat_buoc = len(required_checkpoint_ids)
            luot.so_diem_da_quet = len(scanned_checkpoint_ids)
            luot.so_diem_canh_bao = warning_count
            luot.full_clean(exclude=None)
            luot.save(update_fields=[
                "trang_thai",
                "thoi_gian_ket_thuc",
                "phan_cong_ca_truc",
                "trang_thai_doi_soat",
                "so_diem_bat_buoc",
                "so_diem_da_quet",
                "so_diem_canh_bao",
            ])
            if task:
                task.trang_thai = completion_quality
                task.luot_tuan_tra = luot
                task.so_diem_bat_buoc = luot.so_diem_bat_buoc
                task.so_diem_da_quet = luot.so_diem_da_quet
                task.so_diem_canh_bao = luot.so_diem_canh_bao
                task.save(update_fields=[
                    "trang_thai",
                    "luot_tuan_tra",
                    "so_diem_bat_buoc",
                    "so_diem_da_quet",
                    "so_diem_canh_bao",
                    "updated_at",
                ])
            _audit(
                user=getattr(nhan_vien, "user", None),
                action=AuditLog.Action.EXECUTE,
                model_name="LuotTuanTra",
                object_id=luot.pk,
                note=(
                    f"Hoàn thành lượt tuần tra vận hành: {luot.loai_tuan_tra.ten_loai}. "
                    f"Tiến độ: {luot.tien_do}%. Chất lượng: {completion_quality}."
                ),
                changes={
                    "domain_owner": "operations.guard_patrol",
                    "trang_thai": "HOAN_THANH",
                    "completion_quality": completion_quality,
                    "tien_do": luot.tien_do,
                    "phan_cong_ca_truc_id": shift_context.shift.pk,
                    "lich_tuan_tra_van_hanh_id": luot.lich_tuan_tra_van_hanh_id,
                    "nhiem_vu_tuan_tra_ca_id": task.pk if task else None,
                    "warning_checkpoint_count": warning_count,
                },
            )
        return luot



# Dashboard/read paths intentionally do not materialize tasks. Task creation is
# restricted to MaterializeGuardPatrolTasksUseCase or the authenticated guard's
# current-shift mobile list path.

class GuardPatrolComplianceUseCase:
    """Capped dashboard summary for operations-owned scheduled patrol compliance."""

    @staticmethod
    def execute(*, tenant_id, target_date=None, target_scope_qs=None):
        target_date = target_date or timezone.localdate()
        start_at, end_at = _active_day_bounds(target_date)
        now = timezone.now()

        tasks = (
            NhiemVuTuanTraCa.objects.for_tenant(tenant_id)
            .filter(phan_cong_ca_truc__ngay_truc=target_date)
            .select_related(
                "lich_tuan_tra",
                "tuyen_tuan_tra",
                "tuyen_tuan_tra__muc_tieu",
                "phan_cong_ca_truc",
                "phan_cong_ca_truc__nhan_vien",
                "phan_cong_ca_truc__vi_tri_chot",
            )
        )
        if target_scope_qs is not None:
            tasks = tasks.filter(phan_cong_ca_truc__vi_tri_chot__muc_tieu__in=target_scope_qs)

        overdue_planned = Q(
            trang_thai=NhiemVuTuanTraCa.TrangThai.PLANNED,
            grace_deadline__isnull=False,
            grace_deadline__lt=now,
        )
        stats = tasks.aggregate(
            total=Count("id", distinct=True),
            planned=Count("id", filter=Q(trang_thai=NhiemVuTuanTraCa.TrangThai.PLANNED), distinct=True),
            in_progress=Count("id", filter=Q(trang_thai=NhiemVuTuanTraCa.TrangThai.IN_PROGRESS), distinct=True),
            completed_valid=Count("id", filter=Q(trang_thai=NhiemVuTuanTraCa.TrangThai.COMPLETED_VALID), distinct=True),
            completed_with_warnings=Count("id", filter=Q(trang_thai=NhiemVuTuanTraCa.TrangThai.COMPLETED_WITH_WARNINGS), distinct=True),
            missed=Count("id", filter=Q(trang_thai=NhiemVuTuanTraCa.TrangThai.MISSED) | overdue_planned, distinct=True),
        )
        stats = {key: value or 0 for key, value in stats.items()}
        stats["completed"] = stats["completed_valid"] + stats["completed_with_warnings"]

        patrols = (
            LuotTuanTra.objects.for_tenant(tenant_id)
            .filter(thoi_gian_bat_dau__gte=start_at, thoi_gian_bat_dau__lt=end_at)
            .select_related("nhan_vien", "loai_tuan_tra", "loai_tuan_tra__muc_tieu", "nhiem_vu_tuan_tra_ca")
        )
        if target_scope_qs is not None:
            patrols = patrols.filter(loai_tuan_tra__muc_tieu__in=target_scope_qs)

        anomalies = (
            GhiNhanTuanTra.objects.for_tenant(tenant_id)
            .filter(thoi_gian_quet__gte=start_at, thoi_gian_quet__lt=end_at, ket_qua__in=["CANH_BAO_XA", "MAT_GPS", "GIAN_LAN"])
            .select_related("luot_tuan_tra", "luot_tuan_tra__nhan_vien", "diem_tuan_tra")
            .order_by("-thoi_gian_quet")[:MAX_COMPLIANCE_ITEMS]
        )

        return {
            "stats": stats,
            "tasks": list(tasks.order_by("trang_thai", "thoi_gian_bat_dau_du_kien", "id")[:MAX_COMPLIANCE_ITEMS]),
            "active_sessions": list(patrols.filter(trang_thai="DANG_DI").order_by("-thoi_gian_bat_dau")[:MAX_COMPLIANCE_ITEMS]),
            "anomalies": list(anomalies),
            "canonical_mobile_url_name": "operations:mobile_tuan_tra_list",
            "transition_note": "Routes/checkpoints still use legacy inspection tables, but schedules and shift tasks are owned by operations.",
        }


class MarkMissedGuardPatrolTasksUseCase:
    """Persist overdue PLANNED tasks as MISSED in a controlled job boundary."""

    @staticmethod
    def execute(*, target_date=None, now=None, actor=None, system_actor_label=None):
        target_date = target_date or timezone.localdate()
        now = now or timezone.now()
        audit_context = _require_audit_actor_context(
            actor=actor,
            system_actor_label=system_actor_label,
            reason=SYSTEM_MARK_MISSED_REASON if system_actor_label else "USER_TRIGGERED",
        )
        tasks = list(
            NhiemVuTuanTraCa.objects.for_tenant(_organization_id())
            .filter(
                phan_cong_ca_truc__ngay_truc=target_date,
                trang_thai=NhiemVuTuanTraCa.TrangThai.PLANNED,
                grace_deadline__isnull=False,
                grace_deadline__lt=now,
            )
            .select_related("phan_cong_ca_truc", "tuyen_tuan_tra")
            .order_by("grace_deadline", "id")[:MAX_TASKS_TO_MARK_MISSED]
        )

        updated_count = 0
        with transaction.atomic():
            for task in tasks:
                old_status = task.trang_thai
                task.trang_thai = NhiemVuTuanTraCa.TrangThai.MISSED
                if not task.ly_do_huy_bo:
                    task.ly_do_huy_bo = "Quá hạn grace deadline, chưa bắt đầu tuần tra."
                task.save(update_fields=["trang_thai", "ly_do_huy_bo", "updated_at"])
                updated_count += 1
                _audit(
                    user=audit_context["user"],
                    action=AuditLog.Action.UPDATE,
                    model_name="NhiemVuTuanTraCa",
                    object_id=task.pk,
                    note="Đánh dấu nhiệm vụ tuần tra quá hạn thành MISSED.",
                    changes={
                        "domain_owner": "operations.guard_patrol",
                        "actor_type": audit_context["actor_type"],
                        "actor_label": audit_context["actor_label"],
                        "reason": audit_context["reason"],
                        "trang_thai": {
                            "old": old_status,
                            "new": NhiemVuTuanTraCa.TrangThai.MISSED,
                        },
                        "phan_cong_ca_truc_id": task.phan_cong_ca_truc_id,
                        "tuyen_tuan_tra_id": task.tuyen_tuan_tra_id,
                    },
                )

        _audit(
            user=audit_context["user"],
            action=AuditLog.Action.EXECUTE,
            model_name="GuardPatrolMarkMissedJob",
            note=f"Persist MISSED cho nhiệm vụ tuần tra ngày {target_date:%d/%m/%Y}.",
            changes={
                "domain_owner": "operations.guard_patrol",
                "actor_type": audit_context["actor_type"],
                "actor_label": audit_context["actor_label"],
                "reason": audit_context["reason"],
                "target_date": target_date.isoformat(),
                "updated_task_count": updated_count,
                "effective_now": now.isoformat(),
            },
        )
        return {
            "target_date": target_date,
            "updated_task_count": updated_count,
        }


# Backward-compatible class names used by existing imports/tests.
StartPatrolSessionUseCase = StartGuardPatrolSessionUseCase
RecordPatrolCheckpointUseCase = RecordGuardPatrolCheckpointUseCase
CompletePatrolSessionUseCase = CompleteGuardPatrolSessionUseCase
