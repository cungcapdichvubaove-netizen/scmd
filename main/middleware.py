# -*- coding: utf-8 -*-
"""Dev/test-only performance instrumentation for dashboard/admin surfaces."""

from __future__ import annotations

import logging
import time

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test.utils import CaptureQueriesContext


logger = logging.getLogger(__name__)


class AccessDeniedExperienceMiddleware:
    """Render a friendly HTML 403 page for shell navigation and direct URLs.

    JSON, DRF, and XMLHttpRequest clients must keep their native 403 payloads.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, PermissionDenied):
            return None
        if not self._should_render_html_forbidden(request):
            return None

        from main.views import handler403

        return handler403(request, exception)

    @staticmethod
    def _should_render_html_forbidden(request) -> bool:
        if request.path.startswith("/api/"):
            return False
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return False

        accepted = request.headers.get("Accept", "")
        return not accepted or "text/html" in accepted or "*/*" in accepted


class DashboardPerformanceInstrumentationMiddleware:
    """Emit lightweight per-request metrics for dashboard/admin shells.

    The middleware is inert unless explicitly enabled through settings or DEBUG.
    It targets only internal shell surfaces and adds response headers plus a
    compact log line with the slowest SQL statements.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self._is_enabled() or not self._is_profiled_path(request.path):
            return self.get_response(request)

        start = time.perf_counter()
        with CaptureQueriesContext(connection) as captured:
            response = self.get_response(request)
            render_started = time.perf_counter()
            if hasattr(response, "render") and callable(response.render) and not getattr(response, "is_rendered", True):
                response = response.render()
            render_ms = (time.perf_counter() - render_started) * 1000

        total_ms = (time.perf_counter() - start) * 1000
        sql_ms = sum(float(query.get("time", 0) or 0) for query in captured.captured_queries) * 1000
        query_count = len(captured)
        top_slow_queries = sorted(
            captured.captured_queries,
            key=lambda query: float(query.get("time", 0) or 0),
            reverse=True,
        )[:10]

        response["X-SCMD-Query-Count"] = str(query_count)
        response["X-SCMD-SQL-Time-Ms"] = f"{sql_ms:.2f}"
        response["X-SCMD-Render-Time-Ms"] = f"{render_ms:.2f}"
        response["X-SCMD-Total-Time-Ms"] = f"{total_ms:.2f}"

        logger.info(
            "SCMD perf path=%s status=%s queries=%s sql_ms=%.2f render_ms=%.2f total_ms=%.2f slow=%s",
            request.path,
            getattr(response, "status_code", ""),
            query_count,
            sql_ms,
            render_ms,
            total_ms,
            [
                {
                    "time_ms": round(float(query.get("time", 0) or 0) * 1000, 2),
                    "sql": " ".join(query.get("sql", "").split())[:240],
                }
                for query in top_slow_queries
            ],
        )
        return response

    @staticmethod
    def _is_enabled() -> bool:
        return bool(
            getattr(settings, "SCMD_PERF_INSTRUMENTATION", False)
            or getattr(settings, "DEBUG", False)
        )

    @staticmethod
    def _is_profiled_path(path: str) -> bool:
        prefixes = getattr(
            settings,
            "SCMD_PERF_INSTRUMENTATION_PATH_PREFIXES",
            ("/admin/", "/dashboard/", "/operations/", "/mobile/"),
        )
        return any(path.startswith(prefix) for prefix in prefixes)
