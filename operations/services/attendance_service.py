# -*- coding: utf-8 -*-
"""
SCMD Pro
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: operations/services/attendance_service.py
Author: Mr. Anh
Created Date: 2025-12-10
Description: Service xử lý logic Chấm công & Geofencing.
             UPGRADE PHASE 2: Tích hợp GeoDjango/PostGIS.
             - Xử lý tọa độ GPS bằng đối tượng Geometry (Point).
             - Tính toán khoảng cách chính xác trên bề mặt cầu (Geodesic).
"""

from django.utils import timezone
from django.contrib.gis.geos import Point
# from django.contrib.gis.measure import Distance # Dùng khi query DB trực tiếp
from core.domain.geo import GeofenceEvaluator
from operations.models import ChamCong, PhanCongCaTruc

class AttendanceService:
    """
    Lớp dịch vụ tập trung xử lý nghiệp vụ Chấm công với Geo-spatial Intelligence
    """

    @staticmethod
    def calculate_distance_geometry(point1, point2):
        """
        Tính khoảng cách giữa 2 đối tượng GEOSGeometry.
        Trả về: mét (float)
        """
        if not point1 or not point2:
            return 0.0
        
        try:
            return GeofenceEvaluator.calculate_distance_meters(
                user_lat=point1.y,
                user_lng=point1.x,
                target_lat=point2.y,
                target_lng=point2.x,
            )
        except (ValueError, TypeError):
            return 0.0

    @classmethod
    def process_check_in(cls, phan_cong, lat, lng, image=None, ip=None, device_info=None):
        """
        Xử lý logic Check-in với GeoDjango Point
        Return: (success: bool, message: str, data: dict)
        """
        # 1. Kiểm tra đã checkin chưa
        cham_cong, created = ChamCong.objects.get_or_create(ca_truc=phan_cong)
        
        if cham_cong.thoi_gian_check_in:
            return False, "Bạn đã Check-in ca này rồi!", {}

        # 2. Validate GPS Data
        if not lat or not lng:
            return False, "Thiếu dữ liệu GPS. Vui lòng bật định vị.", {}

        try:
            # Lưu ý: Point(longitude, latitude) - Kinh độ trước, Vĩ độ sau
            lat_float = float(lat)
            lng_float = float(lng)
            check_in_point = Point(lng_float, lat_float, srid=4326)
        except (ValueError, TypeError):
            return False, "Tọa độ GPS không hợp lệ (Format error).", {}

        # 3. Geofencing Logic
        vi_tri_hop_le = True
        khoang_cach = 0.0
        muc_tieu = phan_cong.vi_tri_chot.muc_tieu
        msg_warning = ""

        if muc_tieu.vi_do and muc_tieu.kinh_do:
            # Tạo Point tạm cho mục tiêu để tính toán
            # (Giai đoạn sau sẽ migrate Mục tiêu sang PointField luôn)
            try:
                target_point = Point(float(muc_tieu.kinh_do), float(muc_tieu.vi_do), srid=4326)
                
                # Tính khoảng cách
                khoang_cach = cls.calculate_distance_geometry(check_in_point, target_point)
                limit = getattr(muc_tieu, 'ban_kinh_cho_phep', 100)
                
                if khoang_cach > limit:
                    vi_tri_hop_le = False
                    msg_warning = f" [Cảnh báo: Check-in xa {int(khoang_cach)}m]"
            except (ValueError, TypeError):
                # Nếu tọa độ mục tiêu lỗi, tạm bỏ qua check khoảng cách
                pass

        # 4. Lưu dữ liệu
        cham_cong.thoi_gian_check_in = timezone.now()
        cham_cong.location_check_in = check_in_point # Lưu Point object
        
        if image:
            cham_cong.anh_check_in = image
        
        cham_cong.ip_check_in = ip
        cham_cong.thiet_bi_check_in = device_info
        
        cham_cong.vi_tri_hop_le = vi_tri_hop_le
        cham_cong.khoang_cach_check_in = round(khoang_cach, 2)
        
        if msg_warning:
            cham_cong.ghi_chu = (cham_cong.ghi_chu or "") + msg_warning

        cham_cong.save()
        
        return True, "Check-in thành công!", {
            "time": cham_cong.thoi_gian_check_in,
            "distance": khoang_cach,
            "valid": vi_tri_hop_le
        }

    @classmethod
    def process_check_out(cls, phan_cong, lat, lng, image=None, ip=None, device_info=None):
        """
        Xử lý logic Check-out
        """
        try:
            cham_cong = phan_cong.chamcong
        except ChamCong.DoesNotExist:
            return False, "Bạn chưa Check-in, không thể Check-out.", {}

        if cham_cong.thoi_gian_check_out:
            return False, "Bạn đã Check-out ca này rồi.", {}

        cham_cong.thoi_gian_check_out = timezone.now()
        
        if lat and lng:
            try:
                # Point(longitude, latitude)
                check_out_point = Point(float(lng), float(lat), srid=4326)
                cham_cong.location_check_out = check_out_point
            except (ValueError, TypeError):
                pass 
        
        if image:
            cham_cong.anh_check_out = image
            
        cham_cong.ip_check_out = ip
        cham_cong.thiet_bi_check_out = device_info
        
        cham_cong.save()
        
        return True, "Check-out thành công!", {
            "time": cham_cong.thoi_gian_check_out
        }
