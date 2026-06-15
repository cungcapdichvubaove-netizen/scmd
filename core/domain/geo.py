# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
Domain Layer: Geofencing logic.
Pure Python only; no Django or database dependency.
"""

import math
from dataclasses import dataclass
from typing import Tuple, Union

CoordinateValue = Union[float, int, str]


@dataclass(frozen=True)
class GeofenceResult:
    is_within_radius: bool
    distance_meters: float


class GeofenceEvaluator:
    """
    Pure geofence evaluator for attendance and alive-check flows.
    """

    EARTH_RADIUS_METERS = 6_371_000

    @classmethod
    def validate(
        cls,
        user_lat: CoordinateValue,
        user_lng: CoordinateValue,
        target_lat: CoordinateValue,
        target_lng: CoordinateValue,
        radius_m: CoordinateValue,
    ) -> GeofenceResult:
        distance = cls.calculate_distance_meters(
            user_lat=user_lat,
            user_lng=user_lng,
            target_lat=target_lat,
            target_lng=target_lng,
        )
        return GeofenceResult(
            is_within_radius=distance <= float(radius_m),
            distance_meters=distance,
        )

    @classmethod
    def calculate_distance_meters(
        cls,
        user_lat: CoordinateValue,
        user_lng: CoordinateValue,
        target_lat: CoordinateValue,
        target_lng: CoordinateValue,
    ) -> float:
        lat1, lon1 = cls._to_radians(user_lat, user_lng)
        lat2, lon2 = cls._to_radians(target_lat, target_lng)

        delta_lon = lon2 - lon1
        delta_lat = lat2 - lat1
        haversine = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
        )
        arc = 2 * math.asin(math.sqrt(haversine))
        return arc * cls.EARTH_RADIUS_METERS

    @staticmethod
    def _to_radians(lat: CoordinateValue, lng: CoordinateValue) -> Tuple[float, float]:
        return math.radians(float(lat)), math.radians(float(lng))


def validate_geofence(
    user_lat: CoordinateValue,
    user_lng: CoordinateValue,
    target_lat: CoordinateValue,
    target_lng: CoordinateValue,
    radius_m: CoordinateValue,
) -> Tuple[bool, float]:
    """
    Backward-compatible wrapper during domain helper migration.
    """
    result = GeofenceEvaluator.validate(
        user_lat=user_lat,
        user_lng=user_lng,
        target_lat=target_lat,
        target_lng=target_lng,
        radius_m=radius_m,
    )
    return result.is_within_radius, result.distance_meters
=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
