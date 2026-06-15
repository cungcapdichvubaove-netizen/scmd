# -*- coding: utf-8 -*-
"""
Application Layer: Attendance Use Cases.
Điều phối business flows cho Check-in và Check-out.

SSOT: operations/use_cases/attendance_use_cases.py
      (DOCUMENTATION.md Section 5.2 — Application Layer)
Version: v2.0.1

Import chain (dependency hướng vào trong):
    Interface → [this file] → core.domain.geo (Domain Layer)
                            → operations.models (Infrastructure via ORM)

KHÔNG được import:
    - request / response (HTTP layer)
    - Template / View layer
"""

import logging

from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone

from core.domain.geo import validate_geofence
from operations.models import ChamCong

logger = logging.getLogger(__name__)


class CheckInUseCase:
    """
    Use Case: Thực thi quy trình Check-in đầy đủ.

    Flow:
        1. [Domain]        Validate Geofencing (Pure Python — không DB)
        2. [Infrastructure] Persist ChamCong với transaction.atomic()

    Input validation (lat/lng range, ca_truc_id type) do Serializer tại API
    entry point hoặc View xử lý trước khi gọi Use Case này.
    """

    @staticmethod
    def execute(
        phan_cong,
        lat,
        lng,
        image,
        ip: str,
        device_info: str,
        note: str = "",
        user=None,
    ) -> tuple[bool, str, dict | None]:
        """
        Args:
            phan_cong : PhanCongCaTruc instance
            lat       : vĩ độ (float hoặc Decimal hoặc str — đã validated)
            lng       : kinh độ (float hoặc Decimal hoặc str — đã validated)
            image     : File upload (có thể None)
            ip        : IP address của thiết bị
            device_info: User-Agent string
            note      : ghi chú tuỳ chọn
            user      : User instance (dùng cho audit trail nếu cần)

        Returns:
            (success: bool, message: str, data: dict | None)
        """
        # 1. Domain Logic: Xác thực Geofencing (SSOT từ MucTieu)
        is_valid_location = True
        distance = 0.0

        try:
            target = phan_cong.vi_tri_chot.muc_tieu
            if lat and lng and target.vi_do and target.kinh_do:
                is_valid_location, distance = validate_geofence(
                    current_lat=float(lat),
                    current_lng=float(lng),
                    target_lat=float(target.vi_do),
                    target_lng=float(target.kinh_do),
                    radius=float(target.ban_kinh_cho_phep or 100),
                )
        except (AttributeError, ValueError, TypeError) as e:
            logger.warning(
                f"[CheckInUseCase] Geofence validation skipped for PhanCong "
                f"{phan_cong.id}: {e}"
            )
            is_valid_location = False
            distance = 0.0

        # 2. Infrastructure: Persist → atomic để tránh partial write
        with transaction.atomic():
            point = (
                Point(float(lng), float(lat), srid=4326)
                if lat and lng
                else None
            )

            cham_cong, created = ChamCong.objects.get_or_create(
                ca_truc=phan_cong,
                defaults={
                    "thoi_gian_check_in": timezone.now(),
                    "anh_check_in": image,
                    "location_check_in": point,
                    "ip_check_in": ip,
                    "thiet_bi_check_in": device_info,
                    "vi_tri_hop_le": is_valid_location,
                    "khoang_cach_check_in": distance,
                    "ghi_chu": note,
                },
            )

            if not created:
                return (
                    False,
                    "Bạn đã check-in ca này rồi.",
                    {"time": cham_cong.thoi_gian_check_in},
                )

        logger.info(
            f"[CheckIn] NV={phan_cong.nhan_vien} | CaTruc={phan_cong.id} | "
            f"Valid={is_valid_location} | Dist={distance:.1f}m"
        )
        return True, "Check-in thành công.", {
            "time": cham_cong.thoi_gian_check_in,
            "id": cham_cong.id,
            "vi_tri_hop_le": is_valid_location,
            "khoang_cach": round(distance, 1),
        }


class CheckOutUseCase:
    """
    Use Case: Thực thi quy trình Check-out đầy đủ.

    Flow:
        1. Guard: Tìm ChamCong đã check-in
        2. Guard: Chưa check-out rồi
        3. [Infrastructure] Update ChamCong với transaction.atomic()
        4. Trigger Celery task tính giờ công (fire-and-forget)
    """

    @staticmethod
    def execute(
        phan_cong,
        lat,
        lng,
        image,
        ip: str,
        device_info: str,
        note: str = "",
        user=None,
    ) -> tuple[bool, str, dict | None]:
        """
        Returns:
            (success: bool, message: str, data: dict | None)
        """
        # 1. Guard: Tìm bản ghi check-in
        try:
            cham_cong = phan_cong.chamcong
        except ChamCong.RelatedObjectDoesNotExist:
            return False, "Chưa tìm thấy dữ liệu Check-in cho ca này.", None

        # 2. Guard: Đã check-out rồi
        if cham_cong.thoi_gian_check_out:
            return (
                False,
                "Ca trực này đã check-out rồi.",
                {"time": cham_cong.thoi_gian_check_out},
            )

        # 3. Infrastructure: Persist
        with transaction.atomic():
            cham_cong.thoi_gian_check_out = timezone.now()
            cham_cong.anh_check_out = image
            if lat and lng:
                cham_cong.location_check_out = Point(
                    float(lng), float(lat), srid=4326
                )
            cham_cong.ip_check_out = ip
            cham_cong.thiet_bi_check_out = device_info
            if note:
                existing = cham_cong.ghi_chu or ""
                cham_cong.ghi_chu = f"{existing} | {note}".strip(" |")
            cham_cong.save()

        # 4. Trigger Celery task tính giờ công (fire-and-forget, ngoài atomic block)
        try:
            from operations.tasks import process_timesheet_async
            process_timesheet_async.delay(cham_cong.id)
        except Exception as e:
            # Non-critical: chỉ log, không fail checkout
            logger.warning(f"[CheckOut] Không schedule timesheet task: {e}")

        logger.info(
            f"[CheckOut] NV={phan_cong.nhan_vien} | CaTruc={phan_cong.id} | "
            f"ChamCong={cham_cong.id}"
        )
        return True, "Check-out thành công.", {
            "time": cham_cong.thoi_gian_check_out,
            "id": cham_cong.id,
        }
