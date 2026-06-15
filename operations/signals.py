# operations/signals.py
# -*- coding: utf-8 -*-
import logging

from django.db import transaction
<<<<<<< HEAD
from django.db.models.signals import post_delete, post_save
=======
from django.db.models.signals import post_save
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from django.dispatch import receiver
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
<<<<<<< HEAD
from main.constants import OPERATIONS_NOTIFICATION_GROUPS

from .cache_utils import invalidate_dashboard_cache
from .models import BaoCaoSuCo, ChamCong, PhanCongCaTruc
from .models import KiemTraQuanSo
from .tasks import process_timesheet_async, process_new_incident_alert
=======

from .models import BaoCaoSuCo, ChamCong
from .models_alive_check import KiemTraQuanSo
from .tasks import process_timesheet_async, resize_image_async, process_new_incident_alert
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

logger = logging.getLogger(__name__)


<<<<<<< HEAD
def _schedule_dashboard_cache_invalidation():
    transaction.on_commit(invalidate_dashboard_cache)


=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
def _safe_avatar_url(nhan_vien):
    if not nhan_vien or not nhan_vien.anh_the:
        return None
    try:
        return nhan_vien.anh_the.url
    except Exception:
        logger.exception("Unable to resolve avatar URL for employee %s", getattr(nhan_vien, "id", "unknown"))
        return None


# ==========================================================
# 2. INCIDENT SIGNAL
# ==========================================================

@receiver(post_save, sender=BaoCaoSuCo)
def handle_su_co_changes(sender, instance, created, **kwargs):
<<<<<<< HEAD
    _schedule_dashboard_cache_invalidation()

    # Evidence images are preserved as uploaded. Compression/derivative creation
    # is opt-in only until SCMD Pro defines an original-retention policy.
=======

    if instance.hinh_anh_1:
        resize_image_async.delay(
            'operations',
            'BaoCaoSuCo',
            instance.id,
            'hinh_anh_1'
        )

    if instance.hinh_anh_2:
        resize_image_async.delay(
            'operations',
            'BaoCaoSuCo',
            instance.id,
            'hinh_anh_2'
        )
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

    def broadcast_incident():
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                return

            target_name = instance.muc_tieu.ten_muc_tieu if instance.muc_tieu else "Không xác định"
            lat = float(instance.muc_tieu.vi_do) if instance.muc_tieu and instance.muc_tieu.vi_do else None
            lng = float(instance.muc_tieu.kinh_do) if instance.muc_tieu and instance.muc_tieu.kinh_do else None

            payload = {
                "type": "INCIDENT",
                "id": instance.id,
                "title": instance.tieu_de,
                "level": instance.muc_do,
                "lat": lat,
                "lng": lng,
                "message": f"Sự cố: {instance.tieu_de} tại {target_name}",
                "timestamp": instance.thoi_gian_phat_hien.strftime("%H:%M %d/%m")
            }

<<<<<<< HEAD
            for group in OPERATIONS_NOTIFICATION_GROUPS:
                async_to_sync(channel_layer.group_send)(
                    group,
                    {"type": "send_notification", "payload": payload}
                )
=======
            async_to_sync(channel_layer.group_send)(
                "war_room_staff", # Fix F13: Gửi tới nhóm War Room Staff
                {"type": "send_notification", "payload": payload}
            )
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        except Exception:
            logger.exception("Incident WebSocket broadcast failed for incident %s", instance.id)

    if created:
<<<<<<< HEAD
        transaction.on_commit(lambda: process_new_incident_alert.delay(instance.id))
=======
        process_new_incident_alert.delay(instance.id)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        transaction.on_commit(broadcast_incident)


# ==========================================================
# 3. ATTENDANCE SIGNAL (LIVE MAP)
# ==========================================================

@receiver(post_save, sender=ChamCong)
def broadcast_attendance(sender, instance, created, **kwargs):
    """
    Broadcast Check-in / Check-out realtime lên bản đồ
    """
<<<<<<< HEAD
    _schedule_dashboard_cache_invalidation()
    is_checkout = bool(instance.thoi_gian_check_out)

    # Check-in/out photos are evidence originals; do not auto-compress or
    # overwrite them from a post_save hook.

