# -*- coding: utf-8 -*-
"""
Domain Layer: Geospatial Logic.
Quy tắc: KHÔNG import Django, chỉ dùng Pure Python.
"""
import math
from typing import Tuple, Union

def validate_geofence(
    user_lat: Union[float, str], 
    user_lng: Union[float, str], 
    target_lat: Union[float, str], 
    target_lng: Union[float, str], 
    radius_m: Union[float, str]
) -> Tuple[bool, float]:
    """
    Kiểm tra xem tọa độ người dùng có nằm trong bán kính cho phép của mục tiêu hay không.
    Sử dụng công thức Haversine.
    """
    # Chuyển đổi sang radian
    lat1, lon1 = math.radians(float(user_lat)), math.radians(float(user_lng))
    lat2, lon2 = math.radians(float(target_lat)), math.radians(float(target_lng))

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Bán kính Trái đất tính bằng mét
    r = 6371000
    
    distance = c * r
    is_valid = distance <= float(radius_m)
    
    return is_valid, distance