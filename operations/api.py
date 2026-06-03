# -*- coding: utf-8 -*-
"""
Frozen legacy API surface.

Reason:
- The project now standardizes mobile contracts in `operations.api_views`.
- Old endpoints in this module had broken imports and mismatched contracts.
- They are intentionally frozen instead of silently serving inconsistent behavior.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class FrozenLegacyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return self._response()

    def post(self, request, *args, **kwargs):
        return self._response()

    def _response(self):
        return Response(
            {
                "success": False,
                "error_code": "LEGACY_API_FROZEN",
                "message": (
                    "Legacy endpoint has been frozen in v3.0.0. "
                    "Use the standardized mobile contracts in operations.api_views."
                ),
            },
            status=status.HTTP_410_GONE,
        )
