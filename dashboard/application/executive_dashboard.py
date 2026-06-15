# -*- coding: utf-8 -*-
"""
Application-layer executive dashboard orchestration.
"""

from datetime import datetime, time, timedelta

from django.db.models import Count, F, Q, Subquery, Sum
from django.utils import timezone
from django.db.models.functions import TruncDate


TARGET_STATUS_LIMIT = 300


class GetExecutiveDashboardUseCase:
    """
    Orchestrates high-level business metrics for the SCMD executive dashboard.
    """

    @staticmethod
    def execute(user, tenant_id):
        from accounting.models_soquy import SoQuy
        from clients.models import HopDong, KhachHangTiemNang, MucTieu
        from inventory.models import VatTu
        from operations.models import BaoCaoSuCo, PhanCongCaTruc
        from users.models import ACTIVE_EMPLOYEE_STATUSES, NhanVien
        from workflow.models import Proposal

        now = timezone.localtime()
        today = now.date()
        yesterday = today - timedelta(days=1)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)
        yesterday_start = today_start - timedelta(days=1)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        open_incident_statuses = ["CHO_XU_LY", "DANG_XU_LY", "DA_XU_LY", "CHO_DEN_BU"]

        nv_qs = NhanVien.objects.for_tenant(tenant_id).filter(
            trang_thai_lam_viec__in=ACTIVE_EMPLOYEE_STATUSES
        )

        # Optimization: Gom nhiều lệnh count vào 1 query duy nhất qua Conditional Aggregation (Rule 2.1)
        nv_stats = nv_qs.aggregate(
            total=Count('id'),
            chinh_thuc=Count('id', filter=Q(trang_thai_lam_viec=NhanVien.TrangThaiLamViec.CHINH_THUC)),
            thu_viec=Count('id', filter=Q(trang_thai_lam_viec=NhanVien.TrangThaiLamViec.THU_VIEC)),
            moi=Count('id', filter=Q(ngay_vao_lam=today))
        )

        kh_qs = KhachHangTiemNang.objects.for_tenant(tenant_id)
        hop_dong_qs = HopDong.objects.for_tenant(tenant_id)
        # MucTieu may not expose a direct tenant_id field in older deployments.
        # Scope it through HopDong to avoid FieldError on /dashboard/.
        scoped_muc_tieu_qs = GetExecutiveDashboardUseCase._muc_tieu_for_tenant(
            MucTieu, tenant_id, hop_dong_qs
        )
        
        kh_stats = kh_qs.aggregate(
            total=Count('id'),
            moi=Count('id', filter=Q(ngay_tao__gte=start_of_month))
        )

        muc_tieu_active = scoped_muc_tieu_qs.filter(hop_dong__trang_thai="HIEU_LUC").count()
        rev_expected = (
            hop_dong_qs.filter(trang_thai="HIEU_LUC").aggregate(total=Sum("gia_tri"))["total"] or 0
        )

        so_quy_qs = SoQuy.objects.for_tenant(tenant_id).filter(
            ngay_lap__month=today.month,
            ngay_lap__year=today.year,
        )
        so_quy_stats = so_quy_qs.aggregate(
            thu=Sum("so_tien", filter=Q(loai_phieu="THU")),
            chi=Sum("so_tien", filter=Q(loai_phieu="CHI"))
        )

        # Gộp thống kê ca trực hôm nay và hôm qua vào 1 query duy nhất
        all_shift_stats = PhanCongCaTruc.objects.for_tenant(tenant_id).filter(
            ngay_truc__in=[today, yesterday]
        ).aggregate(
            total_today=Count('id', filter=Q(ngay_truc=today)),
            checkin_today=Count('id', filter=Q(ngay_truc=today, chamcong__thoi_gian_check_in__isnull=False), distinct=True),
            total_yesterday=Count('id', filter=Q(ngay_truc=yesterday)),
            checkin_yesterday=Count('id', filter=Q(ngay_truc=yesterday, chamcong__thoi_gian_check_in__isnull=False), distinct=True)
        )

        ty_le_quan_so = int((all_shift_stats["checkin_today"] / all_shift_stats["total_today"]) * 100) if all_shift_stats["total_today"] > 0 else 0
        ty_le_quan_so_hom_qua = int((all_shift_stats["checkin_yesterday"] / all_shift_stats["total_yesterday"]) * 100) if all_shift_stats["total_yesterday"] > 0 else 0
        ca_chua_checkin = max(all_shift_stats["total_today"] - all_shift_stats["checkin_today"], 0)

        # Gộp thống kê sự cố (tổng cộng, nghiêm trọng, hôm nay, hôm qua) vào 1 query duy nhất
        su_co_aggregate = BaoCaoSuCo.objects.for_tenant(tenant_id).aggregate(
            total_open=Count('id', filter=Q(trang_thai__in=open_incident_statuses)),
            nghiem_trong=Count('id', filter=Q(trang_thai__in=open_incident_statuses, muc_do__in=["CAO", "NGUY_HIEM"])),
            moi_cho_xu_ly=Count('id', filter=Q(trang_thai="CHO_XU_LY")),
            hom_nay=Count('id', filter=Q(created_at__gte=today_start, created_at__lt=tomorrow_start)),
            hom_qua=Count('id', filter=Q(created_at__gte=yesterday_start, created_at__lt=today_start))
        )
        
        count_su_co = su_co_aggregate['total_open']
        su_co_nghiem_trong = su_co_aggregate['nghiem_trong']
        su_co_moi = su_co_aggregate['moi_cho_xu_ly']
        su_co_hom_nay = su_co_aggregate['hom_nay']
        count_su_co_hom_qua = su_co_aggregate['hom_qua']

        canh_bao_kho = VatTu.objects.for_tenant(tenant_id).filter(so_luong_ton__lte=10).count()

        # Single-organization exception: workflow models do not expose a tenant-scoped manager yet.
        de_xuat_qs = Proposal.objects.filter(trang_thai__in=["MOI", "DANG_XU_LY"])
        de_xuat_can_duyet = de_xuat_qs.count()
        proposal_window_start = today_start - timedelta(days=6)
        de_xuat_7_ngay = de_xuat_qs.filter(ngay_tao__gte=proposal_window_start).count()

        target_statuses = GetExecutiveDashboardUseCase._get_target_statuses(
            today, open_incident_statuses, tenant_id
        )
        muc_tieu_rui_ro = sum(
            1 for item in target_statuses if item.dashboard_status_tone in {"warning", "danger"}
        )
        muc_tieu_rui_ro_hom_qua = GetExecutiveDashboardUseCase._count_risky_targets_for_day(
            yesterday,
            open_incident_statuses,
            tenant_id,
        )

        chart_labels, data_su_co, data_doanh_thu = GetExecutiveDashboardUseCase._build_chart_series(
            today, tenant_id, hop_dong_qs
        )
        doanh_thu_7_ngay = sum(data_doanh_thu)
        doanh_thu_7_ngay_truoc = GetExecutiveDashboardUseCase._sum_projected_revenue_for_period(
            hop_dong_qs,
            today - timedelta(days=13),
            today - timedelta(days=7),
        )

        canh_bao_nhanh = []
        if su_co_nghiem_trong > 0:
            canh_bao_nhanh.append(f"{su_co_nghiem_trong} sự cố nghiêm trọng đang mở")
        if ca_chua_checkin > 0:
            canh_bao_nhanh.append(f"{ca_chua_checkin} ca chưa check-in")
        if canh_bao_kho > 0:
            canh_bao_nhanh.append(f"{canh_bao_kho} vật tư dưới ngưỡng tồn")
        if de_xuat_can_duyet > 0:
            canh_bao_nhanh.append(f"{de_xuat_can_duyet} hồ sơ đang chờ duyệt")

        if su_co_nghiem_trong > 0:
            status_label, status_tone = "Cảnh báo", "danger"
            status_detail = f"{su_co_nghiem_trong} sự cố nghiêm trọng đang mở."
        elif count_su_co > 0 or ca_chua_checkin > 0:
            status_label, status_tone = "Cần theo dõi", "warning"
            status_detail = f"{count_su_co} sự cố mở, {ca_chua_checkin} ca chưa check-in."
        elif all_shift_stats["total_today"] > 0 and all_shift_stats["checkin_today"] == all_shift_stats["total_today"]:
            status_label, status_tone = "Ổn định", "success"
            status_detail = "Tất cả ca hôm nay đã có check-in hợp lệ."
        else:
            status_label, status_tone = "Chưa đủ dữ liệu", "neutral"
            status_detail = "Hệ thống cần thiết lập dữ liệu để phản ánh chính xác."

        cong_viec_can_xu_ly = []
        if su_co_nghiem_trong > 0:
            cong_viec_can_xu_ly.append(
                "Rà soát ngay các sự cố nghiêm trọng và người chịu trách nhiệm xử lý."
            )
        if ca_chua_checkin > 0:
            cong_viec_can_xu_ly.append(
                "Kiểm tra các ca chưa check-in để tránh thiếu dữ liệu chấm công cuối ngày."
            )
        if muc_tieu_rui_ro > 0:
            cong_viec_can_xu_ly.append(
                "Ưu tiên theo dõi các mục tiêu đang có rủi ro vận hành hoặc thiếu dữ liệu."
            )
        if de_xuat_can_duyet > 0:
            cong_viec_can_xu_ly.append(
                "Xử lý các hồ sơ đang chờ duyệt để tránh dồn việc điều hành."
            )
        if canh_bao_kho > 0:
            cong_viec_can_xu_ly.append(
                "Đối chiếu vật tư dưới ngưỡng tồn để không ảnh hưởng triển khai mục tiêu."
            )

        top_rui_ro = GetExecutiveDashboardUseCase._build_top_risks(
            count_su_co=count_su_co,
            su_co_nghiem_trong=su_co_nghiem_trong,
            ca_chua_checkin=ca_chua_checkin,
            muc_tieu_rui_ro=muc_tieu_rui_ro,
            canh_bao_kho=canh_bao_kho,
            de_xuat_can_duyet=de_xuat_can_duyet,
            trend_su_co=GetExecutiveDashboardUseCase._build_trend(
                su_co_hom_nay - count_su_co_hom_qua,
                "phát sinh so với hôm qua",
                positive_is_good=False,
            ),
            trend_quan_so=GetExecutiveDashboardUseCase._build_trend(
                ty_le_quan_so - ty_le_quan_so_hom_qua,
                "điểm so với hôm qua",
                positive_is_good=True,
            ),
            trend_muc_tieu=GetExecutiveDashboardUseCase._build_trend(
                muc_tieu_rui_ro - muc_tieu_rui_ro_hom_qua,
                "so với hôm qua",
                positive_is_good=False,
            ),
            trend_de_xuat=GetExecutiveDashboardUseCase._build_volume_note(
                de_xuat_7_ngay,
                "hồ sơ mới trong 7 ngày",
                tone="info" if de_xuat_can_duyet > 0 else "neutral",
            ),
        )

        top_muc_tieu_can_theo_doi = [item for item in target_statuses if item.risk_score > 0][:5]
        if not top_muc_tieu_can_theo_doi:
            top_muc_tieu_can_theo_doi = target_statuses[:5]
        recent_open_incidents = list(
            BaoCaoSuCo.objects.for_tenant(tenant_id)
            .filter(trang_thai__in=open_incident_statuses)
            .select_related("muc_tieu")
            .order_by("-created_at")[:5]
        )
        has_trend_section = any(data_su_co) or any(data_doanh_thu)

        return {
            "tong_nhan_vien": nv_stats["total"],
            "nv_chinh_thuc": nv_stats["chinh_thuc"],
            "nv_thu_viec": nv_stats["thu_viec"],
            "nv_moi": nv_stats["moi"],
            "nhan_su_hoat_dong": nv_stats["chinh_thuc"] + nv_stats["thu_viec"],
            "tong_khach_hang": kh_stats["total"],
            "khach_hang_moi": kh_stats["moi"],
            "muc_tieu_dang_hoat_dong": muc_tieu_active,
            "doanh_thu_du_kien": rev_expected,
            "loi_nhuan_thuc": (so_quy_stats["thu"] or 0) - (so_quy_stats["chi"] or 0),
            "tong_ca": all_shift_stats["total_today"],
            "da_checkin": all_shift_stats["checkin_today"],
            "ca_chua_checkin": ca_chua_checkin,
            "ty_le_quan_so": ty_le_quan_so,
            "muc_tieu_rui_ro": muc_tieu_rui_ro,
            "count_su_co": count_su_co,
            "su_co_moi": su_co_moi,
            "su_co_nghiem_trong": su_co_nghiem_trong,
            "su_co_nong": recent_open_incidents,
            "canh_bao_kho": canh_bao_kho,
            "tinh_trang_van_hanh": status_label,
            "tinh_trang_van_hanh_tone": status_tone,
            "tinh_trang_van_hanh_detail": status_detail,
            "de_xuat_can_duyet": de_xuat_can_duyet,
            "canh_bao_nhanh": canh_bao_nhanh[:4],
            "cong_viec_can_xu_ly": cong_viec_can_xu_ly[:5],
            "top_rui_ro": top_rui_ro[:5],
            "top_muc_tieu_can_theo_doi": top_muc_tieu_can_theo_doi,
            "chart_labels": chart_labels,
            "data_su_co": data_su_co,
            "data_doanh_thu": data_doanh_thu,
            "has_incident_chart_data": any(data_su_co),
            "has_revenue_chart_data": any(data_doanh_thu),
            "has_trend_section": has_trend_section,
            "dashboard_scope_label": "Phạm vi tổ chức đã được cấp quyền",
            "dashboard_timeframe_label": f"Ngày {today.strftime('%d/%m/%Y')}",
            "open_incidents": count_su_co,
            "high_severity_incidents": su_co_nghiem_trong,
            "new_incidents_today": su_co_hom_nay,
            "unchecked_shifts_today": ca_chua_checkin,
            "total_shifts_today": all_shift_stats["total_today"],
            "coverage_rate_today": ty_le_quan_so,
            "active_targets": muc_tieu_active,
            "risk_targets": muc_tieu_rui_ro,
            "pending_approvals": de_xuat_can_duyet,
            "inventory_alerts": canh_bao_kho,
            "projected_revenue_this_month": rev_expected,
            "realized_profit_this_month": (so_quy_stats["thu"] or 0) - (so_quy_stats["chi"] or 0),
            "top_risk_targets": top_muc_tieu_can_theo_doi,
            "recent_open_incidents": recent_open_incidents,
            "trend_quan_so": GetExecutiveDashboardUseCase._build_trend(
                ty_le_quan_so - ty_le_quan_so_hom_qua,
                "điểm so với hôm qua",
                positive_is_good=True,
            ),
            "trend_su_co": GetExecutiveDashboardUseCase._build_trend(
                su_co_hom_nay - count_su_co_hom_qua,
                "phát sinh so với hôm qua",
                positive_is_good=False,
            ),
            "trend_muc_tieu_rui_ro": GetExecutiveDashboardUseCase._build_trend(
                muc_tieu_rui_ro - muc_tieu_rui_ro_hom_qua,
                "so với hôm qua",
                positive_is_good=False,
            ),
            "trend_de_xuat": GetExecutiveDashboardUseCase._build_volume_note(
                de_xuat_7_ngay,
                "hồ sơ mới trong 7 ngày",
                tone="info" if de_xuat_can_duyet > 0 else "neutral",
            ),
            "trend_doanh_thu_7_ngay": GetExecutiveDashboardUseCase._build_trend(
                doanh_thu_7_ngay - doanh_thu_7_ngay_truoc,
                "so với 7 ngày trước",
                positive_is_good=True,
            ),
        }

    @staticmethod
    def _build_chart_series(today, tenant_id, hop_dong_qs):
        from operations.models import BaoCaoSuCo

        chart_labels = []
        start_date = today - timedelta(days=6)

        # Optimization: range filter preserves created_at index; TruncDate is only used after filtering.
        range_start = timezone.make_aware(datetime.combine(start_date, time.min))
        range_end = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min))
        incident_counts = (
            BaoCaoSuCo.objects.for_tenant(tenant_id)
            .filter(created_at__gte=range_start, created_at__lt=range_end)
            .annotate(day=TruncDate('created_at', tzinfo=timezone.get_current_timezone()))
            .values('day')
            .annotate(count=Count('id'))
        )
        incident_map = {item['day']: item['count'] for item in incident_counts}

        # Optimization: Tương tự cho dữ liệu doanh thu
        revenue_data = (
            hop_dong_qs.filter(ngay_ky__range=(start_date, today))
            .values('ngay_ky')
            .annotate(total_val=Sum('gia_tri'))
        )
        revenue_map = {item['ngay_ky']: item['total_val'] for item in revenue_data}

        data_su_co = []
        data_doanh_thu = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            chart_labels.append(day.strftime("%d/%m"))
            data_su_co.append(incident_map.get(day, 0))
            daily_rev = revenue_map.get(day, 0)
            data_doanh_thu.append(int(daily_rev / 12) if daily_rev else 0)

        return chart_labels, data_su_co, data_doanh_thu

    @staticmethod
    def _sum_projected_revenue_for_period(hop_dong_qs, start_date, end_date):
        # Optimization: Sử dụng range aggregation thay vì vòng lặp ngày (Rule 2.1)
        total_rev = (
            hop_dong_qs.filter(ngay_ky__range=(start_date, end_date))
            .aggregate(val=Sum("gia_tri"))["val"] or 0
        )
        return int(total_rev / 12)

    @staticmethod
    def _build_trend(delta, suffix, positive_is_good):
        if delta == 0:
            return {
                "delta": 0,
                "tone": "neutral",
                "text": f"Không đổi {suffix}",
            }

        is_positive = delta > 0
        tone = "success" if is_positive == positive_is_good else "danger"
        sign = "+" if is_positive else ""
        return {
            "delta": delta,
            "tone": tone,
            "text": f"{sign}{delta} {suffix}",
        }

    @staticmethod
    def _build_volume_note(value, suffix, tone="neutral"):
        return {
            "delta": value,
            "tone": tone,
            "text": f"{value} {suffix}",
        }

    @staticmethod
    def _build_top_risks(
        *,
        count_su_co,
        su_co_nghiem_trong,
        ca_chua_checkin,
        muc_tieu_rui_ro,
        canh_bao_kho,
        de_xuat_can_duyet,
        trend_su_co,
        trend_quan_so,
        trend_muc_tieu,
        trend_de_xuat,
    ):
        items = []

        if su_co_nghiem_trong > 0 or count_su_co > 0:
            items.append(
                {
                    "title": "Sự cố hiện trường",
                    "detail": f"{su_co_nghiem_trong} sự cố nghiêm trọng trong tổng số {count_su_co} hồ sơ đang mở.",
                    "metric": f"{count_su_co} hồ sơ",
                    "tone": "danger" if su_co_nghiem_trong > 0 else "warning",
                    "trend": trend_su_co,
                    "progress_pct": min(100, su_co_nghiem_trong * 25 if su_co_nghiem_trong else count_su_co * 10),
                    "progress_label": "Mức độ ưu tiên xử lý sự cố",
                    "action_key": "incidents",
                    "action_label": "Xem danh sách sự cố",
                }
            )

        if ca_chua_checkin > 0:
            items.append(
                {
                    "title": "Ca chưa check-in",
                    "detail": f"{ca_chua_checkin} ca hôm nay chưa có dữ liệu check-in hợp lệ.",
                    "metric": f"{ca_chua_checkin} ca",
                    "tone": "warning",
                    "trend": trend_quan_so,
                    "progress_pct": min(100, ca_chua_checkin * 12),
                    "progress_label": "Áp lực bổ sung dữ liệu đầu ca",
                    "action_key": "operations",
                    "action_label": "Mở dashboard vận hành",
                }
            )

        if muc_tieu_rui_ro > 0:
            items.append(
                {
                    "title": "Mục tiêu cần theo dõi",
                    "detail": f"{muc_tieu_rui_ro} mục tiêu đang có sự cố mở hoặc thiếu dữ liệu ca trực.",
                    "metric": f"{muc_tieu_rui_ro} mục tiêu",
                    "tone": "warning",
                    "trend": trend_muc_tieu,
                    "progress_pct": min(100, muc_tieu_rui_ro * 20),
                    "progress_label": "Áp lực điều phối mục tiêu",
                    "action_key": "operations",
                    "action_label": "Xem mục tiêu vận hành",
                }
            )

        if canh_bao_kho > 0:
            items.append(
                {
                    "title": "Vật tư dưới ngưỡng tồn",
                    "detail": f"{canh_bao_kho} vật tư cần đối chiếu để tránh ảnh hưởng triển khai mục tiêu.",
                    "metric": f"{canh_bao_kho} vật tư",
                    "tone": "warning",
                    "trend": {"delta": 0, "tone": "neutral", "text": "Theo dõi cùng dashboard kho"},
                    "progress_pct": min(100, canh_bao_kho * 10),
                    "progress_label": "Mức độ thiếu hụt vật tư",
                    "action_key": "inventory",
                    "action_label": "Mở dashboard kho",
                }
            )

        if de_xuat_can_duyet > 0:
            items.append(
                {
                    "title": "Hồ sơ chờ duyệt",
                    "detail": f"{de_xuat_can_duyet} hồ sơ đang chờ xử lý, cần tránh dồn quyết định cuối kỳ.",
                    "metric": f"{de_xuat_can_duyet} hồ sơ",
                    "tone": "info",
                    "trend": trend_de_xuat,
                    "progress_pct": min(100, de_xuat_can_duyet * 10),
                    "progress_label": "Áp lực phê duyệt điều hành",
                    "action_key": "workflow",
                    "action_label": "Mở danh sách hồ sơ",
                }
            )

        if not items:
            items.append(
                {
                    "title": "Không có rủi ro nổi bật",
                    "detail": "Dashboard chưa ghi nhận sự cố mở, thiếu check-in hoặc cảnh báo kho đáng chú ý.",
                    "metric": "Ổn định",
                    "tone": "success",
                    "trend": {"delta": 0, "tone": "success", "text": "Ổn định so với hôm qua"},
                    "progress_pct": 100,
                    "progress_label": "Mức ổn định vận hành",
                    "action_key": "reports",
                    "action_label": "Xem báo cáo tổng hợp",
                }
            )

        tone_weight = {"danger": 3, "warning": 2, "info": 1, "success": 0}
        return sorted(items, key=lambda item: tone_weight.get(item["tone"], 0), reverse=True)


    @staticmethod
    def _muc_tieu_for_tenant(MucTieu, tenant_id, hop_dong_qs=None):
        """
        Return organization-scoped MucTieu records without assuming MucTieu has
        a physical tenant_id column. Some deployed schemas inherit scope from
        HopDong via `hop_dong__tenant_id`; using the base TenantAwareManager on
        MucTieu would raise FieldError: Cannot resolve keyword 'tenant_id'.
        """
        qs = MucTieu.objects.select_related("hop_dong")

        field_names = {field.name for field in MucTieu._meta.get_fields()}
        if "tenant_id" in field_names:
            return qs.filter(tenant_id=tenant_id)

        if hop_dong_qs is not None:
            return qs.filter(hop_dong__in=hop_dong_qs)

        return qs.filter(hop_dong__tenant_id=tenant_id)

    @staticmethod
    def _count_risky_targets_for_day(day, open_incident_statuses, tenant_id):
        """Count risky targets for trend without building yesterday's detail list."""
        from clients.models import MucTieu
        from operations.models import BaoCaoSuCo, PhanCongCaTruc

        active_target_ids = GetExecutiveDashboardUseCase._muc_tieu_for_tenant(
            MucTieu,
            tenant_id,
        ).filter(hop_dong__trang_thai="HIEU_LUC").values("id")

        incident_target_ids = set(
            BaoCaoSuCo.objects.for_tenant(tenant_id)
            .filter(
                muc_tieu_id__in=Subquery(active_target_ids),
                trang_thai__in=open_incident_statuses,
            )
            .exclude(muc_tieu_id__isnull=True)
            .values_list("muc_tieu_id", flat=True)
            .distinct()
        )
        missing_shift_target_ids = set(
            PhanCongCaTruc.objects.for_tenant(tenant_id)
            .filter(
                vi_tri_chot__muc_tieu_id__in=Subquery(active_target_ids),
                ngay_truc=day,
            )
            .values("vi_tri_chot__muc_tieu_id")
            .annotate(
                total=Count("id"),
                checked_in=Count(
                    "id",
                    filter=Q(chamcong__thoi_gian_check_in__isnull=False),
                    distinct=True,
                ),
            )
            .filter(total__gt=F("checked_in"))
            .values_list("vi_tri_chot__muc_tieu_id", flat=True)
        )
        return len(incident_target_ids | missing_shift_target_ids)

    @staticmethod
    def _get_target_statuses(today, open_incident_statuses, tenant_id):
        from clients.models import MucTieu
        from operations.models import BaoCaoSuCo, PhanCongCaTruc

        scoped_targets = GetExecutiveDashboardUseCase._muc_tieu_for_tenant(MucTieu, tenant_id)

        targets = list(
            scoped_targets
            .filter(hop_dong__trang_thai="HIEU_LUC")
            .order_by("ten_muc_tieu")[:TARGET_STATUS_LIMIT]
        )
        target_ids = [target.id for target in targets]
        if not target_ids:
            return []

        incident_counts = {
            row["muc_tieu_id"]: row["total"]
            for row in (
                BaoCaoSuCo.objects.for_tenant(tenant_id)
                .filter(muc_tieu_id__in=target_ids, trang_thai__in=open_incident_statuses)
                .values("muc_tieu_id")
                .annotate(total=Count("id"))
            )
        }
        shift_counts = {
            row["vi_tri_chot__muc_tieu_id"]: row
            for row in (
                PhanCongCaTruc.objects.for_tenant(tenant_id)
                .filter(vi_tri_chot__muc_tieu_id__in=target_ids, ngay_truc=today)
                .values("vi_tri_chot__muc_tieu_id")
                .annotate(
                    total=Count("id"),
                    checked_in=Count(
                        "id",
                        filter=Q(chamcong__thoi_gian_check_in__isnull=False),
                        distinct=True,
                    ),
                )
            )
        }

        enriched = []
        for mt in targets:
            mt.su_co_mo = incident_counts.get(mt.id, 0)
            shift_stat = shift_counts.get(mt.id, {})
            mt.ca_hom_nay = shift_stat.get("total", 0)
            mt.ca_da_checkin = shift_stat.get("checked_in", 0)
            mt.ca_thieu = max(mt.ca_hom_nay - mt.ca_da_checkin, 0)
            mt.tien_do_pct = int((mt.ca_da_checkin / mt.ca_hom_nay) * 100) if mt.ca_hom_nay > 0 else 0

            if mt.su_co_mo > 0:
                mt.dashboard_status_label, mt.dashboard_status_tone = "Có sự cố mở", "danger"
                mt.dashboard_status_detail = f"{mt.su_co_mo} sự cố mở cần theo dõi."
            elif mt.ca_hom_nay > 0 and mt.ca_da_checkin < mt.ca_hom_nay:
                mt.dashboard_status_label, mt.dashboard_status_tone = "Thiếu dữ liệu", "warning"
                mt.dashboard_status_detail = f"Thiếu {mt.ca_thieu} ca chưa check-in."
            elif mt.ca_hom_nay > 0:
                mt.dashboard_status_label, mt.dashboard_status_tone = "Ổn định", "success"
                mt.dashboard_status_detail = "Các ca hôm nay đã có check-in hợp lệ."
            else:
                mt.dashboard_status_label, mt.dashboard_status_tone = "Chưa có ca", "neutral"
                mt.dashboard_status_detail = "Chưa phát sinh ca trực trong ngày."

            mt.progress_label = (
                f"{mt.ca_da_checkin}/{mt.ca_hom_nay} ca đã check-in"
                if mt.ca_hom_nay
                else "Chưa phát sinh ca trực hôm nay"
            )
            mt.risk_score = (mt.su_co_mo * 100) + (mt.ca_thieu * 10) + (0 if mt.ca_hom_nay else -1)
            enriched.append(mt)

        return sorted(
            enriched,
            key=lambda item: (item.risk_score, item.ca_hom_nay, item.ten_muc_tieu),
            reverse=True,
        )
