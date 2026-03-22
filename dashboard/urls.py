# file: dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # URL gốc của dashboard, trỏ về view dashboard_main
    path('', views.dashboard_main, name='main'),
]