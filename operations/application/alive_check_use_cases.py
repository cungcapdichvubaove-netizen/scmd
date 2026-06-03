# -*- coding: utf-8 -*-
"""
Application Layer: Alive Check Use Cases.
Description: Xử lý các nghiệp vụ liên quan đến kiểm tra quân số đột xuất.
"""

import logging
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from core.domain.geo import validate_geofence
from operations.models import KiemTraQuanSo
from main.decorators import application_audit_log
from main.models import AuditLog

logger = logging.getLogger(__name__)

class CreateAliveCheckUseCase:
    """
    UseCase: Khởi tạo một yêu cầu kiểm tra quân số từ phía quản lý.
    Đảm bảo tính Atomic, Ghi log và Thông báo realtime.
    """
    @staticmethod
    @application_audit_log(module='operations', model_name='KiemTraQuanSo', action=AuditLog.Action.CREATE)
    def execute(ca_truc, nguoi_kiem_tra, giay_cho_phep=600, **kwargs):
        tenant_id = kwargs.get('tenant_id', settings.SCMD_ORGANIZATION_ID)

        with transaction.atomic():
            check_req = KiemTraQuanSo.objects.create(
                ca_truc=ca_truc,
                thoi_gian_gui_yeu_cau=timezone.now(),
                trang_thai='PENDING',
                tenant_id=tenant_id
            )

            # Broadcast tới thiết bị của bảo vệ (Mobile App)
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"notifications_{ca_truc.nhan_vien.user.id}",
                    {
                        "type": "send_notification",
                        "payload": {
                            "type": "ALIVE_CHECK_REQUEST",
                            "check_id": str(check_req.id),
                            "timeout": giay_cho_phep,
                            "message": "YÊU CẦU XÁC NHẬN QUÂN SỐ ĐỘT XUẤT!"
                        }
                    }
                )

            # Gửi Push Notification qua FCM (ngoài WebSocket)
            if ca_truc.nhan_vien.fcm_token:
                from main.tasks import main_send_fcm_notification
                transaction.on_commit(lambda: main_send_fcm_notification.apply_async(
                    args=[ca_truc.nhan_vien.fcm_token, "YÊU CẦU XÁC NHẬN QUÂN SỐ!", "Bạn có một yêu cầu Alive Check mới. Vui lòng phản hồi ngay!"],
                    kwargs={
                        "data": {"type": "ALIVE_CHECK_REQUEST", "check_id": str(check_req.id)}
                    }
                ))

            # Rule 11.2: Lên lịch Task Celery để tự động đánh dấu quá hạn
            # Dùng transaction.on_commit để đảm bảo task chỉ chạy nếu DB đã commit thành công
            from operations.tasks import operations_auto_expire_alive_check
            transaction.on_commit(lambda: operations_auto_expire_alive_check.apply_async(
                args=[str(check_req.id)],
                countdown=giay_cho_phep
            ))

            return check_req

class ProcessAliveCheckResponseUseCase:
    """
    UseCase: Xử lý phản hồi Alive Check từ bảo vệ.
    Thực hiện so khớp tọa độ GPS và Device ID để phát hiện gian lận.
    """
    @staticmethod
    def execute(check_id: str, lat: float, lon: float, device_id: str, anh_selfie=None) -> tuple[bool, str]:
        tenant_id = settings.SCMD_ORGANIZATION_ID
        
        try:
            with transaction.atomic():
                # 1. Lấy và khóa bản ghi để xử lý (Rule 10: select_for_update)
                check_req = KiemTraQuanSo.objects.select_for_update().get(
                    id=check_id, 
                    tenant_id=tenant_id
                )

                # 2. Kiểm tra tính hợp lệ của trạng thái và thời gian
                if check_req.trang_thai != 'PENDING':
                    return False, "Yêu cầu này đã được xử lý hoặc không còn hiệu lực."

                muc_tieu = check_req.ca_truc.vi_tri_chot.muc_tieu
                is_valid_geo, distance = validate_geofence(
                    user_lat=lat, 
                    user_lng=lon,
                    target_lat=muc_tieu.vi_do, 
                    target_lng=muc_tieu.kinh_do,
                    radius_m=muc_tieu.ban_kinh_cho_phep
                )

                nhan_vien = check_req.ca_truc.nhan_vien

                check_req.thoi_gian_phan_hoi = timezone.now()
                check_req.toa_do_xac_thuc = (
                    f"{lat},{lon}|device={device_id}|distance={round(distance, 2)}"
                )
                if anh_selfie:
                    check_req.anh_xac_thuc = anh_selfie

                if not is_valid_geo:
                    check_req.trang_thai = 'MISSED'
                    result_msg = f"Vi phạm: Vị trí sai lệch {int(distance)}m."
                else:
                    check_req.trang_thai = 'OK'
                    result_msg = "Xác nhận quân số thành công."

                check_req.save()

                # 7. Ghi Audit Log (Rule 8)
                AuditLog.objects.create(
                    action='UPDATE',
                    module='operations',
                    model_name='KiemTraQuanSo',
                    object_id=str(check_req.id),
                    note=f"Phản hồi Alive Check: {nhan_vien.ho_ten}. Kết quả: {check_req.trang_thai}",
                    tenant_id=tenant_id,
                    changes={
                        "status": check_req.trang_thai,
                        "distance": distance,
                        "device_id": device_id,
                        "is_valid_geo": is_valid_geo,
                    }
                )

                return (check_req.trang_thai == 'OK'), result_msg

        except KiemTraQuanSo.DoesNotExist:
            return False, "Không tìm thấy mã yêu cầu kiểm tra."
        except Exception as e:
            logger.error(f"Error in ProcessAliveCheckResponseUseCase: {str(e)}")
            return False, "Lỗi hệ thống khi xử lý phản hồi."

class GetRecentAliveCheckViolationsUseCase:
    """
    UseCase: Truy vấn danh sách các vụ vi phạm điểm danh đột xuất mới nhất.
    Hỗ trợ đối soát tại War Room.
    """
    @staticmethod
    def execute(tenant_id: str, limit: int = 20):
        # Rule 8: N+1 Avoidance - Sử dụng select_related cho các quan hệ FK
        # Rule 4.1: Thực thi for_tenant()
        return KiemTraQuanSo.objects.filter(
            tenant_id=tenant_id
        ).filter(
            trang_thai__in=['MISSED', 'LATE']
        ).select_related(
            'ca_truc__nhan_vien',
            'ca_truc__vi_tri_chot__muc_tieu'
        ).order_by('-thoi_gian_gui_yeu_cau')[:limit]
