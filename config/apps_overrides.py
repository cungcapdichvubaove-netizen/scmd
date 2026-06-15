# -*- coding: utf-8 -*-
from django.contrib.auth.apps import AuthConfig
from django_celery_beat.apps import BeatConfig
from django_celery_results.apps import CeleryResultConfig

<<<<<<< HEAD

class CustomAuthConfig(AuthConfig):
    verbose_name = "9. Quản trị hệ thống"

    def ready(self):
        super().ready()

        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group

        user_model = get_user_model()
        user_model._meta.verbose_name = "Người dùng"
        user_model._meta.verbose_name_plural = "Người dùng"

        field_labels = {
            "username": "Tên đăng nhập",
            "first_name": "Tên",
            "last_name": "Họ",
            "email": "Email",
            "password": "Mật khẩu",
            "is_staff": "Nhân viên hệ thống",
            "is_superuser": "Quản trị tối cao",
            "is_active": "Đang hoạt động",
            "groups": "Nhóm quyền",
            "user_permissions": "Quyền riêng lẻ",
            "last_login": "Lần đăng nhập cuối",
            "date_joined": "Ngày tạo tài khoản",
        }

        for field_name, verbose_name in field_labels.items():
            try:
                user_model._meta.get_field(field_name).verbose_name = verbose_name
            except Exception:
                continue

        Group._meta.verbose_name = "Nhóm quyền"
        Group._meta.verbose_name_plural = "Nhóm quyền"


class CustomBeatConfig(BeatConfig):
    verbose_name = "10. Lịch trình tự động"


class CustomResultsConfig(CeleryResultConfig):
    verbose_name = "11. Kết quả tác vụ"
=======
class CustomAuthConfig(AuthConfig):
    verbose_name = "9. QUẢN TRỊ HỆ THỐNG (AUTH)"

class CustomBeatConfig(BeatConfig):
    verbose_name = "10. LỊCH TRÌNH TỰ ĐỘNG"

class CustomResultsConfig(CeleryResultConfig):
    verbose_name = "11. KẾT QUẢ TÁC VỤ"
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
