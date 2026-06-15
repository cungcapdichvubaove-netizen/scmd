# -*- coding: utf-8 -*-
from rest_framework import serializers

from core.models import AuditLog


class HRAlertHistorySerializer(serializers.ModelSerializer):
    """
    Serializer chuyển đổi AuditLog thành định dạng thông báo HR.
    """

    title = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    count = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "timestamp",
            "title",
            "message",
            "count",
            "status",
        ]

    def _changes_dict(self, obj):
        changes = getattr(obj, "changes", None)
        return changes if isinstance(changes, dict) else {}

    def get_title(self, obj):
        return self._changes_dict(obj).get("title", "")

    def get_message(self, obj):
        return self._changes_dict(obj).get("message", "")

    def get_count(self, obj):
        count = self._changes_dict(obj).get("count", 0)
        try:
            return int(count)
        except (TypeError, ValueError):
            return 0
