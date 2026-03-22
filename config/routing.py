# file: config/routing.py

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

# Import các file routing của từng app có sử dụng WebSocket
import notifications.routing

application = ProtocolTypeRouter({
    # Các request HTTP sẽ vẫn được xử lý bởi Django view như bình thường
    "http": get_asgi_application(),

    # Các kết nối WebSocket sẽ được xử lý tại đây
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                # Đây là nơi bạn sẽ thêm routing từ các app khác trong tương lai
                notifications.routing.websocket_urlpatterns
                # Ví dụ: + chat.routing.websocket_urlpatterns
            )
        )
    ),
})