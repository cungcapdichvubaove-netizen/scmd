# file: notifications/consumers.py

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

# Lấy logger để ghi lại các hoạt động
logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        """
        Được gọi khi một kết nối WebSocket được thiết lập.
        Chỉ chấp nhận kết nối từ những user đã đăng nhập và là staff (quản lý).
        """
        self.user = self.scope["user"]

        # NÂNG CẤP 1: Kiểm tra quyền truy cập
        if not self.user.is_authenticated or not self.user.is_staff:
            # Từ chối kết nối nếu không phải là quản trị viên
            await self.close()
            return

        # Tạo một group chung cho tất cả các quản trị viên đang online
        self.room_group_name = 'admin_notifications'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        
        # NÂNG CẤP 2: Ghi log khi có kết nối thành công
        logger.info(f"User {self.user.username} connected to notifications channel.")

    async def disconnect(self, close_code):
        """
        Được gọi khi kết nối WebSocket bị ngắt.
        """
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        
        # NÂNG CẤP 2: Ghi log khi ngắt kết nối
        if self.user.is_authenticated:
            logger.info(f"User {self.user.username} disconnected from notifications channel.")

    async def receive(self, text_data):
        """
        Hàm này xử lý tin nhắn gửi TỪ trình duyệt ĐẾN server.
        Hiện tại chúng ta không dùng, nhưng đây là cấu trúc để sẵn sàng mở rộng sau này
        (ví dụ: client gửi tin nhắn 'đã xem' thông báo).
        """
        pass

    async def send_notification(self, event):
        """
        Hàm này nhận một sự kiện từ channel layer và gửi thông điệp
        đến client (trình duyệt) thông qua WebSocket.
        """
        # NÂNG CẤP 3: Gửi đi một cấu trúc JSON hoàn chỉnh thay vì chuỗi đơn giản
        notification_data = event['notification']

        # Gửi dữ liệu đã được cấu trúc tới WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'payload': notification_data
        }))