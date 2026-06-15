# -*- coding: utf-8 -*-

from decimal import Decimal

from django.test import SimpleTestCase

from accounting.services.payroll_calculation import PayrollCalculationService


class PayrollCalculationServiceTest(SimpleTestCase):
    def test_get_period_bounds_handles_year_rollover(self):
        start, end = PayrollCalculationService.get_period_bounds(12, 2026)

        self.assertEqual(str(start), "2026-12-01")
        self.assertEqual(str(end), "2027-01-01")

    def test_calculate_detail_uses_prebuilt_context_without_db(self):
        nhan_vien = type("NhanVienStub", (), {"id": 7})()
        muc_tieu = type(
            "MucTieuStub",
            (),
            {"id": 99, "ten_muc_tieu": "Muc tieu A", "tien_chuyen_can": Decimal("0")},
        )()
        salary_config = type(
            "SalaryConfigStub",
            (),
            {
                "phu_cap_trach_nhiem": Decimal("500000"),
                "phu_cap_xang_xe": Decimal("200000"),
                "phu_cap_an_uong": Decimal("300000"),
            },
        )()
        batch_context = {
            "total_hours_by_employee": {7: Decimal("8")},
            "base_salary_by_employee": {7: Decimal("240000")},
            "attendance_snapshot_by_employee": {
                7: [{"gio_lam": 8.0, "muc_tieu": "Muc tieu A"}]
            },
            "salary_configs": {7: salary_config},
            "attendance_count_by_employee": {7: 1},
            "actual_work_days_by_employee": {7: 1},
            "expected_work_days_by_employee": {7: 1},
            "target_counter_by_employee": {7: {99: 1}},
            "target_by_id": {99: muc_tieu},
            "fines_by_employee": {7: Decimal("50000")},
            "inventory_by_employee": {7: Decimal("25000")},
            "advances_by_employee": {7: Decimal("100000")},
            "incident_deductions_by_employee": {7: Decimal("75000")},
        }

        result = PayrollCalculationService.calculate_detail(
            nhan_vien=nhan_vien,
            batch_context=batch_context,
        )

        self.assertEqual(result["tong_gio_lam"], 8.0)
        self.assertEqual(result["luong_chinh"], Decimal("240000"))
        self.assertEqual(result["phu_cap_khac"], Decimal("1000000"))
        # Net pay = base salary + allowances - fines/inventory/advances/incidents.
        # 240000 + 1000000 - (50000 + 25000 + 100000 + 75000) = 990000.
        self.assertEqual(result["thuc_lanh"], Decimal("990000"))
