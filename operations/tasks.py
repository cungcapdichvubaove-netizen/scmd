# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro
=======
Security Command (SCMD) System
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
------------------------------
Infrastructure Layer: Operations Tasks.
"""

import logging
<<<<<<< HEAD
from io import BytesIO
from pathlib import Path
from datetime import timedelta

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError
from main.constants import OPERATIONS_NOTIFICATION_GROUPS

from operations.models import KiemTraQuanSo

logger = logging.getLogger(__name__)

IMAGE_COMPRESSION_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
IMAGE_COMPRESSION_MAX_DIMENSION = 1600
IMAGE_COMPRESSION_QUALITY = 80


def _image_format_from_name(name, fallback=None):
    suffix = Path(name or "").suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "JPEG"
    if suffix == ".png":
        return "PNG"
    if suffix == ".webp":
        return "WEBP"
    return fallback


def _compressed_derivative_name(name, derivative_suffix="display"):
    path = Path(name or "")
    suffix = path.suffix or ".jpg"
    stem = path.name[: -len(suffix)] if suffix else path.name
    derivative_name = f"{stem}.{derivative_suffix}{suffix}"
    if str(path.parent) in {"", "."}:
        return derivative_name
    return str(path.parent / derivative_name)


def _save_compressed_derivative(storage, source_name, data, *, derivative_suffix="display"):
    derivative_name = _compressed_derivative_name(source_name, derivative_suffix=derivative_suffix)
    if storage.exists(derivative_name):
        storage.delete(derivative_name)
    return storage.save(derivative_name, ContentFile(data))


def compress_uploaded_image_field(image_field, *, max_dimension=None, quality=None, derivative_suffix="display"):
    """Create a compressed derivative for an ImageField without touching evidence.

    Evidence photos are business/legal records. This utility intentionally does
    not overwrite the uploaded original. It writes a sidecar derivative only
    when explicitly called by an operator task or a future display/PDF pipeline.
    Automatic signal-driven compression is disabled until the product defines
    a retention policy for originals versus derived display images.
    """

    if not image_field or not getattr(image_field, "name", ""):
        return {"status": "skipped", "reason": "empty-field"}

    max_dimension = int(max_dimension or getattr(settings, "SCMD_IMAGE_MAX_DIMENSION", IMAGE_COMPRESSION_MAX_DIMENSION))
    quality = int(quality or getattr(settings, "SCMD_IMAGE_COMPRESSION_QUALITY", IMAGE_COMPRESSION_QUALITY))
    storage = image_field.storage
    name = image_field.name

    if not storage.exists(name):
        return {"status": "skipped", "reason": "missing-file", "name": name}

    original_size = storage.size(name)

    try:
        with storage.open(name, "rb") as source:
            with Image.open(source) as original_image:
                original_image.load()
                original_format = original_image.format
                original_dimensions = original_image.size
                target_format = _image_format_from_name(name, fallback=original_format)
                if target_format not in IMAGE_COMPRESSION_ALLOWED_FORMATS:
                    return {
                        "status": "skipped",
                        "reason": "unsupported-format",
                        "format": target_format,
                        "name": name,
                    }

                image = ImageOps.exif_transpose(original_image)
                resized = False
                if max(image.size) > max_dimension:
                    image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                    resized = True

                if target_format in {"JPEG", "WEBP"} and image.mode not in {"RGB", "L"}:
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    if "A" in image.getbands():
                        background.paste(image, mask=image.getchannel("A"))
                    else:
                        background.paste(image)
                    image = background

                output = BytesIO()
                save_kwargs = {"optimize": True}
                if target_format in {"JPEG", "WEBP"}:
                    save_kwargs["quality"] = max(1, min(quality, 95))
                if target_format == "JPEG":
                    save_kwargs["progressive"] = True
                image.save(output, format=target_format, **save_kwargs)
                compressed_bytes = output.getvalue()
    except UnidentifiedImageError:
        return {"status": "skipped", "reason": "not-an-image", "name": name}

    new_size = len(compressed_bytes)
    should_write = resized or new_size < original_size
    if not should_write:
        return {
            "status": "skipped",
            "reason": "already-optimized",
            "name": name,
            "original_size": original_size,
            "compressed_size": new_size,
            "dimensions": original_dimensions,
        }

    derivative_name = _save_compressed_derivative(
        storage,
        name,
        compressed_bytes,
        derivative_suffix=derivative_suffix,
    )
    return {
        "status": "compressed",
        "name": name,
        "derivative_name": derivative_name,
        "original_size": original_size,
        "compressed_size": new_size,
        "original_dimensions": original_dimensions,
        "compressed_dimensions": image.size,
        "resized": resized,
        "quality": quality,
        "original_preserved": True,
    }

=======
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

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

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

<<<<<<< HEAD

@shared_task(bind=True, max_retries=2)
def check_target_stability_daily_task(self):
    """
    Task chay hang ngay de kiem tra cac chi so bat thuong tai muc tieu.
    """
    try:
        from operations.application.attendance_use_cases import MonitorWeeklySwapRateUseCase

        tenant_id = settings.SCMD_ORGANIZATION_ID
        count = MonitorWeeklySwapRateUseCase.execute(tenant_id)

        return f"Stability check completed. Alerts triggered: {count}"
    except Exception as exc:
        logger.error("Error in stability monitoring task: %s", str(exc))
        raise self.retry(exc=exc)

=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_worker_heartbeat_task(self):
    """
