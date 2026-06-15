# -*- coding: utf-8 -*-
from django.test import Client, TestCase
from django.urls import reverse


class InfrastructureTests(TestCase):
    """Kiểm tra các endpoint kỹ thuật và guard hạ tầng."""

    def test_healthcheck_endpoint(self):
        """Docker/K8s probe phải nhận được trạng thái DB và cache-control an toàn."""
        client = Client()
        response = client.get(reverse("main:healthcheck"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["checks"]["database"], "ok")
        self.assertIn("no-store", response["Cache-Control"])

    def test_internal_media_auth_route_is_registered(self):
        client = Client()
        response = client.get("/_internal/media-auth/?uri=/media/check_in/example.jpg")

        self.assertEqual(response.status_code, 401)
