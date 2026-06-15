from datetime import date, datetime

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from core.datetime_ranges import local_date_range_bounds, local_day_bounds


@override_settings(USE_TZ=True, TIME_ZONE="Asia/Saigon")
class LocalDateRangeHelperTests(SimpleTestCase):
    def test_local_day_bounds_returns_half_open_range(self):
        start_at, end_at = local_day_bounds(date(2026, 6, 15))

        self.assertEqual(start_at.isoformat(), "2026-06-15T00:00:00+07:00")
        self.assertEqual(end_at.isoformat(), "2026-06-16T00:00:00+07:00")

    def test_local_date_range_bounds_includes_entire_end_day(self):
        start_at, end_at = local_date_range_bounds(date(2026, 6, 1), date(2026, 6, 7))

        self.assertEqual(start_at.isoformat(), "2026-06-01T00:00:00+07:00")
        self.assertEqual(end_at.isoformat(), "2026-06-08T00:00:00+07:00")

    def test_local_day_bounds_normalizes_aware_datetime_to_local_midnight(self):
        aware_dt = timezone.make_aware(datetime(2026, 6, 15, 14, 30))

        start_at, end_at = local_day_bounds(aware_dt)

        self.assertEqual(start_at.isoformat(), "2026-06-15T00:00:00+07:00")
        self.assertEqual(end_at.isoformat(), "2026-06-16T00:00:00+07:00")

    def test_local_date_range_bounds_rejects_reversed_range(self):
        with self.assertRaisesMessage(ValueError, "date_to must be greater than or equal to date_from"):
            local_date_range_bounds(date(2026, 6, 8), date(2026, 6, 7))
