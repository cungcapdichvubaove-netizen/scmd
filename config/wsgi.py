import os
from django.core.wsgi import get_wsgi_application

# Thiết lập file settings mặc định
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Tạo ứng dụng WSGI
application = get_wsgi_application()