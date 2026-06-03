# -*- coding: utf-8 -*-
from rest_framework import serializers
from core.models import AuditLog

class HRAlertHistorySerializer(serializers.ModelSerializer):
    """
    Serializer chuyển đổi AuditLog thành định dạng thông báo HR.
    """
    title = serializers.CharField(source='changes.title', read_only=True)
    message = serializers.CharField(source='changes.message', read_only=True)
    count = serializers.IntegerField(source='changes.count', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'timestamp', 'title', 'message', 'count', 'status'
        ]