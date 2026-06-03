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

        # Tham gia vào các group thông báo
        self.war_room_group = 'war_room_staff'
        self.hr_group = 'hr_notifications'
        self.user_notifications_group = f'notifications_{self.user.id}' # Nhóm thông báo cá nhân cho staff
        
        await self.channel_layer.group_add(
            self.war_room_group,
            self.channel_name
        )
        # Staff cũng có thể nhận thông báo cá nhân (ví dụ: Alive Check Request)
        await self.channel_layer.group_add(
            self.user_notifications_group,
            self.channel_name
        )
        await self.channel_layer.group_add(
            self.hr_group,
            self.channel_name
        )

        await self.accept()
        
        # NÂNG CẤP 2: Ghi log khi có kết nối thành công
        logger.info(f"User {self.user.username} connected to notifications channel.")

    async def disconnect(self, close_code):
        """
        Được gọi khi kết nối WebSocket bị ngắt.
        """
        if hasattr(self, 'war_room_group'):
            await self.channel_layer.group_discard(
                self.war_room_group,
                self.channel_name
            )
        if hasattr(self, 'user_notifications_group'):
            await self.channel_layer.group_discard(
                self.user_notifications_group,
                self.channel_name
            )
        if hasattr(self, 'war_room_group'):
            await self.channel_layer.group_discard(
                self.war_room_group,
                self.channel_name
            )
        if hasattr(self, 'hr_group'):
            await self.channel_layer.group_discard(
                self.hr_group,
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
        # NÂNG CẤP 3: Gửi đi một cấu trúc JSON hoàn chỉnh
        # Fix F06: Hỗ trợ cả 'payload' (từ operations) và 'notification' (Legacy) để đảm bảo SSOT
        notification_data = event.get('payload') or event.get('notification')
        msg_type = notification_data.get('type') if isinstance(notification_data, dict) else 'notification'

        if not notification_data:
            logger.warning(f"WebSocket event thiếu data ('payload' hoặc 'notification'): {event}")
            return

        # Gửi dữ liệu đã được cấu trúc tới WebSocket
        await self.send(text_data=json.dumps({
            'type': msg_type,
            'payload': notification_data
        }))

    async def payroll_alert(self, event):
        """
        Handler cho sự kiện 'payroll.alert' từ AuditPayrollUseCase.
        Chuyển tiếp payload tới client qua WebSocket.
        """
        payload = event['payload']
        
        await self.send(text_data=json.dumps({
            'type': 'payroll_alert',
            'payload': payload
        }))

    async def hr_alert(self, event):
        """
        Handler cho các cảnh báo nhân sự (HR Alerts).
        Chuyển tiếp payload tới client qua WebSocket.
        """
        payload = event['payload']
        
        await self.send(text_data=json.dumps({
            'type': 'hr_alert',
            'payload': payload
        }))

    async def operational_alert(self, event):
        """
        Handler cho các cảnh báo vận hành (Stability/Incident alerts).
        """
        payload = event['payload']
        
        await self.send(text_data=json.dumps({
            'type': 'operational_alert',
            'payload': payload
        }))

    async def worker_status(self, event):
        """
        Handler cập nhật trạng thái hạ tầng Celery Workers cho War Room.
        """
        payload = event['payload']
        
        await self.send(text_data=json.dumps({
            'type': 'worker_status',
            'payload': payload
        }))