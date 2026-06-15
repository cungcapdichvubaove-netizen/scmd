from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone


class AttendanceWindowPolicy:
    """Single source of truth for attendance time-window validation."""

    CHECKIN = "check_in"
    CHECKOUT = "check_out"

    @classmethod
    def validate(cls, phan_cong, action, current_time=None):
        now = timezone.localtime(current_time or timezone.now())
        start_at, end_at = cls._get_shift_bounds(phan_cong)

        if action == cls.CHECKIN:
            early_minutes = getattr(settings, "ATTENDANCE_CHECKIN_EARLY_MINUTES", 60)
            late_minutes = getattr(settings, "ATTENDANCE_CHECKIN_LATE_MINUTES", 0)
            window_start = start_at - timedelta(minutes=early_minutes)
            window_end = end_at + timedelta(minutes=late_minutes)
            if window_start <= now <= window_end:
                return True, None
            return (
                False,
                "Chua den khung gio check-in hop le cho ca truc nay.",
            )

        checkout_early_minutes = getattr(
            settings,
            "ATTENDANCE_CHECKOUT_EARLY_MINUTES",
            0,
        )
        checkout_late_minutes = getattr(
            settings,
            "ATTENDANCE_CHECKOUT_LATE_MINUTES",
            240,
        )
        window_start = start_at - timedelta(minutes=checkout_early_minutes)
        window_end = end_at + timedelta(minutes=checkout_late_minutes)
        if window_start <= now <= window_end:
            return True, None
        return (
            False,
            "Ngoai khung gio check-out hop le cho ca truc nay.",
        )

    @staticmethod
    def _get_shift_bounds(phan_cong):
        start_at = timezone.make_aware(
            datetime.combine(
                phan_cong.ngay_truc,
                phan_cong.ca_lam_viec.gio_bat_dau,
            )
        )
        end_date = (
            phan_cong.ngay_truc + timedelta(days=1)
            if phan_cong.ca_lam_viec.is_night_shift
            else phan_cong.ngay_truc
        )
        end_at = timezone.make_aware(
            datetime.combine(
                end_date,
                phan_cong.ca_lam_viec.gio_ket_thuc,
            )
        )
        return start_at, end_at


class AttendancePhotoPolicy:
    """Resolves whether proof images are required for a specific shift."""

    CHECKIN = "check_in"
    CHECKOUT = "check_out"

    @classmethod
    def is_required(cls, phan_cong, action):
        if action == cls.CHECKIN:
            candidates = (
                getattr(phan_cong.ca_lam_viec, "bat_buoc_anh_check_in", None),
                getattr(phan_cong.vi_tri_chot, "bat_buoc_anh_check_in", None),
                getattr(
                    phan_cong.vi_tri_chot.muc_tieu,
                    "bat_buoc_anh_check_in",
                    None,
                ),
            )
            default_required = getattr(
                settings,
                "ATTENDANCE_REQUIRE_IMAGE_CHECKIN",
                False,
            )
        else:
            candidates = (
                getattr(phan_cong.ca_lam_viec, "bat_buoc_anh_check_out", None),
                getattr(phan_cong.vi_tri_chot, "bat_buoc_anh_check_out", None),
                getattr(
                    phan_cong.vi_tri_chot.muc_tieu,
                    "bat_buoc_anh_check_out",
                    None,
                ),
            )
            default_required = getattr(
                settings,
                "ATTENDANCE_REQUIRE_IMAGE_CHECKOUT",
                False,
            )

        for candidate in candidates:
            if candidate is not None:
                return bool(candidate)
        return default_required
