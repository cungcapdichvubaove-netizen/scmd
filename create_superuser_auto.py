import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

from config.bootstrap_credentials import (
    get_admin_email,
    get_admin_password,
    get_admin_username,
)


def create_superuser():
    User = get_user_model()

    username = get_admin_username()
    email = get_admin_email()
    password = get_admin_password()

    try:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_superuser": True,
                "is_staff": True,
                "is_active": True,
            },
        )
        user.email = email
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.set_password(password)
        user.save()

        action = "Tao" if created else "Dong bo"
        print(f"{action} tai khoan quan tri chuan: {username}")
        print(f"Email: {email}")
        print(f"Password: {password}")
    except Exception as exc:
        print(f"Loi khi dong bo admin user: {exc}")


if __name__ == "__main__":
    create_superuser()
