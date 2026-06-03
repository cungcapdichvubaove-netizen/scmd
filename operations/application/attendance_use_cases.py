# -*- coding: utf-8 -*-
"""
Application Layer: Attendance Use Cases.
Coordinates business flows for Check-in and Check-out.
Version: v2.0.1 (Hardening Phase)
"""

import logging
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.db import transaction, IntegrityError
from core.domain.geo import validate_geofence
from operations.analytics import calculate_swap_rate
from operations.models import ChamCong, PhanCongCaTruc, BaoCaoSuCo, KiemTraQuanSo
from datetime import timedelta, datetime
from django.db.models import Q
from main.models import AuditLog
from operations.tasks import process_timesheet_async
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

class GetMobileDashboardUseCase:
    @staticmethod
    def execute(nhan_vien):
        """
        Logic xác định ca trực ưu tiên hiển thị trên Dashboard.
        """
        today = timezone.localtime(timezone.now()).date()
        yesterday = today - timedelta(days=1)
        current_dt = timezone.now()
        
        # Lấy các phân công trong 2 ngày gần nhất
        phan_congs = PhanCongCaTruc.objects.filter(
            nhan_vien=nhan_vien, 
            ngay_truc__range=[yesterday, today]
        ).select_related('vi_tri_chot__muc_tieu', 'ca_lam_viec').order_by('ngay_truc', 'ca_lam_viec__gio_bat_dau')
        
        ca_truc_uu_tien = None
        trang_thai = False # False: Chưa check-in, True: Đang trực, "DONE": Đã xong

        # 1. Ưu tiên ca đang trực (đã check-in nhưng chưa check-out)
        for pc in phan_congs:
            if hasattr(pc, 'chamcong') and pc.chamcong.thoi_gian_check_in and not pc.chamcong.thoi_gian_check_out:
                return pc, True

        # 2. Tìm ca sắp tới (trong vòng 60p trước giờ bắt đầu) hoặc đang trong giờ trực nhưng chưa check-in
        for pc in phan_congs:
            if hasattr(pc, 'chamcong') and pc.chamcong.thoi_gian_check_out:
                continue
            
            from datetime import datetime
            # Chuyển đổi naive datetime sang aware để so sánh
            start_real = timezone.make_aware(datetime.combine(pc.ngay_truc, pc.ca_lam_viec.gio_bat_dau))
            
            if pc.ca_lam_viec.is_night_shift:
                end_real = timezone.make_aware(datetime.combine(pc.ngay_truc + timedelta(days=1), pc.ca_lam_viec.gio_ket_thuc))
            else:
                end_real = timezone.make_aware(datetime.combine(pc.ngay_truc, pc.ca_lam_viec.gio_ket_thuc))
            
            if end_real > current_dt and (start_real - timedelta(minutes=60)) <= current_dt:
                return pc, False

        # 3. Fallback: Ca đầu tiên của hôm nay chưa check-in
        ca_hom_nay = phan_congs.filter(ngay_truc=today, chamcong__thoi_gian_check_in__isnull=True).first()
        if ca_hom_nay:
            return ca_hom_nay, False
            
        # 4. Cuối cùng: Ca vừa kết thúc
        last_pc = phan_congs.last()
        if last_pc and hasattr(last_pc, 'chamcong') and last_pc.chamcong.thoi_gian_check_out:
            return last_pc, "DONE"
            
        return None, False

class CheckInUseCase:
    @staticmethod
    def execute(phan_cong, lat, lng, image, ip, device_info, note="", user=None) -> tuple[bool, str, dict | None, str | None]:
        """
        Thực thi quy trình Check-in.
        Logic Geofencing được tách biệt vào Domain Layer.
        """
        # 1. Domain Logic: Xác thực Geofencing (SSOT từ CRM/Target)
        is_valid_location = True
        distance = 0.0
        
        target = phan_cong.vi_tri_chot.muc_tieu # SSOT: Lấy thông tin mục tiêu từ PhanCongCaTruc
        if lat and lng and target.vi_do and target.kinh_do:
            is_valid_location, distance = validate_geofence(
                float(lat),
                float(lng),
                float(target.vi_do),
                float(target.kinh_do),
                float(target.ban_kinh_cho_phep or 100)
            )

        # 2. Infrastructure: Lưu trữ dữ liệu vào Database
        with transaction.atomic():
            point = Point(float(lng), float(lat), srid=4326) if lat and lng else None
            
            # Lấy tenant_id từ phan_cong (SSOT)
            tenant_id = phan_cong.tenant_id

            cham_cong, created = ChamCong.objects.get_or_create(
                ca_truc=phan_cong,
                tenant_id=tenant_id,
                defaults={
                    'thoi_gian_check_in': timezone.now(),
                    'anh_check_in': image,
                    'location_check_in': point,
                    'ip_check_in': ip,
                    'thiet_bi_check_in': device_info,
                    'vi_tri_hop_le': is_valid_location,
                    'khoang_cach_check_in': distance,
                    'ghi_chu': note
                }
            )
            
            if not created:
                return False, "Bạn đã check-in ca này rồi.", {"time": cham_cong.thoi_gian_check_in}, "ALREADY_CHECKED_IN"

            # 3. Security Audit Log
            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.EXECUTE,
                module="Operations",
                model_name="ChamCong",
                object_id=str(cham_cong.id),
                ip_address=ip,
                user_agent=device_info,
                note=f"Check-in tại {phan_cong.vi_tri_chot.muc_tieu.ten_muc_tieu}. Distance: {distance}m",
                tenant_id=tenant_id
            )

        return True, "Check-in thành công.", {"time": cham_cong.thoi_gian_check_in, "id": cham_cong.id}, None

