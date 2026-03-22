# operations/consumers.py
# -*- coding: utf-8 -*-
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Xử lý kết nối WebSocket.
        """
        # --- SECURITY FIX: Chỉ cho phép User đã login ---
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.group_name = "notifications"
        
        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        """
        Ngắt kết nối an toàn.
        """
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def send_notification(self, event):
        """
        Nhận message từ Signal và đẩy xuống Client.
        """
        payload = event['payload']
        
        # Gửi dữ liệu JSON xuống trình duyệt
        await self.send(text_data=json.dumps(payload))