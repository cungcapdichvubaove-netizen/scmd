# file: notifications/consumers.py

import json
import logging
<<<<<<< HEAD

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rolepermissions.checkers import has_role
from main.constants import OPERATIONS_NOTIFICATION_GROUPS

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    @database_sync_to_async
    def _has_any_role(self, roles):
        """Kiểm tra xem user có thuộc một trong các role quy định không."""
        return has_role(self.user, roles)

    async def connect(self):
        """
        Được gọi khi một kết nối WebSocket được thiết lập.
        Chỉ chấp nhận kết nối từ những user đã đăng nhập và là staff.
        """
        self.user = self.scope["user"]

        if not self.user.is_authenticated or not self.user.is_staff:
            await self.close()
            return

        # Refactor: Phân quyền group membership theo vai trò nghiệp vụ (P1)
        # Thay vì add toàn bộ staff vào các group nhạy cảm, ta lọc theo Role.
        self.active_groups = []

        # 1. Group cá nhân (Luôn join để nhận thông báo trực tiếp)
        self.user_notifications_group = f"notifications_{self.user.id}"
        self.active_groups.append(self.user_notifications_group)

        # 2. Operations Groups (Chỉ cho Ban Giám Đốc, Quản lý vùng, Đội trưởng, Kế toán)
        # Kế toán cần tham gia để đối soát giờ công/lương thực tế.
        if await self._has_any_role(["ban_giam_doc", "quan_ly_vung", "doi_truong", "ke_toan"]):
            self.active_groups.extend(OPERATIONS_NOTIFICATION_GROUPS)

        # 3. HR Groups (Chỉ cho Ban Giám Đốc, Nhân sự)
        if await self._has_any_role(["ban_giam_doc", "nhan_su"]):
            self.active_groups.append("hr_notifications")

        # 4. Payroll Groups (Chỉ cho Ban Giám Đốc, Kế toán)
        if await self._has_any_role(["ban_giam_doc", "ke_toan"]):
            self.active_groups.append("payroll_notifications")

        # Thực hiện đăng ký các group hợp lệ vào channel layer
        for group in self.active_groups:
            await self.channel_layer.group_add(group, self.channel_name)

        await self.accept()
        logger.info("User ID %s connected to notifications channel. Groups: %s", 
                    self.user.id, self.active_groups)
=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

    async def disconnect(self, close_code):
        """
        Được gọi khi kết nối WebSocket bị ngắt.
        """
<<<<<<< HEAD
        if hasattr(self, "active_groups"):
            for group in self.active_groups:
                await self.channel_layer.group_discard(group, self.channel_name)

        if self.user.is_authenticated:
            logger.info(
                "User ID %s disconnected from notifications channel.",
                self.user.id,
            )

    async def receive(self, text_data):
        """
        Giữ trống bề mặt receive; hiện tại server không cần nhận payload từ client.
=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        """
        pass

    async def send_notification(self, event):
        """
<<<<<<< HEAD
        Nhận sự kiện từ channel layer và chuyển tiếp payload xuống client.
        """
        notification_data = event.get("payload") or event.get("notification")
        msg_type = (
            notification_data.get("type")
            if isinstance(notification_data, dict)
            else "notification"
        )

        if not notification_data:
            logger.warning(
                "WebSocket event thieu data ('payload' hoac 'notification'): %s",
                event,
            )
            return

        await self.send(
            text_data=json.dumps(
                {
                    "type": msg_type,
                    "payload": notification_data,
                }
            )
        )

    async def payroll_alert(self, event):
        """
        Handler cho sự kiện payroll alert từ backend.
        """
        payload = event["payload"]

        await self.send(
            text_data=json.dumps(
                {
                    "type": "payroll_alert",
                    "payload": payload,
                }
            )
        )

    async def hr_alert(self, event):
        """
        Handler cho các cảnh báo nhân sự.
        """
        payload = event["payload"]

        await self.send(
            text_data=json.dumps(
                {
                    "type": "hr_alert",
                    "payload": payload,
                }
            )
        )

    async def operational_alert(self, event):
        """
        Handler cho các cảnh báo vận hành.
        """
        payload = event["payload"]

        await self.send(
            text_data=json.dumps(
                {
                    "type": "operational_alert",
                    "payload": payload,
                }
            )
        )

    async def worker_status(self, event):
        """
        Handler cập nhật trạng thái hạ tầng Celery workers cho bảng điều hành vận hành.
        """
        payload = event["payload"]

        await self.send(
            text_data=json.dumps(
                {
                    "type": "worker_status",
                    "payload": payload,
                }
            )
        )
=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
