from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.utils import timezone


def _coerce_local_start(value: date | datetime) -> datetime:
    current_tz = timezone.get_current_timezone()
    if isinstance(value, datetime):
        start_at = value
        if timezone.is_naive(start_at):
            start_at = timezone.make_aware(start_at, current_tz)
        return timezone.localtime(start_at, current_tz).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    return timezone.make_aware(datetime.combine(value, time.min), current_tz)


def local_day_bounds(target_day: date | datetime) -> tuple[datetime, datetime]:
    """Return timezone-aware local [start, end) bounds for a calendar day."""
    start_at = _coerce_local_start(target_day)
    return start_at, start_at + timedelta(days=1)


def local_date_range_bounds(
    date_from: date | datetime,
    date_to: date | datetime,
) -> tuple[datetime, datetime]:
    """Return timezone-aware local [start, end) bounds for an inclusive date range."""
    start_at, _ = local_day_bounds(date_from)
    end_start, _ = local_day_bounds(date_to)
    if end_start < start_at:
        raise ValueError("date_to must be greater than or equal to date_from")
    return start_at, end_start + timedelta(days=1)
