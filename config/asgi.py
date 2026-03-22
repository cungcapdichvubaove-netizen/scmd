# file: config/asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path
from operations.consumers import NotificationConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Define routing directly here to avoid circular imports
websocket_urlpatterns = [
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})