# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: operations/api_views.py
Author: Mr. Anh
Created Date: 2025-12-10
Description: API Views cho Mobile App & Dashboard War Room.
             FIXED: Khôi phục class name MobileCaTrucViewSet để khớp với urls.py.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Count, Q

from .models import PhanCongCaTruc, BaoCaoSuCo, ChamCong, MucTieu
# Import Alias từ serializers.py (File bạn vừa sửa)
from .serializers import MobileCaTrucSerializer, MobileBaoCaoSuCoSerializer
from .services.attendance_service import AttendanceService
from main.utils.api_helper import api_response, error_response

# ==============================================================================
# 1. MOBILE APP APIS (LEGACY NAMES PRESERVED)
# ==============================================================================

class MobileCaTrucViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API xem lịch trực của nhân viên (Tên cũ: MobileCaTrucViewSet)
    """
    serializer_class = MobileCaTrucSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Lấy nhân viên gắn với User đang login
        if hasattr(self.request.user, 'nhanvien_profile'):
            return PhanCongCaTruc.objects.filter(
                nhan_vien=self.request.user.nhanvien_profile,
                ngay_truc__gte=timezone.now().date()
            ).order_by('ngay_truc')
        # Fallback cho trường hợp dùng related_name khác hoặc chưa có profile
        elif hasattr(self.request.user, 'nhan_vien'):
             return PhanCongCaTruc.objects.filter(
                nhan_vien=self.request.user.nhan_vien,
                ngay_truc__gte=timezone.now().date()
            ).order_by('ngay_truc')
        return PhanCongCaTruc.objects.none()

    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        """
        API Check-out (Action custom cho Mobile App cũ)
        """
        try:
            ca_truc = self.get_object()
        except Exception:
            return Response({"detail": "Không tìm thấy ca trực"}, status=status.HTTP_404_NOT_FOUND)
        
        anh = request.FILES.get('image')
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        
        success, msg, data = AttendanceService.process_check_out(
            phan_cong=ca_truc,
            lat=lat, lng=lng,
            image=anh,
            ip=request.META.get('REMOTE_ADDR'),
            device_info=request.META.get('HTTP_USER_AGENT', '')
        )

        if success:
            return Response({
                "detail": msg,
                "time": data.get('time', timezone.now()).strftime('%H:%M %d/%m/%Y')
            })
        else:
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

class MobileBaoCaoSuCoViewSet(viewsets.ModelViewSet):
    """
    API Sự cố (Tên cũ: MobileBaoCaoSuCoViewSet)
    """
    serializer_class = MobileBaoCaoSuCoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, 'nhanvien_profile'):
            return BaoCaoSuCo.objects.filter(nhan_vien_bao_cao=self.request.user.nhanvien_profile)
        elif hasattr(self.request.user, 'nhan_vien'):
            return BaoCaoSuCo.objects.filter(nhan_vien_bao_cao=self.request.user.nhan_vien)
        return BaoCaoSuCo.objects.none()

    def perform_create(self, serializer):
        if hasattr(self.request.user, 'nhanvien_profile'):
            serializer.save(nhan_vien_bao_cao=self.request.user.nhanvien_profile)
        elif hasattr(self.request.user, 'nhan_vien'):
            serializer.save(nhan_vien_bao_cao=self.request.user.nhan_vien)
        else:
            serializer.save()

# ==============================================================================
# 2. STANDALONE CHECK-IN/OUT APIS (NEW STANDARD)
# ==============================================================================

class CheckInAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ca_truc_id = request.data.get('ca_truc_id')
        lat = request.data.get('lat')
        lng = request.data.get('long')
        image = request.FILES.get('image')
        ip_addr = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT')

        if not ca_truc_id:
            return error_response("Thiếu ID ca trực", error_code="MISSING_ID")

        try:
            # Hỗ trợ cả 2 kiểu related_name
            if hasattr(request.user, 'nhanvien_profile'):
                nv = request.user.nhanvien_profile
            else:
                nv = getattr(request.user, 'nhan_vien', None)

            ca_truc = PhanCongCaTruc.objects.get(id=ca_truc_id, nhan_vien=nv)
        except PhanCongCaTruc.DoesNotExist:
            return error_response("Ca trực không tồn tại", error_code="INVALID_SHIFT")

        success, msg, data = AttendanceService.process_check_in(
            phan_cong=ca_truc, lat=lat, lng=lng, image=image, ip=ip_addr, device_info=user_agent
        )

        if success:
            return api_response(message=msg, data=data)
        else:
            return error_response(message=msg, error_code="CHECKIN_FAILED")

class CheckOutAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ca_truc_id = request.data.get('ca_truc_id')
        lat = request.data.get('lat')
        lng = request.data.get('long')
        image = request.FILES.get('image')
        ip_addr = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT')

        if not ca_truc_id:
            return error_response("Thiếu ID ca trực")

        try:
            if hasattr(request.user, 'nhanvien_profile'):
                nv = request.user.nhanvien_profile
            else:
                nv = getattr(request.user, 'nhan_vien', None)
            ca_truc = PhanCongCaTruc.objects.get(id=ca_truc_id, nhan_vien=nv)
        except PhanCongCaTruc.DoesNotExist:
            return error_response("Ca trực không hợp lệ")

        success, msg, data = AttendanceService.process_check_out(
            phan_cong=ca_truc, lat=lat, lng=lng, image=image, ip=ip_addr, device_info=user_agent
        )

        if success:
            return api_response(message=msg, data=data)
        else:
            return error_response(message=msg)

# ==============================================================================
# 3. DASHBOARD & MAP APIS (WAR ROOM DATA)
# ==============================================================================

class DashboardDataAPIView(APIView):
    """
    API cung cấp dữ liệu tổng hợp cho Dashboard bản đồ.
    Trả về cấu trúc chuẩn: { stats, markers, incidents, last_activity }
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        
        # 1. Stats
        total_shifts = PhanCongCaTruc.objects.filter(ngay_truc=today).count()
        active_shifts = ChamCong.objects.filter(
            thoi_gian_check_in__date=today,
            thoi_gian_check_out__isnull=True
        ).count()
        
        stats = {
            "tong_ca": total_shifts,
            "da_checkin": active_shifts,
            "vang_mat": total_shifts - active_shifts
        }

        # 2. Markers (Staff)
        active_ccs = ChamCong.objects.filter(
            thoi_gian_check_in__date=today,
            thoi_gian_check_out__isnull=True
        ).select_related('ca_truc__nhan_vien', 'ca_truc__vi_tri_chot__muc_tieu')

        markers_data = []
        for cc in active_ccs:
            try:
                lat = float(cc.lat_check_in) if cc.lat_check_in else None
                lng = float(cc.long_check_in) if cc.long_check_in else None
                
                if not lat and cc.location_check_in:
                    lat = float(cc.location_check_in.y)
                    lng = float(cc.location_check_in.x)
                
                if not lat and cc.ca_truc.vi_tri_chot.muc_tieu.vi_do:
                    lat = float(cc.ca_truc.vi_tri_chot.muc_tieu.vi_do)
                    lng = float(cc.ca_truc.vi_tri_chot.muc_tieu.kinh_do)
            except (ValueError, TypeError):
                continue

            if lat and lng:
                nv = cc.ca_truc.nhan_vien
                avatar_url = None
                if nv.anh_the:
                    try:
                        avatar_url = nv.anh_the.url
                    except ValueError:
                        pass

                markers_data.append({
                    "id": nv.id,
                    "name": nv.ho_ten,
                    "employee_code": nv.ma_nhan_vien,
                    "phone": str(nv.sdt_chinh or "N/A"),
                    "avatar": avatar_url,
                    "target": cc.ca_truc.vi_tri_chot.muc_tieu.ten_muc_tieu,
                    "lat": lat,
                    "lng": lng,
                    "time": cc.thoi_gian_check_in.strftime('%H:%M'),
                    "status": "active"
                })

        # 3. Incidents
        incidents_qs = BaoCaoSuCo.objects.filter(
            trang_thai__in=['CHO_XU_LY', 'DANG_XU_LY', 'CHO_DEN_BU']
        ).select_related('muc_tieu', 'nhan_vien_bao_cao').order_by('-created_at')
        
        incidents_data = []
        for ic in incidents_qs:
            lat, lng = None, None
            if ic.muc_tieu and ic.muc_tieu.vi_do:
                try:
                    lat = float(ic.muc_tieu.vi_do)
                    lng = float(ic.muc_tieu.kinh_do)
                except (ValueError, TypeError):
                    pass
            
            if lat and lng:
                incidents_data.append({
                    "id": ic.id,
                    "title": ic.tieu_de,
                    "level": ic.muc_do,
                    "priority": 'high' if ic.muc_do == 'NGUY_HIEM' else 'normal',
                    "thoi_gian": ic.thoi_gian_phat_hien.strftime('%H:%M'),
                    "muc_tieu": ic.muc_tieu.ten_muc_tieu,
                    "reporter": ic.nhan_vien_bao_cao.ho_ten if ic.nhan_vien_bao_cao else "N/A",
                    "reporter_phone": str(ic.nhan_vien_bao_cao.sdt_chinh or "") if ic.nhan_vien_bao_cao else "",
                    "lat": lat,
                    "lng": lng
                })

        # 4. Last Activity
        last_activity = None
        last_cc = ChamCong.objects.filter(thoi_gian_check_in__date=today).order_by('-thoi_gian_check_in').first()
        if last_cc:
            last_activity = {
                "user": last_cc.ca_truc.nhan_vien.ho_ten,
                "action": "Check-in",
                "time": last_cc.thoi_gian_check_in.strftime('%H:%M'),
                "target": last_cc.ca_truc.vi_tri_chot.muc_tieu.ten_muc_tieu
            }

        return Response({
            "stats": stats,
            "markers": markers_data,
            "incidents": incidents_data,
            "last_activity": last_activity
        })