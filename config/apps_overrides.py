# -*- coding: utf-8 -*-
from django.contrib.auth.apps import AuthConfig
from django_celery_beat.apps import BeatConfig
from django_celery_results.apps import CeleryResultConfig

class CustomAuthConfig(AuthConfig):
    verbose_name = "9. QUẢN TRỊ HỆ THỐNG (AUTH)"

class CustomBeatConfig(BeatConfig):
    verbose_name = "10. LỊCH TRÌNH TỰ ĐỘNG"

class CustomResultsConfig(CeleryResultConfig):
    verbose_name = "11. KẾT QUẢ TÁC VỤ"