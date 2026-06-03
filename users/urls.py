# -*- coding: utf-8 -*-
from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views
from .api import HRAlertHistoryViewSet
from .api_views import FCMTokenUpdateAPIView

app_name = "users"

router = DefaultRouter()
router.register(
    "api/v1/hr-alert-history",
    HRAlertHistoryViewSet,
    basename="hralerthistory",
)

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile/", views.profile_view, name="profile"),
    path("mobile/profile/", views.mobile_profile_view, name="mobile_profile"),
    path(
        "mobile/change-password/",
        views.mobile_password_change_view,
        name="mobile_password_change",
    ),
    path(
        "mobile/salary/<int:luong_id>/",
        views.mobile_salary_detail_view,
        name="mobile_salary_detail",
    ),
    path(
        "export/ly-lich/options/<int:nhan_vien_id>/",
        views.export_ly_lich_options_view,
        name="export-ly-lich-options",
    ),
    path(
        "export/ly-lich/<int:nhan_vien_id>/",
        views.export_ly_lich_pdf,
        name="export-ly-lich",
    ),
    path(
        "export/the-ten/<int:nhan_vien_id>/",
        views.export_the_ten_pdf,
        name="export-the-ten",
    ),
    path(
        "export/danh-sach-muc-tieu/<int:muc_tieu_id>/",
        views.export_danh_sach_nhan_su_muc_tieu_pdf,
        name="export-danh-sach-muc-tieu",
    ),
    path(
        "api/v1/users/fcm-token/",
        FCMTokenUpdateAPIView.as_view(),
        name="fcm_token_update",
    ),
]

urlpatterns += router.urls
