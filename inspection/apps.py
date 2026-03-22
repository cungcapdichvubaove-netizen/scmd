from django.apps import AppConfig


# inspection/apps.py
from django.apps import AppConfig

class InspectionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inspection'
    verbose_name = "3. THANH TRA & TUẦN TRA"

    def ready(self):
        # Nếu bạn có signals trong app này, hãy import chúng ở đây.
        # Ví dụ: import inspection.signals
        pass
