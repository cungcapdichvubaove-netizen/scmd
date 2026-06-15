# -*- coding: utf-8 -*-
from rest_framework import viewsets, mixins, pagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.db.models import Q
from main.models import AuditLog
from .serializers import HRAlertHistorySerializer

class HRAlertPagination(pagination.PageNumberPagination):
    """
    Phân trang tùy chỉnh tuân thủ định dạng Response của dự án.
    """
    page_size = 10
    page_size_query_param = 'page_size'  # Cho phép client truyền ?page_size=X
    max_page_size = 100                 # Giới hạn tối đa để tránh quá tải hệ thống

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'message': 'Lấy danh sách thông báo thành công',
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'data': data
        })

class HRAlertHistoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API Endpoint để bộ phận HR truy vấn lịch sử các thông báo hệ thống.
    Lọc trong vòng 30 ngày gần nhất.
    """
    serializer_class = HRAlertHistorySerializer
    permission_classes = [IsAuthenticated] # Nên bổ sung permission check IsHR hoặc IsStaff
    pagination_class = HRAlertPagination

    def get_queryset(self):
        # 1. Truy vấn AuditLog với các điều kiện cơ bản
        # - module: 'users'
        # - note: 'hr_alert_summary' (đã đánh dấu ở Use Case)
        # - tenant_id: Theo đúng cấu trúc Multi-tenancy
        queryset = AuditLog.objects.filter(
            module='users',
            note='hr_alert_summary',
            tenant_id=settings.SCMD_ORGANIZATION_ID
        )

        # Xử lý lọc theo khoảng ngày
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)

        # Nếu không có khoảng ngày, mặc định lấy 30 ngày gần nhất
        if not start_date and not end_date:
            thirty_days_ago = timezone.now() - timedelta(days=30)
            queryset = queryset.filter(timestamp__gte=thirty_days_ago)

        # Xử lý tìm kiếm theo tiêu đề hoặc nội dung (trong JSONField)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(changes__title__icontains=search) | 
                Q(changes__message__icontains=search)
            )

        # Lọc theo trạng thái
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-timestamp')

    def list(self, request, *args, **kwargs):
        """
        Ghi đè phương thức list để tuân thủ Response Format của dự án.
        Rule: { "success": true, "message": "...", "data": [...] }
        """
        return super().list(request, *args, **kwargs)