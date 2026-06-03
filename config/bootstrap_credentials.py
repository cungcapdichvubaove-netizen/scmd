import os


DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@scmd.local"
DEFAULT_ADMIN_PASSWORD = "ScmdAdmin2026!"


def get_admin_username():
    return (
        os.getenv("SCMD_ADMIN_USERNAME")
        or os.getenv("DJANGO_SUPERUSER_USERNAME")
        or DEFAULT_ADMIN_USERNAME
    )


def get_admin_email():
    return (
        os.getenv("SCMD_ADMIN_EMAIL")
        or os.getenv("DJANGO_SUPERUSER_EMAIL")
        or DEFAULT_ADMIN_EMAIL
    )


def get_admin_password():
    return (
        os.getenv("SCMD_ADMIN_PASSWORD")
        or os.getenv("DJANGO_SUPERUSER_PASSWORD")
        or DEFAULT_ADMIN_PASSWORD
    )


def get_seed_password():
    return (
        os.getenv("SCMD_SEED_PASS")
        or os.getenv("SCMD_ADMIN_PASSWORD")
        or os.getenv("DJANGO_SUPERUSER_PASSWORD")
        or DEFAULT_ADMIN_PASSWORD
    )