=======
    is_checkout = bool(instance.thoi_gian_check_out)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    if not created and not is_checkout:
        return
    
    def broadcast_attendance_socket():
        try:
            ca_truc = instance.ca_truc
            nhan_vien = getattr(ca_truc, 'nhan_vien', None) if ca_truc else None
            if not nhan_vien: 
                return

            # Safe extraction of coordinates
            point = instance.location_check_out if is_checkout else instance.location_check_in
            lat = point.y if point else getattr(instance, 'lat_check_in', 0.0)
            lng = point.x if point else getattr(instance, 'long_check_in', 0.0)

            if not lat or not lng: 
                return

            action = "CHECKOUT" if is_checkout else "CHECKIN"
            avatar_url = _safe_avatar_url(nhan_vien)

            channel_layer = get_channel_layer()
            if not channel_layer: 
                return

            payload = {
                "type": action,
                "id": instance.id,
                "user_name": nhan_vien.ho_ten,
                "avatar": avatar_url,
                "lat": float(lat) if lat else 0.0,
                "lng": float(lng) if lng else 0.0,
                "message": f"{nhan_vien.ho_ten} vừa {action.lower()}",
                "timestamp": (
                    instance.thoi_gian_check_out.strftime("%H:%M:%S")
                    if is_checkout
                    else instance.thoi_gian_check_in.strftime("%H:%M:%S")
                )
            }

<<<<<<< HEAD
            for group in OPERATIONS_NOTIFICATION_GROUPS:
                async_to_sync(channel_layer.group_send)(
                    group,
                    {"type": "send_notification", "payload": payload}
                )
=======
            async_to_sync(channel_layer.group_send)(
                "war_room_staff", # Fix F13: Gửi tới nhóm War Room Staff
                {"type": "send_notification", "payload": payload}
            )
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        except Exception:
            logger.exception("Attendance WebSocket broadcast failed for attendance %s", instance.id)

    transaction.on_commit(broadcast_attendance_socket)


# ==========================================================
# 4. ALIVE CHECK MONITORING
# ==========================================================

@receiver(post_save, sender=KiemTraQuanSo)
def handle_alive_check_broadcast(sender, instance, created, **kwargs):
    """
    Broadcast cảnh báo khi Alive Check vi phạm (Sai vị trí hoặc Quá hạn).
    """
    if instance.trang_thai in ['MISSED', 'LATE']:
        def broadcast_alert():
            try:
                channel_layer = get_channel_layer()
                if not channel_layer:
                    return

                payload = {
                    "type": "ALIVE_CHECK_ALERT",
                    "id": str(instance.id),
                    "status": instance.trang_thai,
                    "nhan_vien": instance.ca_truc.nhan_vien.ho_ten,
                    "muc_tieu": instance.ca_truc.vi_tri_chot.muc_tieu.ten_muc_tieu,
                    "message": f"Vi phạm Alive Check: {instance.ca_truc.nhan_vien.ho_ten} ({instance.get_trang_thai_display()})",
                    "timestamp": timezone.now().strftime("%H:%M:%S")
                }
<<<<<<< HEAD
                for group in OPERATIONS_NOTIFICATION_GROUPS:
                    async_to_sync(channel_layer.group_send)(
                        group,
                        {"type": "send_notification", "payload": payload}
                    )
=======
                async_to_sync(channel_layer.group_send)(
                    "war_room_staff",
                    {"type": "send_notification", "payload": payload}
                )
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            except Exception:
                logger.exception("AliveCheck WebSocket broadcast failed for check %s", instance.id)

        transaction.on_commit(broadcast_alert)
<<<<<<< HEAD


@receiver(post_save, sender=PhanCongCaTruc)
def invalidate_dashboard_on_shift_assignment_change(sender, instance, created, **kwargs):
    _schedule_dashboard_cache_invalidation()


@receiver(post_delete, sender=PhanCongCaTruc)
@receiver(post_delete, sender=ChamCong)
@receiver(post_delete, sender=BaoCaoSuCo)
def invalidate_dashboard_on_delete(sender, instance, **kwargs):
    _schedule_dashboard_cache_invalidation()
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
