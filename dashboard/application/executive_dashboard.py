# -*- coding: utf-8 -*-
"""
Application-layer executive dashboard orchestration.
"""

from django.utils import timezone


class GetExecutiveDashboardUseCase:
    """
    Orchestrates high-level business metrics for the SCMD executive dashboard.
    """

    @staticmethod
    def execute(user, tenant_id):
        from django.db.models import Sum
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

        # NhanVien currently has no direct tenant field. This uses an explicit
        # single-organization employee scope instead of an unbounded `.all()`.
        nv_qs = NhanVien.objects.filter(
            trang_thai_lam_viec__in=["THUVIEC", "CHINHTHUC", "TAMHOAN", "NGHIVIEC"]
        )
        tong_nv = nv_qs.count()
        nv_chinh_thuc = nv_qs.filter(trang_thai_lam_viec="CHINHTHUC").count()
        nv_thu_viec = nv_qs.filter(trang_thai_lam_viec="THUVIEC").count()
        nv_moi = nv_qs.filter(ngay_vao_lam=today).count()

        kh_qs = KhachHangTiemNang.objects.for_tenant(tenant_id)
        hop_dong_qs = HopDong.objects.for_tenant(tenant_id)
        muc_tieu_qs = MucTieu.objects.for_tenant(tenant_id)
        tong_kh = kh_qs.count()
        kh_moi = kh_qs.filter(ngay_tao__gte=start_of_month).count()
        muc_tieu_active = muc_tieu_qs.filter(hop_dong__trang_thai="HIEU_LUC").count()
        rev_expected = hop_dong_qs.filter(trang_thai="HIEU_LUC").aggregate(total=Sum("gia_tri"))["total"] or 0

        so_quy_qs = SoQuy.objects.filter(ngay_lap__month=today.month, ngay_lap__year=today.year)
        thuc_thu = so_quy_qs.filter(loai_phieu="THU").aggregate(total=Sum("so_tien"))["total"] or 0
        thuc_chi = so_quy_qs.filter(loai_phieu="CHI").aggregate(total=Sum("so_tien"))["total"] or 0

        shifts_today = PhanCongCaTruc.objects.for_tenant(tenant_id).filter(ngay_truc=today)
        tong_ca = shifts_today.count()
        da_checkin = shifts_today.filter(chamcong__thoi_gian_check_in__isnull=False).distinct().count()

        su_co_qs = BaoCaoSuCo.objects.for_tenant(tenant_id).filter(trang_thai__in=open_incident_statuses)
        count_su_co = su_co_qs.count()
        su_co_nghiem_trong = su_co_qs.filter(muc_do__in=["CAO", "NGUY_HIEM"]).count()

        canh_bao_kho = VatTu.objects.filter(so_luong_ton__lte=10).count()

        de_xuat_can_duyet = 0
        cong_viec_cua_toi = 0
        if hasattr(user, "nhan_vien"):
            nv = user.nhan_vien
            de_xuat_can_duyet = Proposal.objects.filter(trang_thai__in=["MOI", "DANG_XU_LY"]).count()
            cong_viec_cua_toi = Task.objects.filter(nguoi_nhan=nv, trang_thai__in=["MOI", "DANG_THUC_HIEN"]).count()

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

        chart_labels, data_su_co, data_doanh_thu = [], [], []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            chart_labels.append(d.strftime("%d/%m"))
            data_su_co.append(BaoCaoSuCo.objects.for_tenant(tenant_id).filter(created_at__date=d).count())
            daily_rev = hop_dong_qs.filter(ngay_ky=d).aggregate(val=Sum("gia_tri"))["val"] or 0
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
            "su_co_moi": BaoCaoSuCo.objects.for_tenant(tenant_id).filter(trang_thai="CHO_XU_LY").count(),
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
            "trang_thai_muc_tieu": GetExecutiveDashboardUseCase._get_target_statuses(today, open_incident_statuses, tenant_id),
        }

    @staticmethod
    def _get_target_statuses(today, open_incident_statuses, tenant_id):
        from django.db.models import Count, Q
        from clients.models import MucTieu

        targets = MucTieu.objects.for_tenant(tenant_id).filter(hop_dong__trang_thai="HIEU_LUC").annotate(
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
