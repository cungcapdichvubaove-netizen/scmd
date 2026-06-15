# -*- coding: utf-8 -*-
import calendar
from decimal import Decimal, ROUND_HALF_UP


class PayrollRateConfigurationError(ValueError):
    """Raised when payroll rate configuration is invalid."""


def calculate_hourly_rate(*, monthly_salary, standard_hours_per_day, month, year):
    """
    Tính đơn giá giờ từ lương khoán tháng và giờ chuẩn/ngày.

    Công thức:
    đơn giá giờ = lương khoán tháng / (số ngày thực tế trong tháng * giờ chuẩn/ngày)

    Không dùng float.
    Không return 0 im lặng khi cấu hình sai.
    """
    if monthly_salary is None:
        raise PayrollRateConfigurationError("Thiếu cấu hình lương khoán tháng.")

    if standard_hours_per_day is None:
        raise PayrollRateConfigurationError("Thiếu cấu hình giờ chuẩn/ngày.")

    try:
        days_in_month = calendar.monthrange(int(year), int(month))[1]
        salary = Decimal(str(monthly_salary))
        hours_per_day = Decimal(str(standard_hours_per_day))
    except Exception as exc:
        raise PayrollRateConfigurationError(
            f"Cấu hình tháng/năm hoặc dữ liệu lương không hợp lệ: {month}/{year}"
        ) from exc

    total_standard_hours = Decimal(days_in_month) * hours_per_day

    if salary <= 0:
        raise PayrollRateConfigurationError("Lương khoán tháng phải lớn hơn 0.")

    if total_standard_hours <= 0:
        raise PayrollRateConfigurationError("Tổng giờ chuẩn phải lớn hơn 0.")

    return (salary / total_standard_hours).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )


def resolve_effective_rate_record(rate_records, work_date):
    """
    Resolve the latest effective-dated rate record for a shift date.

    `rate_records` may be a queryset or an in-memory prefetched list. This helper
    keeps the selection rule deterministic and testable outside the model layer.
    If any history exists but none is effective on or before `work_date`, payroll
    must fail fast so retroactive payroll never silently falls back to current
    target configuration.
    """
    records = sorted(
        list(rate_records or []),
        key=lambda record: (record.ngay_hieu_luc, getattr(record, "id", 0) or 0),
    )
    if not records:
        return None

    effective = None
    for record in records:
        if record.ngay_hieu_luc <= work_date:
            effective = record
        else:
            break

    if effective is None:
        raise PayrollRateConfigurationError(
            "Thiếu baseline đơn giá hiệu lực cho ngày trực trước mốc lịch sử đầu tiên."
        )
    return effective
