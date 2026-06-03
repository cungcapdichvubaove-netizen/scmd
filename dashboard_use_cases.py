# -*- coding: utf-8 -*-
"""
Application Layer: Dashboard Use Cases.
Version: v2.1.1-strict
"""
import logging
from django.utils import timezone
from rolepermissions.checkers import has_role
from operations.models import ChamCong, PhanCongCaTruc, BaoCaoSuCo
from clients.models import MucTieu

logger = logging.getLogger(__name__)

class GetWarRoomDashboardUseCase:
    @staticmethod
    def execute(user, tenant_id, target_date, muc_tieu_id=None):
        """
        Orchestrates data for the War Room Dashboard with Site Scoping enforcement.
        Business logic separated from Interface Layer.
        """
        if not hasattr(user, 'nhan_vien'):
            return {}

        nv = user.nhan_vien
        
        # 0. Xác định phạm vi mục tiêu được phép (Site Scoping - Rule 2.2 WHITEPAPER)
        allowed_target_ids = []
        
        if has_role(user, ['ban_giam_doc', 'ke_toan']):
            allowed_target_ids = list(MucTieu.objects.values_list('id', flat=True))
        elif has_role(user, 'quan_ly_vung'):
            allowed_target_ids = list(MucTieu.objects.filter(quan_ly_vung=nv).values_list('id', flat=True))
        elif has_role(user, 'doi_truong'):
            allowed_target_ids = list(MucTieu.objects.filter(quan_ly_muc_tieu=nv).values_list('id', flat=True))

        # Lọc theo mục tiêu được yêu cầu và kiểm tra quyền
        final_target_ids = allowed_target_ids
        if muc_tieu_id:
            try:
                req_id = int(muc_tieu_id)
                if req_id in allowed_target_ids:
                    final_target_ids = [req_id]
                else:
                    logger.warning(f"SECURITY: User {user.id} attempted to access unauthorized Site {req_id}")
                    return {"error": "Unauthorized site access"}
            except (ValueError, TypeError):
                pass

        # 1. Query with Tenant Isolation and Site Scoping
        active_ccs_qs = ChamCong.objects.for_tenant(tenant_id).filter(
            thoi_gian_check_in__date=target_date,
            thoi_gian_check_out__isnull=True,
            ca_truc__vi_tri_chot__muc_tieu_id__in=final_target_ids
        ).select_related('ca_truc__nhan_vien', 'ca_truc__vi_tri_chot__muc_tieu')
        
        total_shifts_qs = PhanCongCaTruc.objects.for_tenant(tenant_id).filter(
            ngay_truc=target_date,
            vi_tri_chot__muc_tieu_id__in=final_target_ids
        )
        
        incidents_qs = BaoCaoSuCo.objects.for_tenant(tenant_id).filter(
            trang_thai__in=['CHO_XU_LY', 'DANG_XU_LY', 'CHO_DEN_BU'],
            muc_tieu_id__in=final_target_ids
        ).select_related('muc_tieu', 'nhan_vien_bao_cao').order_by('-created_at')

        # 2. Process Stats
        active_ccs_list = list(active_ccs_qs)
        total_shifts = total_shifts_qs.count()
        active_count = len(active_ccs_list)

        # 3. Process Markers
        markers_data = []
        for cc in active_ccs_list:
            point = cc.location_check_in
            if point:
                nv = cc.ca_truc.nhan_vien
                markers_data.append({
                    "id": nv.id,
                    "name": nv.ho_ten,
                    "lat": float(point.y),
                    "lng": float(point.x),
                    "target": cc.ca_truc.vi_tri_chot.muc_tieu.ten_muc_tieu,
                    "status": "active"
                })

        # 4. Process Incidents
        incidents_data = []
        for ic in incidents_qs:
            if ic.muc_tieu and ic.muc_tieu.vi_do:
                incidents_data.append({
                    "id": ic.id,
                    "title": ic.tieu_de,
                    "level": ic.muc_do,
                    "lat": float(ic.muc_tieu.vi_do),
                    "lng": float(ic.muc_tieu.kinh_do)
                })

        # 5. Last Activity
        last_cc = ChamCong.objects.for_tenant(tenant_id).filter(
            thoi_gian_check_in__date=target_date
        ).select_related('ca_truc__nhan_vien', 'ca_truc__vi_tri_chot__muc_tieu').order_by('-thoi_gian_check_in').first()
        
        last_act = None
        if last_cc:
            last_act = {
                "user": last_cc.ca_truc.nhan_vien.ho_ten,
                "action": "Check-in",
                "time": last_cc.thoi_gian_check_in.strftime('%H:%M')
            }

        return {
            "stats": {
                "tong_ca": total_shifts,
                "da_checkin": active_count,
                "vang_mat": total_shifts - active_count
            },
            "markers": markers_data,
            "incidents": incidents_data,
            "last_activity": last_act
        }


