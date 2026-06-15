from decimal import Decimal

from django.test import SimpleTestCase

from accounting.domain.payroll_rate import (
    PayrollRateConfigurationError,
    calculate_hourly_rate,
)


class PayrollRateTests(SimpleTestCase):
    def test_calculate_hourly_rate_8_hours_per_day(self):
        result = calculate_hourly_rate(
            monthly_salary=Decimal("6000000"),
            standard_hours_per_day=Decimal("8.00"),
            month=3,
            year=2025,
        )
        self.assertEqual(result, Decimal("24193.5484"))

    def test_calculate_hourly_rate_28_days(self):
        result = calculate_hourly_rate(
            monthly_salary=Decimal("6000000"),
            standard_hours_per_day=Decimal("12"),
            month=2,
            year=2025,
        )
        self.assertEqual(result, Decimal("17857.1429"))

    def test_calculate_hourly_rate_31_days(self):
        result = calculate_hourly_rate(
            monthly_salary=Decimal("6000000"),
            standard_hours_per_day=Decimal("12"),
            month=3,
            year=2025,
        )
        self.assertEqual(result, Decimal("16129.0323"))

    def test_calculate_hourly_rate_24_hours_per_day(self):
        result = calculate_hourly_rate(
            monthly_salary=Decimal("6000000"),
            standard_hours_per_day=Decimal("24.00"),
            month=3,
            year=2025,
        )
        self.assertEqual(result, Decimal("8064.5161"))

    def test_invalid_salary_raises(self):
        with self.assertRaises(PayrollRateConfigurationError):
            calculate_hourly_rate(
                monthly_salary=Decimal("0"),
                standard_hours_per_day=Decimal("12"),
                month=3,
                year=2025,
            )

    def test_invalid_standard_hours_raises(self):
        with self.assertRaises(PayrollRateConfigurationError):
            calculate_hourly_rate(
                monthly_salary=Decimal("6000000"),
                standard_hours_per_day=Decimal("0"),
                month=3,
                year=2025,
            )
