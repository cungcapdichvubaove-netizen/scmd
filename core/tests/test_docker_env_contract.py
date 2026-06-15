# -*- coding: utf-8 -*-
"""Regression tests for Docker/PostGIS/Redis environment contract."""

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

from django.test import SimpleTestCase


BASE_DIR = Path(__file__).resolve().parents[2]


class DockerEnvContractTest(SimpleTestCase):
    def _run_settings_import(self, *, database_url, redis_url="redis://redis:6379/0"):
        env = os.environ.copy()
        env.update(
            {
                "DJANGO_SETTINGS_MODULE": "config.settings",
                "PYTHONPATH": str(BASE_DIR),
                "DEBUG": "True",
                "SCMD_DOCKER_COMPOSE": "production",
                "SCMD_ORGANIZATION_ID": "00000000-0000-0000-0000-000000000001",
                "SECRET_KEY": "unit-test-secret-key-not-a-placeholder",
                "SIMPLE_JWT_SIGNING_KEY": "unit-test-jwt-signing-key-not-a-placeholder",
                "FIELD_ENCRYPTION_KEY": "unit-test-field-encryption-key-not-a-placeholder",
                "EXCEL_EXPORT_PASSWORD": "unit-test-export-password-not-a-placeholder",
                "SQL_DATABASE": "scmd_pro",
                "SQL_USER": "scmd_user",
                "SQL_PASSWORD": "scmd_local_password_2026",
            }
        )
        if redis_url is None:
            env.pop("REDIS_URL", None)
        else:
            env["REDIS_URL"] = redis_url
        if database_url is None:
            env.pop("DATABASE_URL", None)
        else:
            env["DATABASE_URL"] = database_url

        code = dedent(
            """
            import config.settings as settings
            print(settings.DATABASES['default']['ENGINE'])
            print(settings.REDIS_URL)
            """
        )
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=BASE_DIR,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )

    def test_docker_prod_missing_database_url_fails_fast(self):
        result = self._run_settings_import(database_url=None)

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("ImproperlyConfigured", combined)
        self.assertIn("DATABASE_URL", combined)

    def test_docker_prod_sqlite_database_url_is_forbidden(self):
        result = self._run_settings_import(database_url="sqlite:///db.sqlite3")

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("ImproperlyConfigured", combined)
        self.assertIn("SQLite", combined)

    def test_docker_prod_localhost_database_url_is_forbidden(self):
        result = self._run_settings_import(
            database_url="postgis://scmd_user:scmd_local_password_2026@localhost:5432/scmd_pro"
        )

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("ImproperlyConfigured", combined)
        self.assertIn("host 'db'", combined)


    def test_docker_prod_missing_redis_url_fails_fast(self):
        result = self._run_settings_import(
            database_url="postgis://scmd_user:scmd_local_password_2026@db:5432/scmd_pro",
            redis_url=None,
        )

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("ImproperlyConfigured", combined)
        self.assertIn("REDIS_URL", combined)

    def test_docker_prod_localhost_redis_url_is_forbidden(self):
        result = self._run_settings_import(
            database_url="postgis://scmd_user:scmd_local_password_2026@db:5432/scmd_pro",
            redis_url="redis://localhost:6379/0",
        )

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("ImproperlyConfigured", combined)
        self.assertIn("host 'redis'", combined)

    def test_docker_prod_postgis_and_redis_service_hosts_are_accepted(self):
        result = self._run_settings_import(
            database_url="postgis://scmd_user:scmd_local_password_2026@db:5432/scmd_pro",
            redis_url="redis://redis:6379/0",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("django.contrib.gis.db.backends.postgis", result.stdout)
        self.assertIn("redis://redis:6379/0", result.stdout)
