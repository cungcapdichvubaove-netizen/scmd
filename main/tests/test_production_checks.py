# -*- coding: utf-8 -*-

from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from main.checks import check_production_security_settings


class ProductionSecurityChecksTest(SimpleTestCase):
    @patch.dict("os.environ", {"ENVIRONMENT": "development"}, clear=False)
    def test_check_passes_outside_production(self):
        self.assertEqual(check_production_security_settings(None), [])

    @patch.dict("os.environ", {"ENVIRONMENT": "production"}, clear=False)
    @override_settings(
        DEBUG=True,
        SECRET_KEY="django-insecure-local-dev-key",
        ALLOWED_HOSTS=["localhost", "app.example.com"],
        CORS_ALLOWED_ORIGINS=["http://localhost:3000"],
        CSRF_TRUSTED_ORIGINS=["http://localhost:8000"],
        SECURE_SSL_REDIRECT=False,
        SESSION_COOKIE_SECURE=False,
        CSRF_COOKIE_SECURE=False,
        ROOT_URLCONF="config.urls",
    )
    def test_insecure_production_settings_fail_with_expected_ids(self):
        errors = check_production_security_settings(None)
        error_ids = {error.id for error in errors}

        self.assertTrue(
            {"scmd.E001", "scmd.E002", "scmd.E003", "scmd.E005", "scmd.E006", "scmd.E007", "scmd.E008", "scmd.E012"}.issubset(error_ids)
        )

    @patch.dict("os.environ", {"ENVIRONMENT": "production"}, clear=False)
    @override_settings(
        DEBUG=False,
        SECRET_KEY="prod-secret-key-with-real-entropy-2026",
        ALLOWED_HOSTS=["app.example.com"],
        CORS_ALLOWED_ORIGINS=["https://app.example.com"],
        CSRF_TRUSTED_ORIGINS=["https://app.example.com"],
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        ROOT_URLCONF="main.tests.urls_without_media_auth",
    )
    def test_missing_internal_media_auth_route_fails_in_production(self):
        errors = check_production_security_settings(None)

        self.assertIn("scmd.E009", {error.id for error in errors})

    @patch.dict("os.environ", {"ENVIRONMENT": "production"}, clear=False)
    @override_settings(
        DEBUG=False,
        SECRET_KEY="prod-secret-key-with-real-entropy-2026",
        ALLOWED_HOSTS=["app.example.com", "api.example.com"],
        CORS_ALLOWED_ORIGINS=["https://app.example.com", "https://ops.example.com"],
        CSRF_TRUSTED_ORIGINS=["https://app.example.com", "https://ops.example.com"],
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        ROOT_URLCONF="config.urls",
    )
    def test_secure_production_settings_pass(self):
        self.assertEqual(check_production_security_settings(None), [])
