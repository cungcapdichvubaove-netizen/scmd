# -*- coding: utf-8 -*-
"""Regression checks for SCMD Pro PWA contract.

These tests intentionally avoid browser automation. Lighthouse and installability
must still be verified in a real browser, but these checks prevent the most common
server-side regressions: invalid manifest, missing service worker route, and unsafe
service-worker cache rules.
"""
import json
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse


class PWAContractTests(SimpleTestCase):
    databases = {"default"}

    def _read_static(self, relative_path: str) -> str:
        return (Path(settings.BASE_DIR) / "static" / relative_path).read_text(encoding="utf-8")

    def test_manifest_is_installable_contract(self):
        manifest = json.loads(self._read_static("manifest.json"))

        self.assertEqual(manifest["name"], "SCMD Pro")
        self.assertEqual(manifest["short_name"], "SCMD Pro")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["orientation"], "portrait")
        self.assertEqual(manifest["start_url"], "/operations/mobile/dashboard/?source=pwa")
        self.assertEqual(manifest["id"], "/operations/mobile/")
        self.assertEqual(len(manifest["shortcuts"]), 3)
        self.assertEqual(
            {shortcut["url"] for shortcut in manifest["shortcuts"]},
            {
                "/operations/mobile/dashboard/?source=pwa-shortcut",
                "/operations/mobile/cham-cong/?source=pwa-shortcut",
                "/operations/mobile/bao-cao-su-co/?source=pwa-shortcut",
            },
        )

        icon_sizes = {icon["sizes"] for icon in manifest["icons"]}
        for expected_size in [
            "16x16",
            "32x32",
            "48x48",
            "72x72",
            "96x96",
            "128x128",
            "144x144",
            "152x152",
            "180x180",
            "192x192",
            "384x384",
            "512x512",
        ]:
            self.assertIn(expected_size, icon_sizes)

        icon_sources = {icon["src"] for icon in manifest["icons"]}
        for expected_source in [
            "/static/img/brand/favicon-16x16.png",
            "/static/img/brand/favicon-32x32.png",
            "/static/img/brand/favicon-48x48.png",
            "/static/img/brand/apple-touch-icon.png",
            "/static/img/brand/android-chrome-192x192.png",
            "/static/img/brand/android-chrome-512x512.png",
            "/static/img/brand/maskable-icon-512x512.png",
        ]:
            self.assertIn(expected_source, icon_sources)

        self.assertTrue(any(icon.get("purpose") == "maskable" for icon in manifest["icons"]))

    def test_service_worker_is_served_from_root_scope(self):
        response = self.client.get(reverse("sw.js"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/javascript", response["Content-Type"])
        self.assertEqual(response["Cache-Control"], "no-store, no-cache, must-revalidate, max-age=0")
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("SCMD_SW_VERSION", response.content.decode("utf-8"))

    def test_service_worker_does_not_cache_auth_or_mutation_endpoints(self):
        sw_template = (Path(settings.BASE_DIR) / "templates" / "sw.js").read_text(encoding="utf-8")
        self.assertIn("{% url 'admin:index' %}", sw_template)
        self.assertNotIn('"/admin/"', sw_template)

        sw = self.client.get(reverse("sw.js")).content.decode("utf-8")
        for blocked in [
            reverse("admin:index"),
            "/login/",
            "/logout/",
            "/operations/api/v1/mobile/checkin/",
            "/operations/api/v1/mobile/checkout/",
            "/inspection/mobile/ghi-nhan/",
        ]:
            self.assertIn(blocked, sw)

        self.assertIn('request.method !== "GET"', sw)
        self.assertIn("isAuthenticationLikeRequest", sw)
        self.assertIn("/media/", sw)
        self.assertIn("/password-reset/", sw)
        self.assertIn("safePrecache", sw)
        self.assertIn("Promise.allSettled", sw)
        self.assertIn("PUBLIC_NAVIGATION_CACHE_PATHS", sw)
        self.assertIn("allowCache: true", sw)
        self.assertIn("event.preloadResponse", sw)
        self.assertNotIn("localStorage", sw)
        self.assertNotIn("refresh_token", sw.lower())
        self.assertNotIn("access_token", sw.lower())

    def test_offline_page_exists_and_is_token_safe(self):
        offline = self._read_static("pwa/offline.html")
        self.assertIn("Bạn đang ngoại tuyến", offline)
        self.assertNotIn("JWT", offline.replace("Không lưu JWT", ""))
        self.assertNotIn("localStorage", offline)

    def test_pwa_register_clears_cache_on_auth_boundaries(self):
        script = self._read_static("pwa/pwa-register.js")
        self.assertIn("submit", script)
        self.assertIn("isAuthBoundaryUrl", script)
        self.assertIn("SCMD_PWA_CLEAR_CACHES", script)
        self.assertIn("window.caches.keys", script)
        self.assertNotIn("localStorage", script)

    def test_pwa_install_prompt_ux_is_available_without_forcing_install(self):
        script = self._read_static("pwa/pwa-register.js")
        self.assertIn("beforeinstallprompt", script)
        self.assertIn("deferredInstallPrompt", script)
        self.assertIn("promptEvent.prompt()", script)
        self.assertIn("appinstalled", script)
        self.assertIn("PWA_INSTALLED_COOKIE", script)
        self.assertIn("persistInstalledState()", script)
        self.assertIn("hasPersistedInstalledState()", script)
        self.assertIn("document.cookie", script)
        self.assertIn("android-app://", script)
        self.assertIn("display-mode: window-controls-overlay", script)
        self.assertIn("showIosInstallHint", script)
        self.assertIn("showUpdatePrompt", script)
        self.assertIn("wireServiceWorkerUpdates", script)
        self.assertIn("window.location.reload()", script)
        self.assertIn("Thêm SCMD Pro vào Màn hình chính", script)
        self.assertIn("/static/img/brand/android-chrome-192x192.png", script)
        self.assertIn("/static/img/brand/favicon-48x48.png", script)
        self.assertNotIn('icon.textContent = "S"', script)
        self.assertIn("shouldSuppressInstallPrompt", script)
        self.assertIn("operations\\/mobile\\/", script)
        self.assertIn("sessionStorage", script)
        self.assertNotIn("localStorage", script)
