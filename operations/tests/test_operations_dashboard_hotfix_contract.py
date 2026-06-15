# -*- coding: utf-8 -*-
"""Regression contract tests for operations dashboard hotfix."""

import os
import tempfile
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError

from django.test import SimpleTestCase, override_settings

from operations.application.dashboard_use_cases import (
    GetOperationsDashboardUseCase,
    MAX_ACTIVE_MARKERS,
    MAX_INCIDENT_MARKERS,
    MAX_RECENT_ACTIVITY,
)
from operations.cache_utils import build_dashboard_cache_key


class OperationsDashboardHotfixContractTest(SimpleTestCase):
    def test_live_dashboard_path_does_not_use_date_lookup(self):
        source = open("operations/application/dashboard_use_cases.py", encoding="utf-8").read()

        self.assertNotIn("thoi_gian_check_in" + "__date", source)
        self.assertIn("thoi_gian_check_in__gte=start_at", source)
        self.assertIn("thoi_gian_check_in__lt=end_at", source)

    def test_response_lists_are_capped_by_contract(self):
        self.assertEqual(MAX_ACTIVE_MARKERS, 300)
        self.assertEqual(MAX_INCIDENT_MARKERS, 100)
        self.assertEqual(MAX_RECENT_ACTIVITY, 20)

        source = open("operations/application/dashboard_use_cases.py", encoding="utf-8").read()
        self.assertIn("[:MAX_ACTIVE_MARKERS]", source)
        self.assertIn("[:MAX_INCIDENT_MARKERS]", source)
        self.assertIn("event_stream[:MAX_RECENT_ACTIVITY]", source)

    def test_coordinate_guard_rejects_missing_non_finite_and_out_of_range_values(self):
        valid = GetOperationsDashboardUseCase._valid_lat_lng(10.762622, 106.660172)
        self.assertEqual(valid, (10.762622, 106.660172))
        self.assertIsNone(GetOperationsDashboardUseCase._valid_lat_lng(None, 106.660172))
        self.assertIsNone(GetOperationsDashboardUseCase._valid_lat_lng(10.762622, None))
        self.assertIsNone(GetOperationsDashboardUseCase._valid_lat_lng(float("nan"), 106.660172))
        self.assertIsNone(GetOperationsDashboardUseCase._valid_lat_lng(91, 106.660172))
        self.assertIsNone(GetOperationsDashboardUseCase._valid_lat_lng(10.762622, 181))

    def test_api_permission_uses_dashboard_router_ssot_and_no_store_response(self):
        source = open("operations/api_views.py", encoding="utf-8").read()

        self.assertIn('DashboardRouter.user_can_access(request.user, "operations:dashboard_vanhanh")', source)
        self.assertNotIn('has_role(request.user, ["ban_giam_doc"', source)
        self.assertIn('response["Cache-Control"] = "no-store"', source)

    def test_service_worker_keeps_live_dashboard_api_network_only(self):
        source = open("templates/sw.js", encoding="utf-8").read()
        network_only_block = source.split("const NETWORK_ONLY_PREFIXES = [", 1)[1].split("];", 1)[0]
        cacheable_block = source.split("const CACHEABLE_API_PREFIXES = [", 1)[1].split("];", 1)[0]

        live_api_path = "/operations/api/dashboard/data/"
        self.assertIn(live_api_path, network_only_block)
        self.assertNotIn(live_api_path, cacheable_block)

    def test_recent_activity_is_capped_only_after_checkin_incident_merge_sort(self):
        events = []
        for index in range(MAX_RECENT_ACTIVITY + 5):
            GetOperationsDashboardUseCase._append_event(
                events,
                {
                    "kind": "checkin",
                    "timestamp": f"2026-06-13T08:{index:02d}:00+07:00",
                },
            )

        self.assertEqual(len(events), MAX_RECENT_ACTIVITY + 5)

        source = open("operations/application/dashboard_use_cases.py", encoding="utf-8").read()
        append_event_block = source.split("def _append_event(event_stream, event):", 1)[1].split("@staticmethod", 1)[0]
        self.assertNotIn("len(event_stream) >= MAX_RECENT_ACTIVITY", append_event_block)
        self.assertIn("event_stream.sort", source)
        self.assertIn("event_stream[:MAX_RECENT_ACTIVITY]", source)

    def test_tile_url_is_configured_by_settings_and_template_dataset(self):
        settings_source = open("config/settings.py", encoding="utf-8").read()
        template_source = open("operations/templates/operations/dashboard_vanhanh.html", encoding="utf-8").read()
        js_source = open("static/js/operations_dashboard_live.js", encoding="utf-8").read()

        self.assertIn("SCMD_MAP_TILE_URL", settings_source)
        self.assertIn("data-tile-url", template_source)
        self.assertIn("root.dataset.tileUrl", js_source)
        self.assertNotIn("tile." + "openstreetmap.org", js_source)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    @patch("operations.cache_utils.has_role")
    def test_global_cache_scope_can_be_shared_across_bgd_users(self, mock_has_role):
        mock_has_role.side_effect = lambda user, role: role == "ban_giam_doc"
        user_a = SimpleNamespace(id=1, is_superuser=False, is_staff=False)
        user_b = SimpleNamespace(id=2, is_superuser=False, is_staff=False)

        key_a = build_dashboard_cache_key(user=user_a, target_date="2026-06-13", muc_tieu_id=None, tenant_id="org-1")
        key_b = build_dashboard_cache_key(user=user_b, target_date="2026-06-13", muc_tieu_id=None, tenant_id="org-1")

        self.assertEqual(key_a, key_b)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    @patch("operations.cache_utils.SiteVisibilityPolicy.managed_sites")
    @patch("operations.cache_utils.has_role")
    def test_scoped_cache_scope_depends_on_resolved_target_ids(self, mock_has_role, mock_managed_sites):
        mock_has_role.side_effect = lambda user, role: role == "quan_ly_vung"

        class FakeManagedSites:
            def __init__(self, ids):
                self.ids = ids

            def order_by(self, *_args):
                return self

            def values_list(self, *_args, **_kwargs):
                return self.ids

        user_a = SimpleNamespace(id=1, is_superuser=False, is_staff=False)
        user_b = SimpleNamespace(id=2, is_superuser=False, is_staff=False)
        mock_managed_sites.side_effect = [FakeManagedSites([10, 11]), FakeManagedSites([12])]

        key_a = build_dashboard_cache_key(user=user_a, target_date="2026-06-13", muc_tieu_id=None, tenant_id="org-1")
        key_b = build_dashboard_cache_key(user=user_b, target_date="2026-06-13", muc_tieu_id=None, tenant_id="org-1")

        self.assertNotEqual(key_a, key_b)


