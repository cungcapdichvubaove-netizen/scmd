import re
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, SimpleTestCase, TestCase

import config.bootstrap_credentials as bootstrap_credentials
import config.settings as project_settings
import main.views as main_views
from operations.models import BaoCaoDeXuat
from users.models import NhanVien


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TAILWIND_CDN_MARKER = "cdn." + "tailwindcss.com"


class StaticTemplateSurfaceSecurityTest(SimpleTestCase):
    def test_no_python_source_under_static_or_templates(self):
        unsafe_files = []
        for root_name in ("static", "staticfiles"):
            root = PROJECT_ROOT / root_name
            if root.exists():
                unsafe_files.extend(path.relative_to(PROJECT_ROOT).as_posix() for path in root.rglob("*.py"))

        unsafe_files.extend(
            path.relative_to(PROJECT_ROOT).as_posix()
            for path in PROJECT_ROOT.rglob("*.py")
            if any(part == "templates" for part in path.parts)
        )

        self.assertEqual(unsafe_files, [], "Python source must not live under static/staticfiles/templates")

    def test_tailwind_cdn_is_not_used_in_owned_templates(self):
        owned_roots = [
            "main",
            "templates",
            "accounting",
            "clients",
            "dashboard",
            "inspection",
            "inventory",
            "operations",
            "reports",
            "users",
        ]
        hits = []
        for root_name in owned_roots:
            root = PROJECT_ROOT / root_name
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.suffix.lower() not in {".html", ".css", ".js"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                if TAILWIND_CDN_MARKER in text:
                    hits.append(path.relative_to(PROJECT_ROOT).as_posix())

        self.assertEqual(hits, [], "Production templates/assets must use local Tailwind build, not CDN")

    def test_nginx_media_location_requires_internal_auth_request(self):
        nginx_conf = (PROJECT_ROOT / "nginx" / "default.conf").read_text(encoding="utf-8")

        self.assertIn("location = /_internal/media-auth/", nginx_conf)
        self.assertIn("auth_request /_internal/media-auth/?uri=$request_uri;", nginx_conf)
        self.assertIn("proxy_pass http://scmd_backend;", nginx_conf)
        self.assertIn("proxy_set_header X-Original-URI $arg_uri;", nginx_conf)
        self.assertIn('add_header Cache-Control "private, no-store" always;', nginx_conf)
        self.assertIn('add_header X-Content-Type-Options "nosniff" always;', nginx_conf)
        self.assertNotIn("location /media/ {\n        alias /app/media/;\n    }", nginx_conf)

    def test_media_auth_policy_matrix_covers_owned_upload_paths(self):
        source_roots = [
            "accounting",
            "clients",
            "inspection",
            "inventory",
            "main",
            "operations",
            "users",
            "workflow",
        ]
        upload_prefixes = set()
        upload_to_pattern = re.compile(r"upload_to\s*=\s*['\"]([^'\"]+)['\"]")
        for root_name in source_roots:
            root = PROJECT_ROOT / root_name
            for path in root.rglob("*.py"):
                if "migrations" in path.parts or path.name.startswith("test") or path.name == "tests.py":
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                for raw_upload_to in upload_to_pattern.findall(text):
                    prefix = raw_upload_to.split("%", 1)[0].rstrip("/") + "/"
                    upload_prefixes.add(prefix)

        missing = sorted(prefix for prefix in upload_prefixes if prefix not in main_views.MEDIA_AUTH_POLICY_MATRIX)
        self.assertEqual(missing, [], "Every owned upload_to prefix must be represented in MEDIA_AUTH_POLICY_MATRIX")

    def test_docker_compose_prod_documents_https_edge_contract(self):
        compose = (PROJECT_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

        self.assertIn("Production HTTPS contract", compose)
        self.assertIn("X-Forwarded-Proto=https", compose)
        self.assertIn("SECURE_SSL_REDIRECT=${SECURE_SSL_REDIRECT:-True}", compose)


class ProductionCredentialFailFastTest(SimpleTestCase):
    def test_settings_reject_common_secret_placeholders(self):
        self.assertTrue(project_settings.is_insecure_default("django-insecure-local-dev-key"))
        self.assertTrue(project_settings.is_insecure_default("your-very-secret-key-here-change-this-in-production!"))
        self.assertTrue(project_settings.is_insecure_default("change-this-admin-password"))
        self.assertFalse(project_settings.is_insecure_default("prod-secret-value-with-real-entropy-2026"))

    @patch.dict("os.environ", {"DEBUG": "False", "SCMD_ADMIN_PASSWORD": "change-this-admin-password"}, clear=True)
    def test_bootstrap_rejects_default_admin_password_in_production(self):
        with self.assertRaises(RuntimeError):
            bootstrap_credentials.get_admin_password()

    @patch.dict("os.environ", {"DEBUG": "False"}, clear=True)
    def test_bootstrap_rejects_default_admin_identity_in_production(self):
        with self.assertRaises(RuntimeError):
            bootstrap_credentials.get_admin_username()
        with self.assertRaises(RuntimeError):
            bootstrap_credentials.get_admin_email()

    @patch.dict(
        "os.environ",
        {
            "DEBUG": "False",
            "SCMD_ADMIN_USERNAME": "scmd.prod.admin",
            "SCMD_ADMIN_EMAIL": "admin@example.com",
            "SCMD_ADMIN_PASSWORD": "prod-admin-password-with-entropy-2026",
        },
        clear=True,
    )
    def test_bootstrap_allows_explicit_non_default_credentials_in_production(self):
        self.assertEqual(bootstrap_credentials.get_admin_username(), "scmd.prod.admin")
        self.assertEqual(bootstrap_credentials.get_admin_email(), "admin@example.com")
        self.assertEqual(bootstrap_credentials.get_admin_password(), "prod-admin-password-with-entropy-2026")


class MediaAuthPolicyCoverageTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner_user = User.objects.create_user("owner", "owner@example.com", "password")
        self.other_user = User.objects.create_user("other", "other@example.com", "password")
        self.staff = self.owner_user.nhan_vien
        self.staff.ho_ten = "Nhan vien media owner"
        self.staff.ma_nhan_vien = "NV-MEDIA-001"
        self.staff.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.staff.save(update_fields=["ho_ten", "ma_nhan_vien", "tenant_id"])

        self.other_staff = self.other_user.nhan_vien
        self.other_staff.ho_ten = "Nhan vien media other"
        self.other_staff.ma_nhan_vien = "NV-MEDIA-002"
        self.other_staff.tenant_id = settings.SCMD_ORGANIZATION_ID
        self.other_staff.save(update_fields=["ho_ten", "ma_nhan_vien", "tenant_id"])
        self.proposal = BaoCaoDeXuat.objects.create(
            nhan_vien=self.staff,
            tieu_de="De xuat test media auth",
            noi_dung="Noi dung de xuat",
            hinh_anh="de_xuat/2026/06/proposal-proof.jpg",
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )

    def test_media_auth_blocks_path_traversal(self):
        self.client.force_login(self.owner_user)

        response = self.client.get("/_internal/media-auth/?uri=/media/de_xuat/../../secret.txt")

        self.assertEqual(response.status_code, 403)

    def test_media_auth_anonymous_returns_401_for_representative_domains(self):
        representative_paths = [
            "anh_the/staff.jpg",
            "hop_dong_lao_dong/2026/06/contract.pdf",
            "check_in/2026/06/in.jpg",
            "su_co/audio/2026/06/voice.webm",
            "hop_dong/customer.pdf",
            "tam_ung_luong/2026/06/advance.pdf",
            "phieu_thu_hoi/2026/06/recovery.pdf",
            "tasks/2026/06/task.pdf",
        ]

        for relative_path in representative_paths:
            with self.subTest(relative_path=relative_path):
                response = self.client.get(f"/_internal/media-auth/?uri=/media/{relative_path}")
                self.assertEqual(response.status_code, 401)

    def test_media_auth_authenticated_unknown_prefix_is_forbidden(self):
        self.client.force_login(self.owner_user)

        response = self.client.get("/_internal/media-auth/?uri=/media/unmapped/private.pdf")

        self.assertEqual(response.status_code, 403)

    def test_media_auth_denies_out_of_scope_supported_document(self):
        self.client.force_login(self.other_user)

        response = self.client.get(f"/_internal/media-auth/?uri=/media/{self.proposal.hinh_anh}")

        self.assertEqual(response.status_code, 403)

    def test_media_auth_allows_owner_for_supported_document_path(self):
        self.client.force_login(self.owner_user)

        response = self.client.get(f"/_internal/media-auth/?uri=/media/{self.proposal.hinh_anh}")

        self.assertEqual(response.status_code, 200)