class GetExecutiveDashboardUseCase:
    """
    Orchestrates high-level business metrics for the SCMD Executive Dashboard.
    Rule 3.2: Contains all aggregation logic, keeping Views thin.
    """
    @staticmethod
    def execute(user, tenant_id):
        from django.db.models import Count, Q, Sum
        from datetime import timedelta
        from accounting.models_soquy import SoQuy
        from clients.models import HopDong, KhachHangTiemNang, MucTieu
        from inventory.models import VatTu
        from operations.models import BaoCaoSuCo, PhanCongCaTruc
        from users.models import NhanVien
        from workflow.models import Proposal, Task

        now = timezone.localtime()
        today = now.date()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        open_incident_statuses = ["CHO_XU_LY", "DANG_XU_LY"]

        # 1. Personnel Stats (With Tenant Isolation)
        nv_qs = NhanVien.objects.all() # Giả định manager đã hỗ trợ multi-tenancy hoặc dùng default
        tong_nv = nv_qs.count()
        nv_chinh_thuc = nv_qs.filter(trang_thai_lam_viec="CHINHTHUC").count()
        nv_thu_viec = nv_qs.filter(trang_thai_lam_viec="THUVIEC").count()
        nv_moi = nv_qs.filter(ngay_vao_lam=today).count()

        # 2. Revenue & CRM
        tong_kh = KhachHangTiemNang.objects.count()
        kh_moi = KhachHangTiemNang.objects.filter(ngay_tao__gte=start_of_month).count()
        muc_tieu_active = MucTieu.objects.filter(hop_dong__trang_thai="HIEU_LUC").count()
        
        rev_expected = HopDong.objects.filter(trang_thai="HIEU_LUC").aggregate(total=Sum("gia_tri"))["total"] or 0
        
        # 3. Financial Snapshot
        so_quy_qs = SoQuy.objects.filter(ngay_lap__month=today.month, ngay_lap__year=today.year)
        thuc_thu = so_quy_qs.filter(loai_phieu="THU").aggregate(total=Sum("so_tien"))["total"] or 0
        thuc_chi = so_quy_qs.filter(loai_phieu="CHI").aggregate(total=Sum("so_tien"))["total"] or 0

        # 4. Operations Real-time
        shifts_today = PhanCongCaTruc.objects.filter(ngay_truc=today)
        tong_ca = shifts_today.count()
        da_checkin = shifts_today.filter(chamcong__thoi_gian_check_in__isnull=False).distinct().count()
        
        # 5. Incidents & Alerts
        su_co_qs = BaoCaoSuCo.objects.filter(trang_thai__in=open_incident_statuses)
        count_su_co = su_co_qs.count()
        su_co_nghiem_trong = su_co_qs.filter(muc_do__in=["CAO", "NGUY_HIEM"]).count()
        
        canh_bao_kho = VatTu.objects.filter(so_luong_ton__lte=10).count()

        # 6. Workflow scoping
        de_xuat_can_duyet = 0
        cong_viec_cua_toi = 0
        if hasattr(user, "nhan_vien"):
            nv = user.nhan_vien
            de_xuat_can_duyet = Proposal.objects.filter(trang_thai__in=["MOI", "DANG_XU_LY"]).count()
            cong_viec_cua_toi = Task.objects.filter(nguoi_nhan=nv, trang_thai__in=["MOI", "DANG_THUC_HIEN"]).count()

        # 7. Operational Status Logic (Consolidated)
        ca_chua_checkin = max(tong_ca - da_checkin, 0)
        if su_co_nghiem_trong > 0:
            status_label, status_tone = "Canh bao", "danger"
            status_detail = f"{su_co_nghiem_trong} su co nghiem trong dang mo."
        elif count_su_co > 0 or ca_chua_checkin > 0:
            status_label, status_tone = "Can theo doi", "warning"
            status_detail = f"{count_su_co} su co mo, {ca_chua_checkin} ca chua check-in."
        elif tong_ca > 0 and da_checkin == tong_ca:
            status_label, status_tone = "On dinh", "success"
            status_detail = "Tat ca ca hom nay da co check-in hop le."
        else:
            status_label, status_tone = "Chua du du lieu", "neutral"
            status_detail = "He thong can thiet lap du lieu de phan anh chinh xac."

        # 8. Charts Data (Last 7 days)
        chart_labels, data_su_co, data_doanh_thu = [], [], []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            chart_labels.append(d.strftime("%d/%m"))
            data_su_co.append(BaoCaoSuCo.objects.filter(created_at__date=d).count())
            daily_rev = HopDong.objects.filter(ngay_ky=d).aggregate(val=Sum("gia_tri"))["val"] or 0
            data_doanh_thu.append(int(daily_rev / 12) if daily_rev else 0)

        return {
            "tong_nhan_vien": tong_nv,
            "nv_chinh_thuc": nv_chinh_thuc,
            "nv_thu_viec": nv_thu_viec,
            "nv_moi": nv_moi,
            "nhan_su_hoat_dong": nv_chinh_thuc + nv_thu_viec,
            "tong_khach_hang": tong_kh,
            "khach_hang_moi": kh_moi,
            "muc_tieu_dang_hoat_dong": muc_tieu_active,
            "doanh_thu_du_kien": rev_expected,
            "loi_nhuan_thuc": thuc_thu - thuc_chi,
            "tong_ca": tong_ca,
            "da_checkin": da_checkin,
            "ca_chua_checkin": ca_chua_checkin,
            "ty_le_quan_so": int((da_checkin / tong_ca) * 100) if tong_ca > 0 else 0,
            "count_su_co": count_su_co,
            "su_co_moi": BaoCaoSuCo.objects.filter(trang_thai="CHO_XU_LY").count(),
            "su_co_nghiem_trong": su_co_nghiem_trong,
            "ds_su_co": su_co_qs.select_related("muc_tieu").order_by("-created_at")[:5],
            "canh_bao_kho": canh_bao_kho,
            "tinh_trang_van_hanh": status_label,
            "tinh_trang_van_hanh_tone": status_tone,
            "tinh_trang_van_hanh_detail": status_detail,
            "de_xuat_can_duyet": de_xuat_can_duyet,
            "cong_viec_cua_toi": cong_viec_cua_toi,
            "chart_labels": chart_labels,
            "data_su_co": data_su_co,
            "data_doanh_thu": data_doanh_thu,
            "has_chart_data": any(data_su_co) or any(data_doanh_thu),
            "trang_thai_muc_tieu": GetExecutiveDashboardUseCase._get_target_statuses(today, open_incident_statuses)
        }

    @staticmethod
    def _get_target_statuses(today, open_incident_statuses):
        """Helper to get annotated target statuses for the dashboard."""
        from django.db.models import Count, Q
        from clients.models import MucTieu
        
        targets = MucTieu.objects.filter(hop_dong__trang_thai="HIEU_LUC").annotate(
            su_co_mo=Count(
                "cac_su_co",
                filter=Q(cac_su_co__trang_thai__in=open_incident_statuses),
                distinct=True,
            ),
            ca_hom_nay=Count(
                "cac_vi_tri_chot__cac_phan_cong",
                filter=Q(cac_vi_tri_chot__cac_phan_cong__ngay_truc=today),
                distinct=True,
            ),
            ca_da_checkin=Count(
                "cac_vi_tri_chot__cac_phan_cong",
                filter=Q(
                    cac_vi_tri_chot__cac_phan_cong__ngay_truc=today,
                    cac_vi_tri_chot__cac_phan_cong__chamcong__thoi_gian_check_in__isnull=False,
                ),
                distinct=True,
            ),
        ).order_by("ten_muc_tieu")[:4]

        for mt in targets:
            if mt.su_co_mo > 0:
                mt.dashboard_status_label, mt.dashboard_status_tone = "Co su co mo", "danger"
            elif mt.ca_hom_nay > 0 and mt.ca_da_checkin < mt.ca_hom_nay:
                mt.dashboard_status_label, mt.dashboard_status_tone = "Thieu du lieu", "warning"
            elif mt.ca_hom_nay > 0:
                mt.dashboard_status_label, mt.dashboard_status_tone = "On dinh", "success"
            else:
                mt.dashboard_status_label, mt.dashboard_status_tone = "Chua co ca", "neutral"
        return list(targets)