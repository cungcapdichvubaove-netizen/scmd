# file: inventory/urls.py
from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('bao-cao-ton/', views.bao_cao_ton_kho, name='bao_cao_ton'),
    path('cong-cu-muc-tieu/', views.cong_cu_muc_tieu, name='cong_cu_muc_tieu'),
    
    # --- ĐƯỜNG DẪN IN ẤN (QUAN TRỌNG) ---
    path('phieu-nhap/<int:pk>/in/', views.chi_tiet_phieu_nhap, name='phieu_nhap_detail'),
    path('phieu-xuat/<int:pk>/in/', views.chi_tiet_phieu_xuat, name='phieu_xuat_detail'),
]