class CheckOutUseCase:
    @staticmethod
    def execute(phan_cong, lat, lng, image, ip, device_info, note="", user=None) -> tuple[bool, str, dict | None, str | None]:
        """
        Thực thi quy trình Check-out.
        """
        with transaction.atomic():
            try:
                # Rule 10: Enforce row lock to prevent race conditions during concurrent check-out attempts.
                cham_cong = ChamCong.objects.select_for_update().get(ca_truc=phan_cong)
            except ChamCong.DoesNotExist:
                return False, "Chưa tìm thấy dữ liệu Check-in.", None, "CHECKIN_DATA_NOT_FOUND"

            if cham_cong.thoi_gian_check_out:
                return False, "Ca trực này đã check-out rồi.", {"time": cham_cong.thoi_gian_check_out}, "ALREADY_CHECKED_OUT"

            cham_cong.thoi_gian_check_out = timezone.now()
            cham_cong.anh_check_out = image
            if lat and lng:
                cham_cong.location_check_out = Point(float(lng), float(lat), srid=4326)
            cham_cong.ip_check_out = ip
            cham_cong.thiet_bi_check_out = device_info
            if note:
                cham_cong.ghi_chu = (cham_cong.ghi_chu or "") + " | " + note
            cham_cong.save()
            phan_cong.da_checkin = False # Reset flag if model has it
            
            # 3. Security Audit Log
            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.EXECUTE,
                module="Operations",
                model_name="ChamCong",
                object_id=str(cham_cong.id),
                ip_address=ip,
                user_agent=device_info,
                note=f"Check-out thành công cho ca ID: {phan_cong.id}",
                tenant_id=phan_cong.tenant_id
            )
            
            # 4. Async Task: Trigger tính lương ngay lập tức (SSOT Section 7)
            transaction.on_commit(lambda: process_timesheet_async.delay(cham_cong.id))

        return True, "Check-out thành công.", {"time": cham_cong.thoi_gian_check_out, "id": cham_cong.id}, None

class CalculateWorkHoursUseCase:
    @staticmethod
    def execute(cham_cong):
        """
        Tính toán tổng giờ làm việc thực tế dựa trên dữ liệu chấm công.
        Business Rule: Chỉ tính khi có đủ In/Out.
        """
        if not cham_cong.thoi_gian_check_in or not cham_cong.thoi_gian_check_out:
            return 0.0
        
        delta = cham_cong.thoi_gian_check_out - cham_cong.thoi_gian_check_in
        total_seconds = delta.total_seconds()
        
        # Anti-fraud: Kiểm tra thời gian âm (Check-out trước Check-in)
        if total_seconds < 0:
            logger.error(
                f"CRITICAL: Negative work hours detected for ChamCong ID {cham_cong.id}. "
                f"In: {cham_cong.thoi_gian_check_in}, Out: {cham_cong.thoi_gian_check_out}"
            )
            return 0.0
            
        return round(total_seconds / 3600, 2)

class TriggerSOSUseCase:
    @staticmethod
    def execute(nhan_vien, lat, lng) -> tuple[bool, str, any, str | None]:
        """Logic gửi tín hiệu SOS khẩn cấp."""
        ca_truc = PhanCongCaTruc.objects.filter(
            nhan_vien=nhan_vien, 
            chamcong__thoi_gian_check_in__isnull=False, 
            chamcong__thoi_gian_check_out__isnull=True
        ).last()
        muc_tieu = ca_truc.vi_tri_chot.muc_tieu if ca_truc else None
        
        with transaction.atomic():
            su_co = BaoCaoSuCo.objects.create(
                tenant_id=settings.SCMD_ORGANIZATION_ID,
                tieu_de=f"🆘 CẤP CỨU: {nhan_vien.ho_ten.upper()}",
                nhan_vien_bao_cao=nhan_vien,
                muc_do='NGUY_HIEM',
                trang_thai='CHO_XU_LY',
                thoi_gian_phat_hien=timezone.now(),
                muc_tieu=muc_tieu,
                ca_truc=ca_truc,
                mo_ta_chi_tiet=f"SOS từ Mobile Web. Vị trí GPS: {lat}, {lng}"
            )
        return True, "ĐÃ GỬI TÍN HIỆU KHẨN CẤP!", su_co, None

