from django.apps import AppConfig


class OperationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "operations"
    verbose_name = "2. Điều hành và giám sát"

    def ready(self):
        import operations.signals
