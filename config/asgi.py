# file: config/asgi.py

import os
import django
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Import application từ config.routing sau khi django.setup()
from config.routing import application