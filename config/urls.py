# -*- coding: utf-8 -*-
"""
Root URL configuration for SCMD Pro.
"""

from types import MethodType

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from django.urls import include, path
from django.views.generic import RedirectView
from main import views as main_views
from main.pwa_views import service_worker
from main.admin_views import admin_global_search_view
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def _scmd_admin_has_permission(self, request):
    return main_views.DashboardRouter.user_can_access_admin_console(request.user)


admin.site.has_permission = MethodType(_scmd_admin_has_permission, admin.site)


def logout_redirect_handler(request):
    """Handle admin logout safely for GET requests."""
    from django.contrib.auth import logout

    if request.user.is_authenticated:
        logout(request)
    return redirect("main:login")


urlpatterns = [
    path(
        "favicon.ico",
        RedirectView.as_view(
            url=settings.STATIC_URL + "img/brand/favicon.ico",
            permanent=True,
        ),
    ),
    path("_internal/media-auth/", main_views.media_auth_view, name="internal_media_auth"),
    path("admin/logout/", logout_redirect_handler, name="admin_logout_fix"),
    path("admin/search/", admin_global_search_view, name="admin_global_search"),
    path("admin/", main_views.admin_root_gateway, name="admin_root_gateway"),
    path("admin/", admin.site.urls),
    path("sw.js", service_worker, name="sw.js"),
    path("api/schema/", staff_member_required(SpectacularAPIView.as_view()), name="schema"),
    path(
        "api/docs/",
        staff_member_required(SpectacularSwaggerView.as_view(url_name="schema")),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        staff_member_required(SpectacularRedocView.as_view(url_name="schema")),
        name="redoc",
    ),
    path("", include("main.urls")),
    path("users/", include("users.urls")),
    path("clients/", include("clients.urls")),
    path("operations/", include("operations.urls")),
    path("inspection/", include("inspection.urls")),
    path("accounting/", include("accounting.urls")),
    path("inventory/", include("inventory.urls")),
    path("workflow/", include("workflow.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("reports/", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]

admin.site.site_header = "Quản trị kỹ thuật SCMD"
admin.site.site_title = "Quản trị kỹ thuật SCMD"
admin.site.index_title = "Không gian quản trị kỹ thuật nội bộ"

handler404 = "main.views.handler404" if "main" in settings.INSTALLED_APPS else None
handler403 = "main.views.handler403" if "main" in settings.INSTALLED_APPS else None
handler500 = "main.views.handler500" if "main" in settings.INSTALLED_APPS else None
