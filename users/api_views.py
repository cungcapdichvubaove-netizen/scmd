# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework import permissions, status
from .api_serializers import FCMTokenRegistrationSerializer
from .application.notification_use_cases import UpdateFCMTokenUseCase
from main.utils.api_helper import api_response, error_response

class FCMTokenUpdateAPIView(APIView):
    """
    API tiếp nhận FCM Token từ thiết bị di động của nhân viên.
    Endpoint: /api/v1/users/fcm-token/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = FCMTokenRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message=serializer.errors, 
                error_code="INVALID_INPUT", 
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Thu thập thông tin thiết bị từ Header để ghi log (Rule 12.3)
            UpdateFCMTokenUseCase.execute(
                user=request.user,
                fcm_token=serializer.validated_data['fcm_token'],
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return api_response(message="Cập nhật mã định danh thiết bị thành công.")
            
        except ValueError as e:
            return error_response(str(e), error_code="PROFILE_NOT_FOUND")
        except Exception as e:
            return error_response(
                "Lỗi hệ thống khi cập nhật token.", 
                error_code="INTERNAL_ERROR"
            )