import os
import django

# Thiết lập môi trường Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

def create_superuser():
    User = get_user_model()
    
    # Thông tin Admin mặc định
    # Bạn có thể đổi password ở đây hoặc dùng biến môi trường
    USERNAME = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
    EMAIL = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
    PASSWORD = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123') # <--- Mật khẩu mặc định là admin123

    if not User.objects.filter(username=USERNAME).exists():
        print(f"Đang tạo Superuser: {USERNAME}...")
        try:
            User.objects.create_superuser(USERNAME, EMAIL, PASSWORD)
            print(f"Tạo thành công! User: {USERNAME}, Pass: {PASSWORD}")
        except Exception as e:
            print(f"Lỗi khi tạo user: {e}")
    else:
        print("Superuser đã tồn tại. Bỏ qua.")

if __name__ == "__main__":
    create_superuser()