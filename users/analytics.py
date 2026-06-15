# -*- coding: utf-8 -*-
"""
Domain Layer: Analytics Logic.
Quy tắc: Pure Python, không phụ thuộc Framework.
"""

def calculate_turnover_rate(leaver_count: int, start_count: int, end_count: int) -> float:
    """
    Tính tỷ lệ biến động nhân sự (%)
    Công thức: (Số người nghỉ / ((Số đầu kỳ + Số cuối kỳ) / 2)) * 100
    """
    avg_staff = (start_count + end_count) / 2
    
    if avg_staff <= 0:
        return 0.0
        
    rate = (leaver_count / avg_staff) * 100
    return round(rate, 2)