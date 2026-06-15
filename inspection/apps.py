from django.apps import AppConfig


<<<<<<< HEAD
class InspectionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inspection"
    verbose_name = "3. Thanh tra & giám sát"

    def ready(self):
=======
# inspection/apps.py
from django.apps import AppConfig

class InspectionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inspection'
    verbose_name = "3. THANH TRA & TUẦN TRA"

    def ready(self):
        # Nếu bạn có signals trong app này, hãy import chúng ở đây.
        # Ví dụ: import inspection.signals
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        pass
