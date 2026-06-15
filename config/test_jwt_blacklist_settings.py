# -*- coding: utf-8 -*-
"""Settings regression tests for mobile JWT refresh-token revocation."""

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase
from datetime import timedelta


class JWTBlacklistSettingsTests(SimpleTestCase):
    def test_token_blacklist_app_is_installed(self):
        self.assertIn("rest_framework_simplejwt.token_blacklist", settings.INSTALLED_APPS)
        self.assertTrue(apps.is_installed("rest_framework_simplejwt.token_blacklist"))

    def test_refresh_token_lifetime_and_blacklist_are_explicit(self):
        self.assertIn("REFRESH_TOKEN_LIFETIME", settings.SIMPLE_JWT)
        self.assertIsInstance(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"], timedelta)
        self.assertTrue(settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"])
        self.assertTrue(settings.SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"])

    def test_jwt_signing_key_uses_dedicated_setting(self):
        self.assertTrue(hasattr(settings, "SIMPLE_JWT_SIGNING_KEY"))
        self.assertEqual(settings.SIMPLE_JWT["SIGNING_KEY"], settings.SIMPLE_JWT_SIGNING_KEY)
