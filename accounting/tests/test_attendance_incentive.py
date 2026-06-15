from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from accounting.domain.attendance_incentive import calculate_attendance_incentive


class AttendanceIncentiveTests(SimpleTestCase):
    def setUp(self):
        self.muc_tieu = SimpleNamespace(
            tien_chuyen_can=Decimal("1000000"),
            tru_nghi_1_ngay=Decimal("400000"),
            tru_nghi_2_ngay=Decimal("300000"),
            tru_nghi_3_ngay=Decimal("1000000"),
        )

    def test_full_attendance_gets_full_bonus(self):
        result = calculate_attendance_incentive(
            muc_tieu=self.muc_tieu,
            absent_days=0,
        )
        self.assertEqual(result["thuong_chuyen_can_thuc_te"], Decimal("1000000"))

    def test_absent_one_day(self):
        result = calculate_attendance_incentive(
            muc_tieu=self.muc_tieu,
            absent_days=1,
        )
        self.assertEqual(result["thuong_chuyen_can_thuc_te"], Decimal("600000"))

    def test_absent_two_days(self):
        result = calculate_attendance_incentive(
            muc_tieu=self.muc_tieu,
            absent_days=2,
        )
        self.assertEqual(result["thuong_chuyen_can_thuc_te"], Decimal("700000"))

    def test_absent_three_or_more_days(self):
        result = calculate_attendance_incentive(
            muc_tieu=self.muc_tieu,
            absent_days=3,
        )
        self.assertEqual(result["thuong_chuyen_can_thuc_te"], Decimal("0"))
