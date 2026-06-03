# -*- coding: utf-8 -*-
"""
Root URL configuration for SCMD Pro.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def logout_redirect_handler(request):
    """Handle admin logout safely for GET requests."""
    from django.contrib.auth import logout

    if request.user.is_authenticated:
        logout(request)
    return redirect("main:login")


urlpatterns = [
    path("admin/logout/", logout_redirect_handler, name="admin_logout_fix"),
    path("admin/", admin.site.urls),
    path(
        "sw.js",
        TemplateView.as_view(
            template_name="sw.js",
            content_type="application/javascript",
        ),
        name="sw.js",
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
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

admin.site.site_header = "SCMD Admin"
admin.site.site_title = "SCMD Technical Console"
admin.site.index_title = "Không gian quản trị kỹ thuật nội bộ"

handler404 = "main.views.handler404" if "main" in settings.INSTALLED_APPS else None
handler500 = "main.views.handler500" if "main" in settings.INSTALLED_APPS else None
