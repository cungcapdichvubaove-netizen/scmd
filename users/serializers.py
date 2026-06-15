# -*- coding: utf-8 -*-
from rest_framework import serializers
<<<<<<< HEAD

from core.models import AuditLog


=======
from core.models import AuditLog

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
class HRAlertHistorySerializer(serializers.ModelSerializer):
    """
    Serializer chuyển đổi AuditLog thành định dạng thông báo HR.
    """
<<<<<<< HEAD

    title = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    count = serializers.SerializerMethodField()
=======
    title = serializers.CharField(source='changes.title', read_only=True)
    message = serializers.CharField(source='changes.message', read_only=True)
    count = serializers.IntegerField(source='changes.count', read_only=True)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

    class Meta:
        model = AuditLog
        fields = [
<<<<<<< HEAD
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
=======
            'id', 'timestamp', 'title', 'message', 'count', 'status'
        ]
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
