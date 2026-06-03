# file: operations/routing.py

from django.urls import re_path
# Sử dụng Consumer từ module notifications làm SSOT cho toàn hệ thống
from notifications import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]