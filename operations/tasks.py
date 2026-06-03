# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Infrastructure Layer: Operations Tasks.
"""

import logging
from datetime import timedelta
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from asgiref.sync import async_to_sync
from django.apps import apps
from PIL import Image
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_new_incident_alert(self, incident_id):
    """
    Lightweight incident task used by signals to avoid import-time crashes.
    """
    try:
        from operations.models import BaoCaoSuCo

        incident = BaoCaoSuCo.objects.get(id=incident_id)
        logger.info("Processed incident alert for %s", incident.ma_su_co or incident.id)
        return str(incident.id)
    except BaoCaoSuCo.DoesNotExist:
        logger.warning("Incident %s not found for alert processing", incident_id)
        return None
    except Exception as exc:
        logger.error("Error in process_new_incident_alert: %s", str(exc))
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=2)
def check_target_stability_daily_task(self):
    """
    Task chạy hàng ngày để kiểm tra các chỉ số bất thường tại mục tiêu.
    """
    try:
        from operations.application.attendance_use_cases import MonitorWeeklySwapRateUseCase
        
        tenant_id = settings.SCMD_ORGANIZATION_ID
        count = MonitorWeeklySwapRateUseCase.execute(tenant_id)
        
        return f"Stability check completed. Alerts triggered: {count}"
    except Exception as e:
        logger.error(f"Error in stability monitoring task: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_worker_heartbeat_task(self):
    """
    Task tự động chạy trên workers để cập nhật trạng thái 'Alive'.
    Hostname được lấy trực tiếp từ ngữ cảnh của worker đang thực thi.
    """
    from main.models import WorkerHeartbeat
    hostname = self.request.hostname or "unknown-worker"
    
    WorkerHeartbeat.objects.update_or_create(
        hostname=hostname,
        defaults={
            'is_active': True,
            'tenant_id': settings.SCMD_ORGANIZATION_ID
        }
    )
    return f"Heartbeat updated for {hostname}"

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def monitor_worker_health_and_broadcast_task(self):
    """
    Task giám sát: Phát hiện các worker bị treo (quá 5 phút không ping)
    và broadcast trạng thái tổng thể lên War Room Dashboard qua WebSocket.
    """
    from main.models import WorkerHeartbeat
    
    try:
        # Ngưỡng xác định offline: 5 phút
        threshold = timezone.now() - timedelta(minutes=5)
        offline_workers = WorkerHeartbeat.objects.filter(last_ping__lt=threshold, is_active=True)
        count_deactivated = offline_workers.update(is_active=False)
        
        # Thu thập danh sách đang online
        active_workers = WorkerHeartbeat.objects.filter(is_active=True).values_list('hostname', flat=True)
        total_count = WorkerHeartbeat.objects.count()
        
        # Broadcast qua WebSocket
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "war_room_staff",
                {
                    "type": "worker.status",
                    "payload": {
                        "active_workers": list(active_workers),
                        "active_count": len(active_workers),
                        "total_count": total_count,
                        "timestamp": timezone.now().strftime("%H:%M:%S")
                    }
                }
            )
        
        return f"Health check completed. Active: {len(active_workers)}"
    except Exception as e:
        logger.error(f"Error in worker health monitoring task: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def operations_mark_expired_alive_checks(self):
    """
    Task tự động quét và đánh dấu 'QUA_HAN' cho các yêu cầu Alive Check 
    không được bảo vệ phản hồi trong thời gian quy định.
    Tần suất khuyến nghị: Chạy mỗi 1-5 phút (Celery Beat).
    """
    from operations.models_alive_check import KiemTraQuanSo
    from main.models import AuditLog

    now = timezone.now()
    
    try:
        with transaction.atomic():
            # 1. Tìm các yêu cầu đang chờ nhưng đã quá hạn
            expired_qs = KiemTraQuanSo.objects.filter(
                trang_thai='PENDING',
                thoi_gian_gui_yeu_cau__lt=now - timedelta(minutes=10)
            )
            
            count = expired_qs.count()
            
            if count > 0:
                # 2. Cập nhật trạng thái hàng loạt (Bulk Update)
                expired_qs.update(trang_thai='LATE')
                
                # 3. Ghi Audit Log cho hệ thống (Rule 8)
                AuditLog.objects.create(
                    action='UPDATE',
                    module='operations',
                    model_name='KiemTraQuanSo',
                    note=f"Hệ thống tự động đánh dấu {count} yêu cầu Alive Check quá hạn.",
                    tenant_id=settings.SCMD_ORGANIZATION_ID,
                    status='SUCCESS'
                )
                
                # 4. Broadcast WebSocket tới War Room (Rule 12)
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        "war_room_staff",
                        {
                            "type": "send_notification",
                            "payload": {
                                "type": "ALIVE_CHECK_EXPIRED",
                                "message": f"CẢNH BÁO: {count} nhân sự không phản hồi Alive Check!",
                                "count": count,
                                "severity": "HIGH",
                                "timestamp": now.strftime("%H:%M:%S")
                            }
                        }
                    )
                
                logger.info(f"[Alive-Check-Cleanup] Đã xử lý {count} bản ghi quá hạn tại {now}")
                return f"Processed {count} expired checks."
            
            return "No expired checks found."
            
    except Exception as exc:
        logger.error(f"[Alive-Check-Cleanup] Lỗi khi quét quá hạn: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3)
def operations_auto_expire_alive_check(self, check_id):
    """
    Task kiểm tra trạng thái một yêu cầu Alive Check cụ thể sau khi hết thời gian chờ.
    Nếu vẫn ở trạng thái CHO_XAC_NHAN, hệ thống tự động chuyển sang QUA_HAN.
    """
    from operations.models_alive_check import KiemTraQuanSo
    from main.models import AuditLog

    try:
        with transaction.atomic():
            # Sử dụng select_for_update để tránh race condition với phản hồi từ Mobile
            check_req = KiemTraQuanSo.objects.select_for_update().get(id=check_id)

            if check_req.trang_thai == 'PENDING':
                check_req.trang_thai = 'LATE'
                check_req.save()

                # Ghi Audit Log (Rule 8)
                AuditLog.objects.create(
                    action='UPDATE',
                    module='operations',
                    model_name='KiemTraQuanSo',
                    object_id=str(check_id),
                    note=f"Hệ thống tự động đánh dấu quá hạn sau thời gian chờ.",
                    tenant_id=settings.SCMD_ORGANIZATION_ID,
                    status='SUCCESS'
                )
                
                # Lưu ý: Signal handle_alive_check_broadcast sẽ tự động 
                # gửi WebSocket tới War Room khi trạng thái này thay đổi.
                
                return f"Check {check_id} marked as EXPIRED."
            
            return f"Check {check_id} was already processed (Status: {check_req.trang_thai})."

    except KiemTraQuanSo.DoesNotExist:
        logger.warning(f"[Alive-Check-Timeout] Không tìm thấy bản ghi {check_id}")
    except Exception as exc:
        logger.error(f"[Alive-Check-Timeout] Lỗi xử lý bản ghi {check_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=30)

@shared_task(bind=True, max_retries=3)
def process_timesheet_async(self, cham_cong_id):
    """
    Task tính toán giờ công thực tế sau khi nhân viên check-out.
    Cập nhật kết quả vào trường thuc_lam_gio của ChamCong (SSOT).
    """
    from operations.models import ChamCong
    from operations.application.attendance_use_cases import CalculateWorkHoursUseCase
    from django.db import transaction

    try:
        with transaction.atomic():
            # Khóa bản ghi để tính toán chính xác trong môi trường concurrency
            cham_cong = ChamCong.objects.select_for_update().get(id=cham_cong_id)
            
            # Idempotency check: If already processed, do nothing.
            
            # Thực thi logic tính toán giờ làm việc (Business Rule)
            hours = CalculateWorkHoursUseCase.execute(cham_cong)
            
            # Lưu kết quả vào Database làm nguồn sự thật cho module Kế toán (Rule 7)
            cham_cong.thuc_lam_gio = hours
            # Cập nhật duy nhất trường giờ làm để tránh ghi đè dữ liệu khác
            cham_cong.save(update_fields=['thuc_lam_gio'])
            
            logger.info(f"Timesheet processed for ChamCong {cham_cong_id}: {hours}h")
            return hours
    except ChamCong.DoesNotExist:
        logger.error(f"ChamCong {cham_cong_id} không tồn tại.")
    except Exception as exc:
        logger.error(f"Lỗi xử lý bảng công {cham_cong_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_late_checkout_task(self):
    """
    Task quét các ca trực đã kết thúc nhưng nhân viên chưa check-out.
    Nếu quá 2 giờ sau giờ kết thúc ca, đánh dấu là 'LATE_CHECKOUT' và ghi log.
    """
    from operations.models import ChamCong, PhanCongCaTruc
    from main.models import AuditLog
    from django.db.models import Q

    now = timezone.now()
    late_checkout_threshold = now - timedelta(hours=2)
    
    try:
        # Tìm các bản ghi ChamCong chưa check-out
        # và ca trực của chúng đã kết thúc hơn 2 giờ trước
        late_checkouts_qs = ChamCong.objects.filter(
            thoi_gian_check_out__isnull=True,
            ca_truc__ngay_truc__lte=late_checkout_threshold.date() # Ensure it's not a future shift
        ).select_related('ca_truc__ca_lam_viec', 'ca_truc__nhan_vien')

        count = 0
        with transaction.atomic():
            for cham_cong in late_checkouts_qs:
                # Calculate the actual end time of the shift
                shift_end_time = cham_cong.ca_truc.get_thoi_gian_ket_thuc_thuc_te()
                
                # Only process if shift_end_time is valid and in the past
                if shift_end_time and shift_end_time < late_checkout_threshold:
                    # Idempotency: Avoid re-processing if already flagged
                    if "LATE_CHECKOUT" in cham_cong.ghi_chu:
                        continue

                    cham_cong.ghi_chu = (cham_cong.ghi_chu or "") + " [LATE_CHECKOUT_AUTO_FLAGGED]"
                    cham_cong.save(update_fields=['ghi_chu'])
                    
                    AuditLog.objects.create(
                        action=AuditLog.Action.UPDATE,
                        module='operations',
                        model_name='ChamCong',
                        object_id=str(cham_cong.id),
                        tenant_id=settings.SCMD_ORGANIZATION_ID,
                        note=f"Hệ thống tự động đánh dấu LATE_CHECKOUT cho NV {cham_cong.ca_truc.nhan_vien.ma_nhan_vien} (Ca kết thúc: {shift_end_time}).",
                        status='WARNING'
                    )
                    logger.warning(f"LATE_CHECKOUT: ChamCong ID {cham_cong.id} for {cham_cong.ca_truc.nhan_vien.ho_ten} flagged.")
                    count += 1
        
        return f"Processed {count} late checkouts."
    except Exception as exc:
        logger.error(f"Error in check_late_checkout_task: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def resize_image_async(self, app_label, model_name, obj_id, field_name):
    """
    Task để nén và resize ảnh sau khi upload.
    """
    from django.core.files.base import ContentFile
    import io

    try:
        Model = apps.get_model(app_label, model_name)
        obj = Model.objects.get(pk=obj_id)
        image_field = getattr(obj, field_name)
        if not image_field:
            logger.warning(f"Image field {field_name} not found for {model_name} {obj_id}.")
            return
        # Placeholder for actual image processing logic (e.g., using Pillow)
        logger.info(f"Placeholder: Resizing image for {model_name} {obj_id}, field {field_name}.")
        return f"Image resize task for {model_name} {obj_id} completed (placeholder)."
    except Model.DoesNotExist:
        logger.warning(f"Object {model_name} {obj_id} not found for image resizing.")
    except Exception as exc:
        logger.error(f"Error resizing image for {model_name} {obj_id}, field {field_name}: {str(exc)}")
        raise self.retry(exc=exc)
