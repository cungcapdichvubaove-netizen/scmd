import os


DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@scmd.local"
<<<<<<< HEAD
INSECURE_BOOTSTRAP_CREDENTIAL_VALUES = {
    "",
    "admin",
    "password",
    "123456",
    "changeme",
    "change-me",
    "change-this-admin-password",
    "change-this-seed-password",
    "local/dev only",
}


def _is_production_runtime():
    return os.getenv("DEBUG", "False").strip().lower() not in {"1", "true", "yes", "on"}


def _get_first_env(*keys):
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def _assert_not_insecure_default(name, value):
    if not _is_production_runtime():
        return value

    normalized = (value or "").strip()
    lowered = normalized.lower()
    if lowered in INSECURE_BOOTSTRAP_CREDENTIAL_VALUES or "change-this" in lowered or "please-change" in lowered:
        raise RuntimeError(
            f"{name} dang dung gia tri mac dinh/placeholder trong production. "
            "Hay cau hinh credential rieng qua bien moi truong truoc khi bootstrap."
        )
    return value


def get_admin_username():
    username = (
=======
DEFAULT_ADMIN_PASSWORD = "ScmdAdmin2026!"


def get_admin_username():
    return (
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        os.getenv("SCMD_ADMIN_USERNAME")
        or os.getenv("DJANGO_SUPERUSER_USERNAME")
        or DEFAULT_ADMIN_USERNAME
    )
<<<<<<< HEAD
    return _assert_not_insecure_default("SCMD_ADMIN_USERNAME/DJANGO_SUPERUSER_USERNAME", username)


def get_admin_email():
    email = (
=======


def get_admin_email():
    return (
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        os.getenv("SCMD_ADMIN_EMAIL")
        or os.getenv("DJANGO_SUPERUSER_EMAIL")
        or DEFAULT_ADMIN_EMAIL
    )
<<<<<<< HEAD
    if _is_production_runtime() and email == DEFAULT_ADMIN_EMAIL:
        raise RuntimeError(
            "SCMD_ADMIN_EMAIL/DJANGO_SUPERUSER_EMAIL dang dung email mac dinh admin@scmd.local trong production."
        )
    return email


def get_admin_password():
    password = _get_first_env("SCMD_ADMIN_PASSWORD", "DJANGO_SUPERUSER_PASSWORD")
    if password:
        return _assert_not_insecure_default("SCMD_ADMIN_PASSWORD/DJANGO_SUPERUSER_PASSWORD", password)
    raise RuntimeError(
        "Phải cấu hình SCMD_ADMIN_PASSWORD hoặc DJANGO_SUPERUSER_PASSWORD cho bootstrap admin."
=======


def get_admin_password():
    return (
        os.getenv("SCMD_ADMIN_PASSWORD")
        or os.getenv("DJANGO_SUPERUSER_PASSWORD")
        or DEFAULT_ADMIN_PASSWORD
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    )


def get_seed_password():
<<<<<<< HEAD
    password = _get_first_env(
        "SCMD_SEED_PASS",
        "SCMD_ADMIN_PASSWORD",
        "DJANGO_SUPERUSER_PASSWORD",
    )
    if password:
        return _assert_not_insecure_default("SCMD_SEED_PASS/SCMD_ADMIN_PASSWORD/DJANGO_SUPERUSER_PASSWORD", password)
    raise RuntimeError(
        "Phải cấu hình SCMD_SEED_PASS, SCMD_ADMIN_PASSWORD hoặc DJANGO_SUPERUSER_PASSWORD cho seed data."
=======
    return (
        os.getenv("SCMD_SEED_PASS")
        or os.getenv("SCMD_ADMIN_PASSWORD")
        or os.getenv("DJANGO_SUPERUSER_PASSWORD")
        or DEFAULT_ADMIN_PASSWORD
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    )
