# operations/signals.py
# -*- coding: utf-8 -*-

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from users.models import NhanVien
from .models import BaoCaoSuCo, ChamCong
from .tasks import process_timesheet_async, resize_image_async, process_new_incident_alert


# ==========================================================
# 1. AUTO CREATE PROFILE
# ==========================================================

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'nhanvien'):
        NhanVien.objects.create(
            user=instance,
            ho_ten=instance.username
        )


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    if hasattr(instance, 'nhanvien'):
        instance.nhanvien.save()


# ==========================================================
# 2. INCIDENT SIGNAL
# ==========================================================

@receiver(post_save, sender=BaoCaoSuCo)
def handle_su_co_changes(sender, instance, created, **kwargs):

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

    if created:

        process_new_incident_alert.delay(instance.id)

        try:
            channel_layer = get_channel_layer()

            target_name = (
                instance.muc_tieu.ten_muc_tieu
                if instance.muc_tieu
                else "Không xác định"
            )

            lat = None
            lng = None

            if instance.lat:
                lat = float(instance.lat)

            if instance.long:
                lng = float(instance.long)

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

            async_to_sync(channel_layer.group_send)(
                "notifications",
                {
                    "type": "send_notification",
                    "payload": payload
                }
            )

        except Exception as e:
            print("Incident WebSocket Error:", e)


# ==========================================================
# 3. ATTENDANCE SIGNAL (LIVE MAP)
# ==========================================================

@receiver(post_save, sender=ChamCong)
def broadcast_attendance(sender, instance, created, **kwargs):
    """
    Broadcast Check-in / Check-out realtime lên bản đồ
    """

    try:

        nhan_vien = instance.ca_truc.nhan_vien

        lat = instance.lat_check_in
        lng = instance.long_check_in

        if not lat or not lng:
            if instance.location_check_in:
                lat = instance.location_check_in.y
                lng = instance.location_check_in.x

        if not lat or not lng:
            return

        action = "CHECKIN"

        if instance.thoi_gian_check_out:
            action = "CHECKOUT"

        avatar_url = None

        if nhan_vien.anh_the:
            try:
                avatar_url = nhan_vien.anh_the.url
            except:
                pass

        channel_layer = get_channel_layer()

        payload = {
            "type": action,
            "id": instance.id,
            "user_name": nhan_vien.ho_ten,
            "avatar": avatar_url,
            "lat": float(lat),
            "lng": float(lng),
            "message": f"{nhan_vien.ho_ten} vừa {action.lower()}",
            "timestamp": (
                instance.thoi_gian_check_out.strftime("%H:%M:%S")
                if action == "CHECKOUT"
                else instance.thoi_gian_check_in.strftime("%H:%M:%S")
            )
        }

        async_to_sync(channel_layer.group_send)(
            "notifications",
            {
                "type": "send_notification",
                "payload": payload
            }
        )

    except Exception as e:
        print("Attendance WebSocket Error:", e)