<<<<<<< HEAD
    Task tu dong chay tren workers de cap nhat trang thai Alive.
    """
    from main.models import WorkerHeartbeat

    hostname = self.request.hostname or "unknown-worker"

    WorkerHeartbeat.objects.update_or_create(
        hostname=hostname,
        defaults={
            "is_active": True,
            "tenant_id": settings.SCMD_ORGANIZATION_ID,
        },
    )
    return f"Heartbeat updated for {hostname}"


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def monitor_worker_health_and_broadcast_task(self):
    """
    Task giam sat worker va broadcast trang thai tong the len bang dieu hanh.
    """
    from main.models import WorkerHeartbeat

    try:
        threshold = timezone.now() - timedelta(minutes=5)
        offline_workers = WorkerHeartbeat.objects.filter(
            last_ping__lt=threshold,
            is_active=True,
        )
        offline_workers.update(is_active=False)

        active_workers = WorkerHeartbeat.objects.filter(
            is_active=True
        ).values_list("hostname", flat=True)
        total_count = WorkerHeartbeat.objects.count()

        channel_layer = get_channel_layer()
        if channel_layer:
            for group in OPERATIONS_NOTIFICATION_GROUPS:
                async_to_sync(channel_layer.group_send)(
                    group,
                    {
                        "type": "worker.status",
                        "payload": {
                            "active_workers": list(active_workers),
                            "active_count": len(active_workers),
                            "total_count": total_count,
                            "timestamp": timezone.now().strftime("%H:%M:%S"),
                        },
                    },
                )

        return f"Health check completed. Active: {len(active_workers)}"
    except Exception as exc:
        logger.error("Error in worker health monitoring task: %s", str(exc))
        raise self.retry(exc=exc)

=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def operations_mark_expired_alive_checks(self):
    """
<<<<<<< HEAD
    Task quét và đánh dấu Alive Check quá hạn.
    """
    try:
        from operations.application.maintenance_use_cases import (
            ExpireAliveChecksUseCase,
        )

        result = ExpireAliveChecksUseCase.execute(
            now=timezone.now(),
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )
        return result["message"]
    except Exception as exc:
        logger.error("[Alive-Check-Cleanup] Loi khi quet qua han: %s", str(exc))
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def operations_auto_expire_alive_check(self, check_id):
    """
    Task đánh dấu một yêu cầu Alive Check là quá hạn sau timeout.
    """
    try:
        from operations.application.maintenance_use_cases import (
            AutoExpireAliveCheckUseCase,
        )

        result = AutoExpireAliveCheckUseCase.execute(
            check_id=check_id,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )
        return result["message"]
    except KiemTraQuanSo.DoesNotExist:
        logger.warning("[Alive-Check-Timeout] Khong tim thay ban ghi %s", check_id)
    except Exception as exc:
        logger.error(
            "[Alive-Check-Timeout] Loi xu ly ban ghi %s: %s",
            check_id,
            str(exc),
        )
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=3, acks_late=True)
def process_timesheet_async(self, cham_cong_id):
    """
    Task tính toán giờ công thực tế sau khi nhân viên check-out.
    """
    from operations.application.attendance_use_cases import CalculateWorkHoursUseCase
    from operations.models import ChamCong

    try:
        with transaction.atomic():
            cham_cong = ChamCong.objects.select_for_update().get(id=cham_cong_id)
            hours = CalculateWorkHoursUseCase.execute(cham_cong)
            from core.audit_context import allow_attendance_mutation

            cham_cong.thuc_lam_gio = hours
            with allow_attendance_mutation("TIMESHEET_PROCESSING_TASK"):
                cham_cong.save(update_fields=["thuc_lam_gio"])

            logger.info("Timesheet processed for ChamCong %s: %sh", cham_cong_id, hours)
            return hours
    except ChamCong.DoesNotExist:
        logger.error("ChamCong %s khong ton tai.", cham_cong_id)
    except Exception as exc:
        logger.error("Loi xu ly bang cong %s: %s", cham_cong_id, str(exc))
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def check_late_checkout_task(self):
    """
    Task quét các ca trực đã kết thúc nhưng nhân viên chưa check-out.
    """
    try:
        from operations.application.maintenance_use_cases import (
            FlagLateCheckoutUseCase,
        )

        result = FlagLateCheckoutUseCase.execute(
            now=timezone.now(),
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )
        return result["message"]
    except Exception as exc:
        logger.error("Error in check_late_checkout_task: %s", str(exc))
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def resize_image_async(self, app_label, model_name, obj_id, field_name):
    """Opt-in image derivative task; does not overwrite evidence originals."""
    try:
        model = apps.get_model(app_label, model_name)
        obj = model.objects.get(pk=obj_id)
        image_field = getattr(obj, field_name)
        result = compress_uploaded_image_field(image_field)
        logger.info(
            "Image derivative compression result for %s %s field %s: %s",
            model_name,
            obj_id,
            field_name,
            result,
        )
        return result
    except ObjectDoesNotExist:
        logger.warning("Object %s %s not found for image derivative task.", model_name, obj_id)
        return {"status": "skipped", "reason": "missing-object", "model": model_name, "object_id": obj_id}
    except Exception as exc:
        logger.error(
            "Error creating image derivative for %s %s, field %s: %s",
            model_name,
            obj_id,
            field_name,
            str(exc),
        )
=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        raise self.retry(exc=exc)
