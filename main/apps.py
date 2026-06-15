from django.apps import AppConfig


class MainConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "main"
    verbose_name = "0. Cấu hình chung"

    def ready(self):
        # Rule 12.3: Register custom release checks for production safety
        from . import checks  # noqa
