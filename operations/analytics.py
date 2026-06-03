# Moving from operations/analytics.py
def calculate_swap_rate(swap_count: int, total_shifts: int) -> float:
    if total_shifts <= 0:
        return 0.0
    return round((swap_count / total_shifts) * 100, 2)