class ConfirmAliveCheckUseCase:
    @staticmethod
    def execute(check_id, image, user) -> tuple[bool, str, any, str | None]:
        """Logic xác nhận điểm danh Alive Check."""
        # Rule 4.1: Enforce tenant isolation
        alive = KiemTraQuanSo.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(id=check_id).first()
        
        if not alive:
            return False, "Yêu cầu kiểm tra không tồn tại.", None, "NOT_FOUND"
        
        if alive.ca_truc.nhan_vien.user != user:
            return False, "Bạn không có quyền xác nhận yêu cầu này.", None, "FORBIDDEN"

        with transaction.atomic():
            alive.anh_xac_thuc = image
            alive.thoi_gian_phan_hoi = timezone.now()
            alive.trang_thai = 'OK'
            alive.save()
            
        return True, "Xác nhận điểm danh thành công!", alive, None

class GetSwapRateReportUseCase:
    """
    Application Layer: Báo cáo tỷ lệ đổi ca theo Mục tiêu.
    Phân tích độ ổn định nhân sự (Personnel Stability).
    """
    @staticmethod
    def execute(month: int, year: int, tenant_id: str):
        from clients.models import MucTieu
        from operations.models import BaoCaoDeXuat

        # 1. Lấy danh sách mục tiêu đang hoạt động
        muc_tieus = MucTieu.objects.all()
        report_data = []

        for mt in muc_tieus:
            # 2. Tổng số ca trực đã xếp trong kỳ (SSOT: PhanCongCaTruc)
            total_planned = PhanCongCaTruc.objects.filter(
                vi_tri_chot__muc_tieu=mt,
                ngay_truc__month=month,
                ngay_truc__year=year,
                tenant_id=tenant_id
            ).count()

            # 3. Số ca đã thực hiện đổi thành công (SSOT: BaoCaoDeXuat[DOI_CA])
            swaps_approved = BaoCaoDeXuat.objects.filter(
                ca_truc__vi_tri_chot__muc_tieu=mt,
                loai_de_xuat='DOI_CA',
                trang_thai='DA_XU_LY', # Trạng thái đã phê duyệt thành công
                ca_truc__ngay_truc__month=month,
                ca_truc__ngay_truc__year=year,
                tenant_id=tenant_id
            ).count()

            # 4. Tính toán qua Domain Logic
            rate = calculate_swap_rate(swaps_approved, total_planned)

            report_data.append({
                "muc_tieu_id": mt.id,
                "ten_muc_tieu": mt.ten_muc_tieu,
                "total_shifts": total_planned,
                "swap_count": swaps_approved,
                "swap_rate": rate,
                "stability_index": "STABLE" if rate < 10 else "MODERATE" if rate < 25 else "UNSTABLE"
            })

        # Sắp xếp theo tỷ lệ đổi ca giảm dần để Ban Giám đốc nhận diện điểm nóng
        report_data.sort(key=lambda x: x['swap_rate'], reverse=True)

        return {"month": month, "year": year, "results": report_data}

class MonitorWeeklySwapRateUseCase:
    """
    Application Layer: Giám sát tỷ lệ đổi ca tự động.
    Tần suất check: Định kỳ (qua Celery).
    Ngưỡng cảnh báo: 30% trong 7 ngày.
    """
    @staticmethod
    def execute(tenant_id: str):
        from clients.models import MucTieu
        from operations.models import BaoCaoDeXuat

        # 1. Thiết lập khoảng thời gian: 7 ngày qua
        today = timezone.now().date()
        start_date = today - timedelta(days=7)
        
        muc_tieus = MucTieu.objects.all()
        alerts_triggered = 0

        for mt in muc_tieus:
            total_planned = PhanCongCaTruc.objects.filter(
                vi_tri_chot__muc_tieu=mt,
                ngay_truc__range=[start_date, today],
                tenant_id=tenant_id
            ).count()

            swaps_approved = BaoCaoDeXuat.objects.filter(
                ca_truc__vi_tri_chot__muc_tieu=mt,
                loai_de_xuat='DOI_CA',
                trang_thai='DA_XU_LY',
                ca_truc__ngay_truc__range=[start_date, today],
                tenant_id=tenant_id
            ).count()

            rate = calculate_swap_rate(swaps_approved, total_planned)

            # 2. Kiểm tra ngưỡng (Threshold: 30%)
            if rate >= 30.0:
                # 3. Gửi thông báo WebSocket tới War Room
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "war_room_staff",
                    {
                        "type": "operational.alert",
                        "payload": {
                            "title": "Cảnh báo Độ ổn định nhân sự",
                            "message": f"Mục tiêu '{mt.ten_muc_tieu}' có tỷ lệ đổi ca cao bất thường ({rate}%).",
                            "target_id": mt.id,
                            "swap_rate": rate,
                            "severity": "CRITICAL" if rate > 50 else "WARNING"
                        }
                    }
                )
                logger.warning(f"[Stability Alert] Target: {mt.ten_muc_tieu} - Rate: {rate}%")
                alerts_triggered += 1

        return alerts_triggered