class ReleaseHygieneAndGovernanceContractTest(SimpleTestCase):
    def test_build_clean_source_zip_excludes_virtualenv_directories(self):
        from scripts.build_clean_source_zip import should_include

        self.assertFalse(should_include(Path("venv/pyvenv.cfg")))
        self.assertFalse(should_include(Path(".venv/pyvenv.cfg")))
        self.assertFalse(should_include(Path("env/pyvenv.cfg")))
        self.assertFalse(should_include(Path("node_modules/package/index.js")))
        self.assertFalse(should_include(Path("staticfiles/admin/app.css")))
        self.assertFalse(should_include(Path("media/private/evidence.jpg")))
        self.assertFalse(should_include(Path("app/__pycache__/models.cpython-312.pyc")))
        self.assertFalse(should_include(Path("app/debug.log")))
        self.assertFalse(should_include(Path(".env")))
        self.assertFalse(should_include(Path("db.sqlite3")))
        self.assertFalse(should_include(Path("celerybeat-schedule")))
        self.assertFalse(should_include(Path("tmp-edge-profile/Default/Preferences")))
        self.assertFalse(should_include(Path("htmlcov/index.html")))
        self.assertFalse(should_include(Path(".pytest_cache/v/cache/nodeids")))

    def test_release_contract_check_fails_fast_on_virtualenv_artifact(self):
        from scripts import release_contract_check

        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)
                Path("venv/Scripts").mkdir(parents=True)
                Path("venv/Scripts/python.exe").write_text("", encoding="utf-8")
                violations = release_contract_check.check_forbidden_release_artifacts()
            finally:
                os.chdir(old_cwd)

        self.assertTrue(any("venv" in item and "Virtualenv detected" in item for item in violations))

    def test_nginx_release_contract_headers_and_gzip_are_present(self):
        source = Path("nginx/default.conf").read_text(encoding="utf-8")

        self.assertIn("gzip on;", source)
        self.assertIn("gzip_vary on;", source)
        self.assertIn("gzip_comp_level 5;", source)
        self.assertIn("gzip_min_length 1024;", source)
        self.assertIn("gzip_types text/plain text/css text/javascript application/javascript application/json application/xml image/svg+xml;", source)
        self.assertIn("gzip_static on;", source)
        self.assertIn("Cache-Control \"public, max-age=2592000, immutable\"", source)
        self.assertIn("Cache-Control \"private, no-store\"", source)
        self.assertIn("auth_request /_internal/media-auth/?uri=$request_uri;", source)
        self.assertIn("map $http_upgrade $connection_upgrade", source)
        self.assertIn("proxy_set_header Connection $connection_upgrade;", source)
        self.assertIn("proxy_set_header X-Real-IP $remote_addr;", source)
        self.assertIn("proxy_read_timeout 60s;", source)

    def test_profile_ops_dashboard_uses_capture_context_and_does_not_mutate_debug(self):
        source = Path("operations/management/commands/profile_ops_dashboard.py").read_text(encoding="utf-8")

        self.assertIn("CaptureQueriesContext(connection)", source)
        self.assertNotIn("settings.DEBUG =", source)
        self.assertIn("--max-queries", source)
        self.assertIn("--max-ms", source)
        self.assertIn("--json", source)
        self.assertIn("duplicate_sql_patterns", source)
        self.assertIn("slow_sql", source)

    @patch("operations.management.commands.profile_ops_dashboard.GetOperationsDashboardUseCase.execute", return_value={})
    @patch("operations.management.commands.profile_ops_dashboard.Command._ensure_user_schema_ready")
    @patch("operations.management.commands.profile_ops_dashboard.Command._get_user_model")
    def test_profile_ops_dashboard_fails_when_threshold_is_exceeded(self, mock_get_user_model, _mock_schema_ready, _mock_execute):
        class FakeCaptureQueriesContext:
            def __init__(self, _connection):
                self.captured_queries = [
                    {"sql": "SELECT * FROM operations_chamcong WHERE id = 1", "time": "0.001"},
                ]

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

        mock_get_user_model.return_value.objects.filter.return_value.first.return_value = SimpleNamespace(username="admin_profile")

        with patch("operations.management.commands.profile_ops_dashboard.CaptureQueriesContext", FakeCaptureQueriesContext):
            with self.assertRaises(CommandError) as raised:
                call_command(
                    "profile_ops_dashboard",
                    target_date="2026-06-14",
                    max_queries=0,
                    max_ms=999999,
                    as_json=True,
                    stdout=StringIO(),
                )

        self.assertIn("query_count=1 vượt max_queries=0", str(raised.exception))
