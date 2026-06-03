# -*- coding: utf-8 -*-
"""
Domain Layer: Geo-spatial Business Rules.
Pure Python implementation, independent of Framework/ORM.
Version: v2.0.0 (Clean Architecture)
"""

import math

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two points on Earth in meters.
    Sử dụng công thức Haversine để đảm bảo độ chính xác cho tọa độ GPS.
    """
    R = 6371000  # Bán kính trái đất trung bình (mét)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def validate_geofence(current_lat: float, current_lng: float, target_lat: float, target_lng: float, radius: float) -> tuple[bool, float]:
    """Kiểm tra xem tọa độ hiện tại có nằm trong bán kính cho phép của mục tiêu không."""
    distance = calculate_haversine_distance(current_lat, current_lng, target_lat, target_lng)
    return distance <= radius, distance