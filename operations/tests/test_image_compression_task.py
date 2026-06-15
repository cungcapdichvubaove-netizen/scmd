# -*- coding: utf-8 -*-
"""Tests for opt-in image derivative compression in operations."""

from io import BytesIO
import hashlib
import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from operations.models import BaoCaoSuCo
from operations.tasks import compress_uploaded_image_field


class OperationsImageCompressionTaskTest(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix="scmd-image-compression-")
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.media_root, ignore_errors=True))

    def _noisy_jpeg_upload(self, *, width=2400, height=1600, quality=95):
        image = Image.effect_noise((width, height), 96).convert("RGB")
        payload = BytesIO()
        image.save(payload, format="JPEG", quality=quality)
        return SimpleUploadedFile(
            "incident-evidence.jpg",
            payload.getvalue(),
            content_type="image/jpeg",
        )

    def _stored_bytes(self, field):
        with field.storage.open(field.name, "rb") as stored:
            return stored.read()

    def test_compress_uploaded_image_field_creates_derivative_and_preserves_original(self):
        upload = self._noisy_jpeg_upload()
        incident = BaoCaoSuCo.objects.create(
            ma_su_co="IMG-COMP-001",
            tieu_de="Ảnh hiện trường giữ nguyên bản gốc",
            hinh_anh_1=upload,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )
        original_name = incident.hinh_anh_1.name
        original_bytes = self._stored_bytes(incident.hinh_anh_1)
        original_hash = hashlib.sha256(original_bytes).hexdigest()
        original_size = len(original_bytes)

        result = compress_uploaded_image_field(
            incident.hinh_anh_1,
            max_dimension=800,
            quality=75,
        )

        self.assertEqual(result["status"], "compressed")
        self.assertEqual(result["name"], original_name)
        self.assertNotEqual(result["derivative_name"], original_name)
        self.assertTrue(result["original_preserved"])
        self.assertLess(result["compressed_size"], original_size)
        self.assertLessEqual(max(result["compressed_dimensions"]), 800)

        preserved_bytes = self._stored_bytes(incident.hinh_anh_1)
        self.assertEqual(hashlib.sha256(preserved_bytes).hexdigest(), original_hash)
        self.assertEqual(len(preserved_bytes), original_size)

        storage = incident.hinh_anh_1.storage
        self.assertTrue(storage.exists(result["derivative_name"]))
        self.assertLess(storage.size(result["derivative_name"]), original_size)
        with storage.open(result["derivative_name"], "rb") as derivative:
            with Image.open(derivative) as compressed_image:
                self.assertLessEqual(max(compressed_image.size), 800)
