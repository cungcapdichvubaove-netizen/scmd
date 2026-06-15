# -*- coding: utf-8 -*-
"""PWA delivery views for SCMD Pro.

The service worker must be served from the origin root and should not be
served with long-lived browser/proxy caching. Static asset caching is handled
inside the service worker itself.
"""

from django.conf import settings
from django.shortcuts import render


def service_worker(request):
    response = render(
        request,
        "sw.js",
        {
            "scmd_sw_version": getattr(settings, "SCMD_PRO_CACHE_VERSION", "scmd-pro"),
        },
        content_type="application/javascript",
    )
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    # Explicit even though /sw.js already permits root scope. It prevents
    # accidental scope regressions if the route is ever moved.
    response["Service-Worker-Allowed"] = "/"
    response["X-Content-Type-Options"] = "nosniff"
    return response
