# -*- coding: utf-8 -*-
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

class FCMTokenRegistrationSerializer(serializers.Serializer):
    """
    Serializer validate token gửi từ Mobile App.
    """
    fcm_token = serializers.CharField(
        required=True, max_length=255, 
        error_messages={'required': _("Thiếu FCM token.")}
    )