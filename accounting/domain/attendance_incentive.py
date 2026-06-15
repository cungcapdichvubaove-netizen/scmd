# -*- coding: utf-8 -*-
from decimal import Decimal, ROUND_HALF_UP


def to_money(value):
    if value is None:
        return Decimal("0")
    return Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def calculate_attendance_incentive(*, muc_tieu, absent_days):
    """
    Tính thưởng chuyên cần thực nhận theo bậc thang tại Mục tiêu.

    Quy ước V1:
    - Nghỉ 0 ngày: nhận đủ tien_chuyen_can.
    - Nghỉ 1 ngày: tien_chuyen_can - tru_nghi_1_ngay.
    - Nghỉ 2 ngày: tien_chuyen_can - tru_nghi_2_ngay.
    - Nghỉ >= 3 ngày: tien_chuyen_can - tru_nghi_3_ngay.
    - Không cho âm.
    """
    max_bonus = to_money(getattr(muc_tieu, "tien_chuyen_can", 0))

    if absent_days <= 0:
        deduction = Decimal("0")
        rule = "FULL_ATTENDANCE_BONUS"
    elif absent_days == 1:
        deduction = to_money(getattr(muc_tieu, "tru_nghi_1_ngay", 0))
        rule = "ABSENT_1_DAY"
    elif absent_days == 2:
        deduction = to_money(getattr(muc_tieu, "tru_nghi_2_ngay", 0))
        rule = "ABSENT_2_DAYS"
    else:
        deduction = to_money(getattr(muc_tieu, "tru_nghi_3_ngay", 0))
        rule = "ABSENT_3_OR_MORE_DAYS"

    actual_bonus = max(max_bonus - deduction, Decimal("0"))

    return {
        "tien_chuyen_can_goc": max_bonus,
        "so_ngay_nghi": int(absent_days or 0),
        "khau_tru_chuyen_can": deduction,
        "thuong_chuyen_can_thuc_te": actual_bonus,
        "rule": rule,
    }
