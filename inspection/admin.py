# -*- coding: utf-8 -*-
"""Admin surfaces for inspection, patrol and training.

SCMD Pro admin is a technical console: keep the default Django Admin behavior,
add compact operational context, and avoid fake CTA routes.
"""

from __future__ import annotations

from datetime import timedelta
import csv

from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.http import HttpResponse
from django.urls import NoReverseMatch, path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from main.models import AuditLog

from .models import (
    BienBanThanhTra,
    BienBanViPham,
    BuoiHuanLuyen,
    DiemTuanTra,
    DotThanhTra,
    GhiNhanTuanTra,
    HangMucKiemTra,
    KetQuaKiemTra,
    LoaiTuanTra,
    LuotTuanTra,
)


def _safe_reverse(viewname: str, *, args=None, fallback: str = "#") -> str:
    try:
        return reverse(viewname, args=args)
    except NoReverseMatch:
        return fallback


def _admin_change_url(obj, fallback: str = "#") -> str:
    if not obj or not getattr(obj, "pk", None):
        return fallback
    meta = obj._meta
    return _safe_reverse(f"admin:{meta.app_label}_{meta.model_name}_change", args=[obj.pk], fallback=fallback)


def _admin_changelist_url(app_label: str, model_name: str, fallback: str = "#") -> str:
    return _safe_reverse(f"admin:{app_label}_{model_name}_changelist", fallback=fallback)


def _request_ip(request) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or ""


def _request_ua(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:1000]




def _audit_json_value(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)

def _append_query(url: str, params: dict[str, str]) -> str:
    if not url or url == "#":
        return url
    query = "&".join(f"{key}={value}" for key, value in params.items() if value is not None)
    if not query:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{query}"


class DiemTuanTraInline(admin.TabularInline):
    model = DiemTuanTra
    extra = 1
    fields = ("thu_tu", "ten_diem", "ma_qr", "vi_do", "kinh_do", "ban_kinh_cho_phep")
    verbose_name = _("Điểm QR/GPS")
    verbose_name_plural = _("Danh sách điểm QR/GPS")


class DiemTuanTraQualityFilter(admin.SimpleListFilter):
    title = _("Chất lượng điểm QR/GPS")
    parameter_name = "point_ops"

    def lookups(self, request, model_admin):
        return (
            ("with_coordinates", _("Đã có GPS")),
            ("missing_coordinates", _("Thiếu GPS")),
            ("radius_under_30", _("Bán kính dưới 30m")),
            ("radius_over_100", _("Bán kính trên 100m")),
            ("never_scanned", _("Chưa từng được quét")),
            ("scanned_today", _("Có quét hôm nay")),
            ("has_warning", _("Có cảnh báo GPS/gian lận")),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        value = self.value()
        if value == "with_coordinates":
            return queryset.filter(vi_do__isnull=False, kinh_do__isnull=False)
        if value == "missing_coordinates":
            return queryset.filter(Q(vi_do__isnull=True) | Q(kinh_do__isnull=True))
        if value == "radius_under_30":
            return queryset.filter(ban_kinh_cho_phep__lt=30)
        if value == "radius_over_100":
            return queryset.filter(ban_kinh_cho_phep__gt=100)
        if value == "never_scanned":
            return queryset.filter(scan_count=0)
        if value == "scanned_today":
            return queryset.filter(ghinhantuantra__thoi_gian_quet__date=today).distinct()
        if value == "has_warning":
            return queryset.filter(warning_scan_count__gt=0)
        return queryset


@admin.register(DiemTuanTra)
class DiemTuanTraAdmin(admin.ModelAdmin):
    change_list_template = "admin/inspection/diemtuantra/change_list.html"
    list_display = ("point_display", "route_site_display", "gps_display", "scan_usage_display", "config_status_display", "row_actions")
    list_filter = (DiemTuanTraQualityFilter, "loai_tuan_tra__muc_tieu", "loai_tuan_tra")
    list_select_related = ("loai_tuan_tra", "loai_tuan_tra__muc_tieu", "loai_tuan_tra__muc_tieu__hop_dong")
    search_fields = (
        "ten_diem",
        "ma_qr",
        "loai_tuan_tra__ten_loai",
        "loai_tuan_tra__muc_tieu__ten_muc_tieu",
        "loai_tuan_tra__muc_tieu__dia_chi",
    )
    readonly_fields = ("qr_identity_note",)
    list_per_page = 25
    save_on_top = True
    fieldsets = (
        (_("Thông tin điểm kiểm soát"), {"fields": (("loai_tuan_tra", "thu_tu"), ("ten_diem", "ma_qr"), "qr_identity_note")} ),
        (_("GPS & bán kính xác thực"), {"fields": (("vi_do", "kinh_do"), "ban_kinh_cho_phep")} ),
    )



    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inspection_diemtuantra_export_csv",
            ),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        today = timezone.localdate()
        return (
            super()
            .get_queryset(request)
            .select_related("loai_tuan_tra", "loai_tuan_tra__muc_tieu", "loai_tuan_tra__muc_tieu__hop_dong")
            .annotate(
                scan_count=Count("ghinhantuantra", distinct=True),
                today_scan_count=Count("ghinhantuantra", filter=Q(ghinhantuantra__thoi_gian_quet__date=today), distinct=True),
                valid_scan_count=Count("ghinhantuantra", filter=Q(ghinhantuantra__ket_qua="HOP_LE"), distinct=True),
                warning_scan_count=Count(
                    "ghinhantuantra",
                    filter=Q(ghinhantuantra__ket_qua__in=["CANH_BAO_XA", "MAT_GPS", "GIAN_LAN"]),
                    distinct=True,
                ),
            )
        )

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        today = timezone.localdate()
        base_url = _admin_changelist_url("inspection", "diemtuantra")
        current_query = request.GET.urlencode()
        export_url = _safe_reverse("admin:inspection_diemtuantra_export_csv")
        if current_query:
            export_url = f"{export_url}?{current_query}"
        extra_context = extra_context or {}
        extra_context.update(
            {
                "scmd_patrol_point_stats": {
                    "total": qs.count(),
                    "with_coordinates": qs.filter(vi_do__isnull=False, kinh_do__isnull=False).count(),
                    "missing_coordinates": qs.filter(Q(vi_do__isnull=True) | Q(kinh_do__isnull=True)).count(),
                    "radius_under_30": qs.filter(ban_kinh_cho_phep__lt=30).count(),
                    "radius_over_100": qs.filter(ban_kinh_cho_phep__gt=100).count(),
                    "never_scanned": qs.filter(scan_count=0).count(),
                    "scanned_today": qs.filter(ghinhantuantra__thoi_gian_quet__date=today).distinct().count(),
                    "has_warning": qs.filter(warning_scan_count__gt=0).count(),
                },
                "scmd_patrol_point_links": {
                    "list": base_url,
                    "add": _safe_reverse("admin:inspection_diemtuantra_add", fallback=base_url),
                    "export_csv": export_url,
                    "routes": _admin_changelist_url("inspection", "loaituantra", fallback=base_url),
                    "sessions": _admin_changelist_url("inspection", "luottuantra", fallback=base_url),
                    "scans": _admin_changelist_url("inspection", "ghinhantuantra", fallback=base_url),
                    "violations": _admin_changelist_url("inspection", "bienbanvipham", fallback=base_url),
                    "targets": _admin_changelist_url("clients", "muctieu", fallback=base_url),
                    "dashboard": _safe_reverse("inspection:dashboard", fallback=base_url),
                    "mobile": _safe_reverse("operations:mobile_tuan_tra_list", fallback=base_url),
                    "with_coordinates": _append_query(base_url, {"point_ops": "with_coordinates"}),
                    "missing_coordinates": _append_query(base_url, {"point_ops": "missing_coordinates"}),
                    "radius_under_30": _append_query(base_url, {"point_ops": "radius_under_30"}),
                    "radius_over_100": _append_query(base_url, {"point_ops": "radius_over_100"}),
                    "never_scanned": _append_query(base_url, {"point_ops": "never_scanned"}),
                    "scanned_today": _append_query(base_url, {"point_ops": "scanned_today"}),
                    "has_warning": _append_query(base_url, {"point_ops": "has_warning"}),
                },
            }
        )
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="scmd-pro-diem-tuan-tra.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Tuyến tuần tra vận hành",
            "Mục tiêu",
            "Thứ tự",
            "Tên điểm kiểm soát",
            "Mã QR",
            "Vĩ độ",
            "Kinh độ",
            "Bán kính cho phép (m)",
            "Tổng lượt quét",
            "Lượt quét hôm nay",
            "Lượt hợp lệ",
            "Lượt cảnh báo",
            "Tình trạng cấu hình",
        ])
        for obj in queryset.iterator(chunk_size=200):
            route = obj.loai_tuan_tra
            target = getattr(route, "muc_tieu", None) if route else None
            config_notes = []
            if obj.vi_do is None or obj.kinh_do is None:
                config_notes.append("Thiếu GPS")
            if obj.ban_kinh_cho_phep < 30:
                config_notes.append("Bán kính hẹp")
            if obj.ban_kinh_cho_phep > 100:
                config_notes.append("Bán kính rộng")
            if not config_notes:
                config_notes.append("Sẵn sàng")
            writer.writerow([
                getattr(route, "ten_loai", "") or "",
                getattr(target, "ten_muc_tieu", "") or "",
                obj.thu_tu,
                obj.ten_diem,
                obj.ma_qr,
                obj.vi_do or "",
                obj.kinh_do or "",
                obj.ban_kinh_cho_phep,
                getattr(obj, "scan_count", 0),
                getattr(obj, "today_scan_count", 0),
                getattr(obj, "valid_scan_count", 0),
                getattr(obj, "warning_scan_count", 0),
                "; ".join(config_notes),
            ])
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.ACCESS,
            module="inspection",
            model_name="DiemTuanTra",
            object_id="bulk-export",
            changes={"count": queryset.count(), "filters": request.GET.dict()},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xuất CSV danh sách điểm QR/GPS tuần tra từ Django Admin.",
        )
        return response

    @admin.display(description=_("Lưu ý định danh QR"))
    def qr_identity_note(self, obj=None):
        return _("Mã QR là định danh vận hành của điểm kiểm soát. Không nên đổi mã QR khi điểm đã phát sinh lịch sử quét nếu chưa có kế hoạch đối soát.")

    @admin.display(description=_("Điểm kiểm soát"))
    def point_display(self, obj):
        return format_html(
            '<div><b>[{}] {}</b><div style="font-size:12px;color:#64748b;">QR: {}</div></div>',
            obj.thu_tu,
            obj.ten_diem,
            obj.ma_qr,
        )

    @admin.display(description=_("Tuyến / mục tiêu"))
    def route_site_display(self, obj):
        route = obj.loai_tuan_tra
        route_url = _admin_change_url(route)
        target = getattr(route, "muc_tieu", None) if route else None
        target_text = getattr(target, "ten_muc_tieu", "Chưa gắn mục tiêu") if target else "Chưa gắn mục tiêu"
        return format_html(
            '<a href="{}"><b>{}</b></a><div style="font-size:12px;color:#64748b;">{}</div>',
            route_url,
            getattr(route, "ten_loai", "-") or "-",
            target_text,
        )

    @admin.display(description=_("GPS / bán kính"))
    def gps_display(self, obj):
        has_coordinates = obj.vi_do is not None and obj.kinh_do is not None
        if has_coordinates:
            return format_html(
                '<b style="color:#047857;">Có tọa độ</b><div style="font-size:12px;color:#64748b;">{}, {} · {}m</div>',
                obj.vi_do,
                obj.kinh_do,
                obj.ban_kinh_cho_phep,
            )
        return format_html(
            '<b style="color:#b45309;">Thiếu GPS</b><div style="font-size:12px;color:#64748b;">Bán kính {}m</div>',
            obj.ban_kinh_cho_phep,
        )

    @admin.display(description=_("Lượt quét"))
    def scan_usage_display(self, obj):
        return format_html(
            '<div><b>{}</b> lượt</div><div style="font-size:12px;color:#64748b;">Hôm nay: {} · Hợp lệ: {} · Cảnh báo: {}</div>',
            getattr(obj, "scan_count", 0),
            getattr(obj, "today_scan_count", 0),
            getattr(obj, "valid_scan_count", 0),
            getattr(obj, "warning_scan_count", 0),
        )

    @admin.display(description=_("Tình trạng"))
    def config_status_display(self, obj):
        badges = []
        if obj.vi_do is None or obj.kinh_do is None:
            badges.append(("#fef3c7", "#92400e", "Thiếu GPS"))
        if obj.ban_kinh_cho_phep < 30:
            badges.append(("#eff6ff", "#1d4ed8", "Bán kính hẹp"))
        if obj.ban_kinh_cho_phep > 100:
            badges.append(("#fff7ed", "#9a3412", "Bán kính rộng"))
        if getattr(obj, "scan_count", 0) == 0:
            badges.append(("#f8fafc", "#475569", "Chưa quét"))
        if not badges:
            badges.append(("#dcfce7", "#166534", "Sẵn sàng"))
        return format_html_join(
            " ",
            '<span style="display:inline-block;padding:3px 7px;border-radius:999px;background:{};color:{};font-size:11px;font-weight:700;">{}</span>',
            badges,
        )

    @admin.display(description=_("Thao tác"))
    def row_actions(self, obj):
        edit_url = _admin_change_url(obj)
        route_url = _admin_change_url(obj.loai_tuan_tra)
        scans_url = f"{_admin_changelist_url('inspection', 'ghinhantuantra')}?diem_tuan_tra__id__exact={obj.pk}"
        sessions_url = _admin_changelist_url("inspection", "luottuantra")
        return format_html(
            '<div style="display:flex;gap:6px;flex-wrap:wrap;">'
            '<a class="button" href="{}">Sửa</a>'
            '<a class="button" href="{}">Tuyến</a>'
            '<a class="button" href="{}">Lượt quét</a>'
            '<a class="button" href="{}">Lượt tuần tra</a>'
            '</div>',
            edit_url,
            route_url,
            scans_url,
            sessions_url,
        )

    def _snapshot(self, obj):
        return {
            "loai_tuan_tra_id": getattr(obj, "loai_tuan_tra_id", None),
            "ten_diem": obj.ten_diem,
            "ma_qr": obj.ma_qr,
            "thu_tu": obj.thu_tu,
            "vi_do": _audit_json_value(obj.vi_do),
            "kinh_do": _audit_json_value(obj.kinh_do),
            "ban_kinh_cho_phep": obj.ban_kinh_cho_phep,
        }

    def save_model(self, request, obj, form, change):
        before = None
        if change and obj.pk:
            before_obj = self.model.objects.filter(pk=obj.pk).first()
            before = self._snapshot(before_obj) if before_obj else None
        super().save_model(request, obj, form, change)
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
            module="inspection",
            model_name="DiemTuanTra",
            object_id=str(obj.pk),
            changes={"before": before, "after": self._snapshot(obj)},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Cập nhật điểm QR/GPS tuần tra qua Django Admin.",
        )

    def delete_model(self, request, obj):
        snapshot = self._snapshot(obj)
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.DELETE,
            module="inspection",
            model_name="DiemTuanTra",
            object_id=str(obj.pk),
            changes={"deleted": snapshot},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xóa điểm QR/GPS tuần tra qua Django Admin.",
        )
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            for obj in queryset.select_for_update().order_by("pk"):
                self.delete_model(request, obj)


class GhiNhanTuanTraOperationalFilter(admin.SimpleListFilter):
    title = _("Đối soát quét QR")
    parameter_name = "scan_ops"

    def lookups(self, request, model_admin):
        return (
            ("today", _("Quét hôm nay")),
            ("month", _("Trong tháng này")),
            ("valid", _("Hợp lệ")),
            ("warning", _("Cảnh báo GPS")),
            ("lost_gps", _("Mất GPS")),
            ("fraud", _("Nghi gian lận")),
            ("missing_photo", _("Thiếu ảnh xác thực")),
            ("missing_note", _("Thiếu ghi chú")),
            ("missing_actual_gps", _("Thiếu tọa độ thực tế")),
            ("distance_over_100", _("Lệch trên 100m")),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        value = self.value()
        if value == "today":
            return queryset.filter(thoi_gian_quet__date=today)
        if value == "month":
            return queryset.filter(thoi_gian_quet__date__gte=month_start)
        if value == "valid":
            return queryset.filter(ket_qua="HOP_LE")
        if value == "warning":
            return queryset.filter(ket_qua="CANH_BAO_XA")
        if value == "lost_gps":
            return queryset.filter(ket_qua="MAT_GPS")
        if value == "fraud":
            return queryset.filter(ket_qua="GIAN_LAN")
        if value == "missing_photo":
            return queryset.filter(Q(hinh_anh_xac_thuc__isnull=True) | Q(hinh_anh_xac_thuc=""))
        if value == "missing_note":
            return queryset.filter(Q(ghi_chu__isnull=True) | Q(ghi_chu=""))
        if value == "missing_actual_gps":
            return queryset.filter(Q(lat_thuc_te__isnull=True) | Q(lng_thuc_te__isnull=True))
        if value == "distance_over_100":
            return queryset.filter(khoang_cach__gt=100)
        return queryset


@admin.register(GhiNhanTuanTra)
class GhiNhanTuanTraAdmin(admin.ModelAdmin):
    change_list_template = "admin/inspection/ghinhantuantra/change_list.html"
    list_display = ("scan_display", "employee_route_display", "gps_result_display", "evidence_display", "note_display", "row_actions")
    list_select_related = (
        "luot_tuan_tra",
        "luot_tuan_tra__nhan_vien",
        "luot_tuan_tra__loai_tuan_tra",
        "luot_tuan_tra__loai_tuan_tra__muc_tieu",
        "diem_tuan_tra",
        "diem_tuan_tra__loai_tuan_tra",
        "diem_tuan_tra__loai_tuan_tra__muc_tieu",
    )
    list_filter = (GhiNhanTuanTraOperationalFilter, "ket_qua", "thoi_gian_quet", "luot_tuan_tra__loai_tuan_tra")
    search_fields = (
        "luot_tuan_tra__nhan_vien__ho_ten",
        "luot_tuan_tra__nhan_vien__ma_nv",
        "luot_tuan_tra__nhan_vien__ma_nhan_vien",
        "luot_tuan_tra__loai_tuan_tra__ten_loai",
        "luot_tuan_tra__loai_tuan_tra__muc_tieu__ten_muc_tieu",
        "diem_tuan_tra__ten_diem",
        "diem_tuan_tra__ma_qr",
        "toa_do",
        "ghi_chu",
    )
    readonly_fields = ("thoi_gian_quet",)
    date_hierarchy = "thoi_gian_quet"
    list_per_page = 25
    save_on_top = True
    actions = ("mark_valid", "mark_gps_warning", "mark_fraud_suspect")
    fieldsets = (
        (_("Thông tin quét QR"), {"fields": (("luot_tuan_tra", "diem_tuan_tra"), "thoi_gian_quet", "ket_qua")} ),
        (_("Đối soát GPS"), {"fields": (("lat_thuc_te", "lng_thuc_te"), "toa_do", "khoang_cach")} ),
        (_("Bằng chứng hiện trường"), {"fields": ("hinh_anh_xac_thuc", "ghi_chu")} ),
    )



    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inspection_ghinhantuantra_export_csv",
            ),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "luot_tuan_tra",
                "luot_tuan_tra__nhan_vien",
                "luot_tuan_tra__loai_tuan_tra",
                "luot_tuan_tra__loai_tuan_tra__muc_tieu",
                "diem_tuan_tra",
                "diem_tuan_tra__loai_tuan_tra",
                "diem_tuan_tra__loai_tuan_tra__muc_tieu",
            )
        )

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        base_url = _admin_changelist_url("inspection", "ghinhantuantra")
        current_query = request.GET.urlencode()
        export_url = _safe_reverse("admin:inspection_ghinhantuantra_export_csv")
        if current_query:
            export_url = f"{export_url}?{current_query}"
        extra_context = extra_context or {}
        extra_context.update(
            {
                "scmd_patrol_scan_stats": {
                    "total": qs.count(),
                    "today": qs.filter(thoi_gian_quet__date=today).count(),
                    "month": qs.filter(thoi_gian_quet__date__gte=month_start).count(),
                    "valid": qs.filter(ket_qua="HOP_LE").count(),
                    "warning": qs.filter(ket_qua="CANH_BAO_XA").count(),
                    "lost_gps": qs.filter(ket_qua="MAT_GPS").count(),
                    "fraud": qs.filter(ket_qua="GIAN_LAN").count(),
                    "missing_photo": qs.filter(Q(hinh_anh_xac_thuc__isnull=True) | Q(hinh_anh_xac_thuc="")).count(),
                    "missing_actual_gps": qs.filter(Q(lat_thuc_te__isnull=True) | Q(lng_thuc_te__isnull=True)).count(),
                    "distance_over_100": qs.filter(khoang_cach__gt=100).count(),
                },
                "scmd_patrol_scan_links": {
                    "list": base_url,
                    "add": _safe_reverse("admin:inspection_ghinhantuantra_add", fallback=base_url),
                    "export_csv": export_url,
                    "sessions": _admin_changelist_url("inspection", "luottuantra", fallback=base_url),
                    "routes": _admin_changelist_url("inspection", "loaituantra", fallback=base_url),
                    "points": _admin_changelist_url("inspection", "diemtuantra", fallback=base_url),
                    "violations": _admin_changelist_url("inspection", "bienbanvipham", fallback=base_url),
                    "dashboard": _safe_reverse("inspection:dashboard", fallback=base_url),
                    "mobile": _safe_reverse("operations:mobile_tuan_tra_list", fallback=base_url),
                    "today": _append_query(base_url, {"scan_ops": "today"}),
                    "month": _append_query(base_url, {"scan_ops": "month"}),
                    "valid": _append_query(base_url, {"scan_ops": "valid"}),
                    "warning": _append_query(base_url, {"scan_ops": "warning"}),
                    "lost_gps": _append_query(base_url, {"scan_ops": "lost_gps"}),
                    "fraud": _append_query(base_url, {"scan_ops": "fraud"}),
                    "missing_photo": _append_query(base_url, {"scan_ops": "missing_photo"}),
                    "missing_actual_gps": _append_query(base_url, {"scan_ops": "missing_actual_gps"}),
                    "distance_over_100": _append_query(base_url, {"scan_ops": "distance_over_100"}),
                },
            }
        )
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="scmd-pro-ghi-nhan-tuan-tra.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Thời gian quét",
            "Nhân viên",
            "Mã nhân viên",
            "Tuyến tuần tra vận hành",
            "Mục tiêu",
            "Điểm kiểm soát",
            "Mã QR",
            "Kết quả GPS",
            "Khoảng cách lệch (m)",
            "Vĩ độ thực tế",
            "Kinh độ thực tế",
            "Chuỗi tọa độ",
            "Có ảnh xác thực",
            "Ghi chú",
        ])
        for obj in queryset.iterator(chunk_size=200):
            session = obj.luot_tuan_tra
            employee = getattr(session, "nhan_vien", None)
            route = getattr(session, "loai_tuan_tra", None)
            target = getattr(route, "muc_tieu", None) if route else None
            point = obj.diem_tuan_tra
            writer.writerow([
                timezone.localtime(obj.thoi_gian_quet).strftime("%d/%m/%Y %H:%M:%S") if obj.thoi_gian_quet else "",
                getattr(employee, "ho_ten", "") or "",
                getattr(employee, "ma_nv", None) or getattr(employee, "ma_nhan_vien", "") or "",
                getattr(route, "ten_loai", "") or "",
                getattr(target, "ten_muc_tieu", "") or "",
                getattr(point, "ten_diem", "") or "",
                getattr(point, "ma_qr", "") or "",
                obj.get_ket_qua_display(),
                obj.khoang_cach,
                obj.lat_thuc_te or "",
                obj.lng_thuc_te or "",
                obj.toa_do or "",
                "Có" if obj.hinh_anh_xac_thuc else "Không",
                obj.ghi_chu or "",
            ])
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.ACCESS,
            module="inspection",
            model_name="GhiNhanTuanTra",
            object_id="bulk-export",
            changes={"count": queryset.count(), "filters": request.GET.dict()},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xuất CSV nhật ký quét QR tuần tra từ Django Admin.",
        )
        return response

    @admin.display(description=_("Thời điểm / điểm QR"))
    def scan_display(self, obj):
        point_url = _admin_change_url(obj.diem_tuan_tra)
        scan_time = timezone.localtime(obj.thoi_gian_quet).strftime("%d/%m/%Y %H:%M") if obj.thoi_gian_quet else "-"
        qr = getattr(obj.diem_tuan_tra, "ma_qr", "") or "-"
        return format_html(
            '<div><b>{}</b></div><a href="{}" style="font-weight:700;">{}</a><div style="font-size:12px;color:#64748b;">QR: {}</div>',
            scan_time,
            point_url,
            obj.diem_tuan_tra.ten_diem if obj.diem_tuan_tra else "-",
            qr,
        )

    @admin.display(description=_("Nhân viên / tuyến"))
    def employee_route_display(self, obj):
        session = obj.luot_tuan_tra
        employee = getattr(session, "nhan_vien", None)
        route = getattr(session, "loai_tuan_tra", None)
        employee_url = _admin_change_url(employee)
        session_url = _admin_change_url(session)
        route_url = _admin_change_url(route)
        code = getattr(employee, "ma_nv", None) or getattr(employee, "ma_nhan_vien", "") or "-"
        target = getattr(route, "muc_tieu", None) if route else None
        target_text = getattr(target, "ten_muc_tieu", "") or "Chưa gắn mục tiêu"
        return format_html(
            '<a href="{}"><b>{}</b></a><div style="font-size:12px;color:#64748b;">{}</div>'
            '<a href="{}" style="font-size:12px;font-weight:700;">Lượt tuần tra</a> · '
            '<a href="{}" style="font-size:12px;font-weight:700;">{}</a>'
            '<div style="font-size:12px;color:#64748b;">{}</div>',
            employee_url,
            getattr(employee, "ho_ten", "-") or "-",
            code,
            session_url,
            route_url,
            getattr(route, "ten_loai", "-") or "-",
            target_text,
        )

    @admin.display(description=_("Kết quả GPS"))
    def gps_result_display(self, obj):
        palette = {
            "HOP_LE": ("#dcfce7", "#166534"),
            "CANH_BAO_XA": ("#fef3c7", "#92400e"),
            "MAT_GPS": ("#f1f5f9", "#475569"),
            "GIAN_LAN": ("#fee2e2", "#991b1b"),
        }
        bg, color = palette.get(obj.ket_qua, ("#e0f2fe", "#075985"))
        distance_color = "#991b1b" if (obj.khoang_cach or 0) > 100 else "#047857"
        return format_html(
            '<span style="display:inline-block;padding:4px 8px;border-radius:999px;background:{};color:{};font-size:12px;font-weight:800;">{}</span>'
            '<div style="font-size:12px;color:{};font-weight:700;margin-top:4px;">Lệch: {} m</div>',
            bg,
            color,
            obj.get_ket_qua_display(),
            distance_color,
            obj.khoang_cach,
        )

    @admin.display(description=_("Bằng chứng"))
    def evidence_display(self, obj):
        gps_ok = bool(obj.lat_thuc_te and obj.lng_thuc_te)
        photo_ok = bool(obj.hinh_anh_xac_thuc)
        gps_badge = ("#dcfce7", "#166534", "Có GPS") if gps_ok else ("#fee2e2", "#991b1b", "Thiếu GPS")
        photo_badge = ("#dbeafe", "#1d4ed8", "Có ảnh") if photo_ok else ("#f1f5f9", "#475569", "Thiếu ảnh")
        return format_html_join(
            " ",
            '<span style="display:inline-block;padding:3px 7px;border-radius:999px;background:{};color:{};font-size:11px;font-weight:700;">{}</span>',
            [gps_badge, photo_badge],
        )

    @admin.display(description=_("Ghi chú"))
    def note_display(self, obj):
        if obj.ghi_chu:
            note = obj.ghi_chu[:80] + ("…" if len(obj.ghi_chu) > 80 else "")
            return format_html('<span style="color:#334155;">{}</span>', note)
        return format_html('<span style="color:#b45309;font-weight:700;">Thiếu ghi chú</span>')

    @admin.display(description=_("Thao tác"))
    def row_actions(self, obj):
        edit_url = _admin_change_url(obj)
        session_url = _admin_change_url(obj.luot_tuan_tra)
        point_url = _admin_change_url(obj.diem_tuan_tra)
        route = getattr(obj.luot_tuan_tra, "loai_tuan_tra", None)
        route_url = _admin_change_url(route)
        return format_html(
            '<div style="display:flex;gap:6px;flex-wrap:wrap;">'
            '<a class="button" href="{}">Sửa</a>'
            '<a class="button" href="{}">Lượt</a>'
            '<a class="button" href="{}">Điểm QR</a>'
            '<a class="button" href="{}">Tuyến</a>'
            '</div>',
            edit_url,
            session_url,
            point_url,
            route_url,
        )

    def _bulk_update_result(self, request, queryset, *, ket_qua: str, note: str, success_message: str, level=messages.SUCCESS):
        locked_qs = queryset.select_for_update().order_by("pk")
        updated = 0
        with transaction.atomic():
            for obj in locked_qs:
                before = {"ket_qua": obj.ket_qua}
                if obj.ket_qua == ket_qua:
                    continue
                obj.ket_qua = ket_qua
                obj.save(update_fields=["ket_qua"])
                AuditLog.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    action=AuditLog.Action.UPDATE,
                    module="inspection",
                    model_name="GhiNhanTuanTra",
                    object_id=str(obj.pk),
                    changes={"before": before, "after": {"ket_qua": ket_qua}},
                    ip_address=_request_ip(request) or None,
                    user_agent=_request_ua(request),
                    note=note,
                )
                updated += 1
        self.message_user(request, success_message % {"count": updated}, level)

    @admin.action(description=_("Đánh dấu hợp lệ"))
    def mark_valid(self, request, queryset):
        self._bulk_update_result(
            request,
            queryset,
            ket_qua="HOP_LE",
            note="Đánh dấu bản ghi quét QR hợp lệ từ bulk action Django Admin.",
            success_message=_("Đã đánh dấu hợp lệ %(count)s bản ghi quét QR."),
            level=messages.SUCCESS,
        )

    @admin.action(description=_("Đánh dấu cảnh báo GPS"))
    def mark_gps_warning(self, request, queryset):
        self._bulk_update_result(
            request,
            queryset,
            ket_qua="CANH_BAO_XA",
            note="Đánh dấu cảnh báo GPS cho bản ghi quét QR từ bulk action Django Admin.",
            success_message=_("Đã đánh dấu cảnh báo GPS %(count)s bản ghi quét QR."),
            level=messages.WARNING,
        )

    @admin.action(description=_("Đánh dấu nghi vấn gian lận"))
    def mark_fraud_suspect(self, request, queryset):
        self._bulk_update_result(
            request,
            queryset,
            ket_qua="GIAN_LAN",
            note="Đánh dấu nghi vấn gian lận cho bản ghi quét QR từ bulk action Django Admin.",
            success_message=_("Đã đánh dấu nghi vấn gian lận %(count)s bản ghi quét QR."),
            level=messages.ERROR,
        )

    def save_model(self, request, obj, form, change):
        before = {}
        if change and obj.pk:
            old = type(obj).objects.filter(pk=obj.pk).first()
            if old:
                before = {
                    "ket_qua": old.ket_qua,
                    "khoang_cach": old.khoang_cach,
                    "lat_thuc_te": _audit_json_value(old.lat_thuc_te),
                    "lng_thuc_te": _audit_json_value(old.lng_thuc_te),
                    "ghi_chu": old.ghi_chu,
                    "hinh_anh_xac_thuc": bool(old.hinh_anh_xac_thuc),
                }
        super().save_model(request, obj, form, change)
        after = {
            "ket_qua": obj.ket_qua,
            "khoang_cach": obj.khoang_cach,
            "lat_thuc_te": _audit_json_value(obj.lat_thuc_te),
            "lng_thuc_te": _audit_json_value(obj.lng_thuc_te),
            "ghi_chu": obj.ghi_chu,
            "hinh_anh_xac_thuc": bool(obj.hinh_anh_xac_thuc),
        }
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
            module="inspection",
            model_name="GhiNhanTuanTra",
            object_id=str(obj.pk),
            changes={"before": before, "after": after},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Cập nhật bản ghi quét QR tuần tra qua Django Admin." if change else "Tạo bản ghi quét QR tuần tra qua Django Admin.",
        )

    def delete_model(self, request, obj):
        snapshot = {
            "luot_tuan_tra_id": obj.luot_tuan_tra_id,
            "diem_tuan_tra_id": obj.diem_tuan_tra_id,
            "ket_qua": obj.ket_qua,
            "thoi_gian_quet": _audit_json_value(obj.thoi_gian_quet),
        }
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.DELETE,
            module="inspection",
            model_name="GhiNhanTuanTra",
            object_id=str(obj.pk),
            changes={"deleted": snapshot},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xóa bản ghi quét QR tuần tra qua Django Admin.",
        )
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            for obj in queryset.select_for_update().order_by("pk"):
                self.delete_model(request, obj)


class LoaiTuanTraQualityFilter(admin.SimpleListFilter):
    title = _("Chất lượng cấu hình")
    parameter_name = "quality"

    def lookups(self, request, model_admin):
        return (
            ("with_site", _("Đã gắn mục tiêu")),
            ("missing_site", _("Chưa gắn mục tiêu")),
            ("no_points", _("Chưa có điểm QR")),
            ("one_point", _("Chỉ có 1 điểm QR")),
            ("no_sessions", _("Chưa từng phát sinh lượt")),
            ("today", _("Có tuần tra hôm nay")),
            ("abandoned", _("Có lượt bỏ dở")),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        value = self.value()
        if value == "with_site":
            return queryset.filter(muc_tieu__isnull=False)
        if value == "missing_site":
            return queryset.filter(muc_tieu__isnull=True)
        if value == "no_points":
            return queryset.filter(points_count=0)
        if value == "one_point":
            return queryset.filter(points_count=1)
        if value == "no_sessions":
            return queryset.filter(sessions_count=0)
        if value == "today":
            return queryset.filter(luottuantra__thoi_gian_bat_dau__date=today).distinct()
        if value == "abandoned":
            return queryset.filter(abandoned_count__gt=0)
        return queryset


@admin.register(LoaiTuanTra)
class LoaiTuanTraAdmin(admin.ModelAdmin):
    change_list_template = "admin/inspection/loaituantra/change_list.html"
    list_display = ("route_display", "site_display", "gps_policy_display", "points_display", "sessions_display", "config_status_display", "row_actions")
    list_filter = (LoaiTuanTraQualityFilter, "yeu_cau_gps", "muc_tieu")
    list_select_related = ("muc_tieu", "muc_tieu__hop_dong", "muc_tieu__hop_dong__khach_hang_cu")
    autocomplete_fields = ("muc_tieu",)
    list_per_page = 25
    save_on_top = True
    search_fields = (
        "ten_loai",
        "mo_ta",
        "muc_tieu__ten_muc_tieu",
        "muc_tieu__dia_chi",
        "muc_tieu__hop_dong__so_hop_dong",
        "muc_tieu__hop_dong__khach_hang_cu__ten_cong_ty",
        "cac_diem__ten_diem",
        "cac_diem__ma_qr",
    )
    fieldsets = (
        (_("Thông tin tuyến tuần tra"), {"fields": (("ten_loai", "muc_tieu"), "thoi_gian_quy_dinh", "yeu_cau_gps", "mo_ta")} ),
        (_("Điểm QR/GPS"), {"fields": (), "description": _("Thiết lập danh sách điểm QR/GPS bên dưới. Tuyến nên có tối thiểu 2 điểm để đủ giá trị kiểm soát vận hành.")}),
    )
    inlines = [DiemTuanTraInline]

    @admin.display(description=_("GPS bắt buộc"), boolean=True)
    def gps_policy_display(self, obj):
        return bool(obj.yeu_cau_gps)



    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inspection_loaituantra_export_csv",
            ),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        today = timezone.localdate()
        return (
            super()
            .get_queryset(request)
            .select_related("muc_tieu", "muc_tieu__hop_dong", "muc_tieu__hop_dong__khach_hang_cu")
            .annotate(
                points_count=Count("cac_diem", distinct=True),
                sessions_count=Count("luottuantra", distinct=True),
                today_sessions_count=Count("luottuantra", filter=Q(luottuantra__thoi_gian_bat_dau__date=today), distinct=True),
                abandoned_count=Count("luottuantra", filter=Q(luottuantra__trang_thai="BO_DO"), distinct=True),
            )
        )

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        today = timezone.localdate()
        base_url = _admin_changelist_url("inspection", "loaituantra")
        current_query = request.GET.urlencode()
        export_url = _safe_reverse("admin:inspection_loaituantra_export_csv")
        if current_query:
            export_url = f"{export_url}?{current_query}"
        extra_context = extra_context or {}
        extra_context.update(
            {
                "scmd_patrol_route_stats": {
                    "total": qs.count(),
                    "with_site": qs.filter(muc_tieu__isnull=False).count(),
                    "missing_site": qs.filter(muc_tieu__isnull=True).count(),
                    "no_points": qs.filter(points_count=0).count(),
                    "one_point": qs.filter(points_count=1).count(),
                    "points_total": DiemTuanTra.objects.count(),
                    "today": qs.filter(luottuantra__thoi_gian_bat_dau__date=today).distinct().count(),
                    "abandoned": qs.filter(abandoned_count__gt=0).count(),
                },
                "scmd_patrol_route_links": {
                    "list": base_url,
                    "add": _safe_reverse("admin:inspection_loaituantra_add", fallback=base_url),
                    "export_csv": export_url,
                    "points": _admin_changelist_url("inspection", "diemtuantra", fallback=base_url),
                    "sessions": _admin_changelist_url("inspection", "luottuantra", fallback=base_url),
                    "scans": _admin_changelist_url("inspection", "ghinhantuantra", fallback=base_url),
                    "targets": _admin_changelist_url("clients", "muctieu", fallback=base_url),
                    "dashboard": _safe_reverse("inspection:dashboard", fallback=base_url),
                    "mobile": _safe_reverse("operations:mobile_tuan_tra_list", fallback=base_url),
                    "with_site": _append_query(base_url, {"quality": "with_site"}),
                    "missing_site": _append_query(base_url, {"quality": "missing_site"}),
                    "no_points": _append_query(base_url, {"quality": "no_points"}),
                    "one_point": _append_query(base_url, {"quality": "one_point"}),
                    "today": _append_query(base_url, {"quality": "today"}),
                    "abandoned": _append_query(base_url, {"quality": "abandoned"}),
                },
            }
        )
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="scmd-pro-tuyen-tuan-tra.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Tuyến tuần tra vận hành",
            "Mô tả",
            "Thời gian quy định (phút)",
            "Mục tiêu",
            "Địa chỉ mục tiêu",
            "Hợp đồng",
            "Khách hàng",
            "Số điểm QR/GPS",
            "Tổng lượt thực hiện",
            "Lượt hôm nay",
            "Lượt bỏ dở",
            "Tình trạng cấu hình",
        ])
        for obj in queryset.iterator(chunk_size=200):
            target = obj.muc_tieu
            contract = getattr(target, "hop_dong", None) if target else None
            customer = getattr(getattr(contract, "khach_hang_cu", None), "ten_cong_ty", "") if contract else ""
            points_count = getattr(obj, "points_count", 0)
            status_notes = []
            if not target:
                status_notes.append("Thiếu mục tiêu")
            if points_count == 0:
                status_notes.append("Thiếu điểm QR/GPS")
            elif points_count == 1:
                status_notes.append("Chỉ có 1 điểm QR/GPS")
            if not status_notes:
                status_notes.append("Sẵn sàng")
            writer.writerow([
                obj.ten_loai,
                obj.mo_ta or "",
                obj.thoi_gian_quy_dinh,
                getattr(target, "ten_muc_tieu", "") or "",
                getattr(target, "dia_chi", "") or "",
                getattr(contract, "so_hop_dong", "") or "",
                customer,
                points_count,
                getattr(obj, "sessions_count", 0),
                getattr(obj, "today_sessions_count", 0),
                getattr(obj, "abandoned_count", 0),
                "; ".join(status_notes),
            ])
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.ACCESS,
            module="inspection",
            model_name="LoaiTuanTra",
            object_id="bulk-export",
            changes={"count": queryset.count(), "filters": request.GET.dict()},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xuất CSV danh sách tuyến tuần tra từ Django Admin.",
        )
        return response

    @admin.display(description=_("Tuyến tuần tra vận hành"))
    def route_display(self, obj):
        return format_html(
            '<div><b>{}</b><div style="font-size:12px;color:#64748b;">{} phút quy định</div></div>',
            obj.ten_loai,
            obj.thoi_gian_quy_dinh,
        )

    @admin.display(description=_("Mục tiêu / hợp đồng"))
    def site_display(self, obj):
        if not obj.muc_tieu:
            return format_html('<span style="color:#b45309;font-weight:700;">Chưa gắn mục tiêu</span>')
        target_url = _admin_change_url(obj.muc_tieu)
        contract = getattr(obj.muc_tieu, "hop_dong", None)
        contract_text = getattr(contract, "so_hop_dong", "Chưa có HĐ") if contract else "Chưa có HĐ"
        customer = getattr(getattr(contract, "khach_hang_cu", None), "ten_cong_ty", "") if contract else ""
        return format_html(
            '<a href="{}"><b>{}</b></a><div style="font-size:12px;color:#64748b;">{}</div><div style="font-size:12px;color:#64748b;">{}</div>',
            target_url,
            obj.muc_tieu.ten_muc_tieu,
            contract_text,
            customer,
        )

    @admin.display(description=_("Điểm QR"))
    def points_display(self, obj):
        count = getattr(obj, "points_count", 0)
        color = "#047857" if count >= 2 else "#b45309"
        label = "đủ tuyến" if count >= 2 else "cần bổ sung"
        return format_html('<b style="color:{};">{} điểm</b><div style="font-size:12px;color:#64748b;">{}</div>', color, count, label)

    @admin.display(description=_("Lượt thực hiện"))
    def sessions_display(self, obj):
        return format_html(
            '<div><b>{}</b> lượt</div><div style="font-size:12px;color:#64748b;">Hôm nay: {} · Bỏ dở: {}</div>',
            getattr(obj, "sessions_count", 0),
            getattr(obj, "today_sessions_count", 0),
            getattr(obj, "abandoned_count", 0),
        )

    @admin.display(description=_("Tình trạng"))
    def config_status_display(self, obj):
        badges = []
        if not obj.muc_tieu:
            badges.append(("#fef3c7", "#92400e", "Thiếu mục tiêu"))
        if getattr(obj, "points_count", 0) == 0:
            badges.append(("#fee2e2", "#991b1b", "Thiếu QR"))
        if getattr(obj, "points_count", 0) == 1:
            badges.append(("#fff7ed", "#9a3412", "Chỉ 1 điểm"))
        if not badges:
            badges.append(("#dcfce7", "#166534", "Sẵn sàng"))
        return format_html_join(
            " ",
            '<span style="display:inline-block;padding:3px 7px;border-radius:999px;background:{};color:{};font-size:11px;font-weight:700;">{}</span>',
            badges,
        )

    @admin.display(description=_("Thao tác"))
    def row_actions(self, obj):
        edit_url = _admin_change_url(obj)
        qr_url = _safe_reverse("inspection:export_qr_pdf", args=[obj.pk], fallback=edit_url)
        points_url = f"{_admin_changelist_url('inspection', 'diemtuantra')}?loai_tuan_tra__id__exact={obj.pk}"
        sessions_url = f"{_admin_changelist_url('inspection', 'luottuantra')}?loai_tuan_tra__id__exact={obj.pk}"
        target_url = _admin_change_url(obj.muc_tieu) if obj.muc_tieu else _admin_changelist_url("clients", "muctieu")
        return format_html(
            '<div style="display:flex;gap:6px;flex-wrap:wrap;">'
            '<a class="button" href="{}">Sửa</a>'
            '<a class="button" href="{}" target="_blank" rel="noopener">QR PDF</a>'
            '<a class="button" href="{}">Điểm QR</a>'
            '<a class="button" href="{}">Lượt</a>'
            '<a class="button" href="{}">Mục tiêu</a>'
            '</div>',
            edit_url,
            qr_url,
            points_url,
            sessions_url,
            target_url,
        )


class GhiNhanInline(admin.TabularInline):
    model = GhiNhanTuanTra
    extra = 0
    can_delete = False
    readonly_fields = ("diem_tuan_tra", "thoi_gian_quet", "ket_qua", "khoang_cach", "toa_do", "hinh_anh_xac_thuc", "ghi_chu")
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class LuotTuanTraOperationalFilter(admin.SimpleListFilter):
    title = _("Tác nghiệp tuần tra")
    parameter_name = "ops"

    def lookups(self, request, model_admin):
        return (
            ("today", _("Bắt đầu hôm nay")),
            ("active", _("Đang thực hiện")),
            ("completed_today", _("Hoàn thành hôm nay")),
            ("abandoned", _("Bỏ dở / không hoàn thành")),
            ("no_scan", _("Chưa quét điểm nào")),
            ("gps_warning", _("Có cảnh báo GPS")),
            ("missing_end", _("Thiếu thời gian kết thúc")),
            ("month", _("Trong tháng này")),
            ("overtime", _("Vượt thời gian chuẩn")),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        value = self.value()
        if value == "today":
            return queryset.filter(thoi_gian_bat_dau__date=today)
        if value == "active":
            return queryset.filter(trang_thai="DANG_DI")
        if value == "completed_today":
            return queryset.filter(trang_thai="HOAN_THANH", thoi_gian_ket_thuc__date=today)
        if value == "abandoned":
            return queryset.filter(trang_thai="BO_DO")
        if value == "no_scan":
            return queryset.filter(scan_count=0)
        if value == "gps_warning":
            return queryset.filter(gps_warning_count__gt=0)
        if value == "missing_end":
            return queryset.filter(thoi_gian_ket_thuc__isnull=True).exclude(trang_thai="DANG_DI")
        if value == "month":
            return queryset.filter(thoi_gian_bat_dau__date__gte=month_start)
        if value == "overtime":
            ids = []
            for item in queryset.select_related("loai_tuan_tra")[:1000]:
                standard = item.loai_tuan_tra.thoi_gian_quy_dinh if item.loai_tuan_tra else 0
                if item.thoi_gian_thuc_hien and standard and item.thoi_gian_thuc_hien > standard:
                    ids.append(item.pk)
            return queryset.filter(pk__in=ids)
        return queryset


@admin.register(LuotTuanTra)
class LuotTuanTraAdmin(admin.ModelAdmin):
    change_list_template = "admin/inspection/luottuantra/change_list.html"
    list_display = ("employee_display", "route_site_display", "time_display", "progress_display", "evidence_display", "row_actions")
    list_filter = (LuotTuanTraOperationalFilter, "trang_thai", "trang_thai_doi_soat", "thoi_gian_bat_dau", "loai_tuan_tra__muc_tieu")
    list_select_related = ("nhan_vien", "loai_tuan_tra", "loai_tuan_tra__muc_tieu", "phan_cong_ca_truc", "phan_cong_ca_truc__vi_tri_chot", "lich_tuan_tra_van_hanh", "nhiem_vu_tuan_tra_ca")
    autocomplete_fields = ("nhan_vien", "loai_tuan_tra", "phan_cong_ca_truc", "lich_tuan_tra_van_hanh", "nhiem_vu_tuan_tra_ca")
    list_per_page = 25
    save_on_top = True
    search_fields = (
        "nhan_vien__ma_nv",
        "nhan_vien__ho_ten",
        "nhan_vien__sdt",
        "loai_tuan_tra__ten_loai",
        "loai_tuan_tra__muc_tieu__ten_muc_tieu",
        "loai_tuan_tra__muc_tieu__dia_chi",
        "loai_tuan_tra__muc_tieu__hop_dong__so_hop_dong",
        "ghi_nhan__diem_tuan_tra__ten_diem",
        "ghi_nhan__diem_tuan_tra__ma_qr",
    )
    readonly_fields = ("thoi_gian_bat_dau", "thoi_gian_ket_thuc", "tien_do", "thoi_gian_thuc_hien", "so_diem_bat_buoc", "so_diem_da_quet", "so_diem_canh_bao")
    fieldsets = (
        (_("Thông tin lượt tuần tra vận hành"), {"fields": (("nhan_vien", "loai_tuan_tra"), ("phan_cong_ca_truc", "trang_thai"), ("lich_tuan_tra_van_hanh", "nhiem_vu_tuan_tra_ca"), "trang_thai_doi_soat")} ),
        (_("Thời gian và đối soát"), {"fields": (("thoi_gian_bat_dau", "thoi_gian_ket_thuc"), ("tien_do", "thoi_gian_thuc_hien"), ("so_diem_bat_buoc", "so_diem_da_quet", "so_diem_canh_bao"))}),
        (_("Bằng chứng quét QR/GPS"), {"fields": (), "description": _("Chi tiết quét QR/GPS được hiển thị bên dưới dưới dạng chỉ đọc để bảo toàn nhật ký hiện trường.")}),
    )
    inlines = [GhiNhanInline]
    date_hierarchy = "thoi_gian_bat_dau"
    actions = ("mark_completed", "mark_abandoned")



    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inspection_luottuantra_export_csv",
            ),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("nhan_vien", "loai_tuan_tra", "loai_tuan_tra__muc_tieu", "loai_tuan_tra__muc_tieu__hop_dong")
            .annotate(
                scan_count=Count("ghi_nhan", distinct=True),
                gps_warning_count=Count("ghi_nhan", filter=Q(ghi_nhan__ket_qua__in=["CANH_BAO_XA", "MAT_GPS", "GIAN_LAN"]), distinct=True),
                photo_count=Count("ghi_nhan", filter=Q(ghi_nhan__hinh_anh_xac_thuc__isnull=False), distinct=True),
            )
        )

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        base_url = _admin_changelist_url("inspection", "luottuantra")
        current_query = request.GET.urlencode()
        export_url = _safe_reverse("admin:inspection_luottuantra_export_csv")
        if current_query:
            export_url = f"{export_url}?{current_query}"
        extra_context = extra_context or {}
        extra_context.update(
            {
                "scmd_patrol_session_stats": {
                    "total": qs.count(),
                    "today": qs.filter(thoi_gian_bat_dau__date=today).count(),
                    "month": qs.filter(thoi_gian_bat_dau__date__gte=month_start).count(),
                    "active": qs.filter(trang_thai="DANG_DI").count(),
                    "completed_today": qs.filter(trang_thai="HOAN_THANH", thoi_gian_ket_thuc__date=today).count(),
                    "abandoned": qs.filter(trang_thai="BO_DO").count(),
                    "gps_warning": qs.filter(gps_warning_count__gt=0).count(),
                    "no_scan": qs.filter(scan_count=0).count(),
                    "missing_end": qs.filter(thoi_gian_ket_thuc__isnull=True).exclude(trang_thai="DANG_DI").count(),
                },
                "scmd_patrol_session_links": {
                    "list": base_url,
                    "add": _safe_reverse("admin:inspection_luottuantra_add", fallback=base_url),
                    "export_csv": export_url,
                    "routes": _admin_changelist_url("inspection", "loaituantra", fallback=base_url),
                    "points": _admin_changelist_url("inspection", "diemtuantra", fallback=base_url),
                    "scans": _admin_changelist_url("inspection", "ghinhantuantra", fallback=base_url),
                    "violations": _admin_changelist_url("inspection", "bienbanvipham", fallback=base_url),
                    "inspection_runs": _admin_changelist_url("inspection", "dotthanhtra", fallback=base_url),
                    "targets": _admin_changelist_url("clients", "muctieu", fallback=base_url),
                    "dashboard": _safe_reverse("inspection:dashboard", fallback=base_url),
                    "mobile": _safe_reverse("operations:mobile_tuan_tra_list", fallback=base_url),
                    "today": _append_query(base_url, {"ops": "today"}),
                    "month": _append_query(base_url, {"ops": "month"}),
                    "active": _append_query(base_url, {"ops": "active"}),
                    "completed_today": _append_query(base_url, {"ops": "completed_today"}),
                    "abandoned": _append_query(base_url, {"ops": "abandoned"}),
                    "gps_warning": _append_query(base_url, {"ops": "gps_warning"}),
                    "no_scan": _append_query(base_url, {"ops": "no_scan"}),
                    "missing_end": _append_query(base_url, {"ops": "missing_end"}),
                },
            }
        )
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="scmd-pro-luot-tuan-tra.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Thời gian bắt đầu",
            "Thời gian kết thúc",
            "Trạng thái",
            "Nhân viên",
            "Mã nhân viên",
            "Tuyến tuần tra vận hành",
            "Mục tiêu",
            "Hợp đồng",
            "Tiến độ (%)",
            "Số điểm đã quét",
            "Cảnh báo GPS",
            "Số ảnh xác thực",
            "Thời gian thực hiện (phút)",
        ])
        for obj in queryset.iterator(chunk_size=200):
            employee = obj.nhan_vien
            route = obj.loai_tuan_tra
            target = getattr(route, "muc_tieu", None) if route else None
            contract = getattr(target, "hop_dong", None) if target else None
            writer.writerow([
                timezone.localtime(obj.thoi_gian_bat_dau).strftime("%d/%m/%Y %H:%M") if obj.thoi_gian_bat_dau else "",
                timezone.localtime(obj.thoi_gian_ket_thuc).strftime("%d/%m/%Y %H:%M") if obj.thoi_gian_ket_thuc else "",
                obj.get_trang_thai_display(),
                getattr(employee, "ho_ten", "") or "",
                getattr(employee, "ma_nv", None) or getattr(employee, "ma_nhan_vien", "") or "",
                getattr(route, "ten_loai", "") or "",
                getattr(target, "ten_muc_tieu", "") or "",
                getattr(contract, "so_hop_dong", "") or "",
                obj.tien_do,
                getattr(obj, "scan_count", 0),
                getattr(obj, "gps_warning_count", 0),
                getattr(obj, "photo_count", 0),
                obj.thoi_gian_thuc_hien,
            ])
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.ACCESS,
            module="inspection",
            model_name="LuotTuanTra",
            object_id="bulk-export",
            changes={"count": queryset.count(), "filters": request.GET.dict()},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xuất CSV danh sách lượt tuần tra từ Django Admin.",
        )
        return response

    def _audit_admin_change(self, request, obj, before: dict, after: dict, note: str):
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.UPDATE,
            module="inspection",
            model_name="LuotTuanTra",
            object_id=str(obj.pk),
            changes={"before": before, "after": after},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note=note,
        )

    def _bulk_update_records(self, request, queryset, *, updates: dict, note: str, success_message: str, level=messages.SUCCESS):
        updated = 0
        with transaction.atomic():
            for obj in queryset.filter(trang_thai="DANG_DI").select_for_update():
                current_values = {field: getattr(obj, field) for field in updates.keys()}
                if current_values == updates:
                    continue
                for field, value in updates.items():
                    setattr(obj, field, value)
                obj.save(update_fields=[*updates.keys()])
                before = {field: _audit_json_value(value) for field, value in current_values.items()}
                after = {field: _audit_json_value(value) for field, value in updates.items()}
                self._audit_admin_change(request, obj, before, after, note)
                updated += 1
        self.message_user(request, success_message % {"count": updated}, level)

    @admin.display(description=_("Nhân viên"))
    def employee_display(self, obj):
        staff_url = _admin_change_url(obj.nhan_vien)
        code = getattr(obj.nhan_vien, "ma_nv", None) or getattr(obj.nhan_vien, "ma_nhan_vien", "") or "-"
        return format_html(
            '<a href="{}"><b>{}</b></a><div style="font-size:12px;color:#64748b;">{}</div>',
            staff_url,
            obj.nhan_vien.ho_ten if obj.nhan_vien else "-",
            code,
        )

    @admin.display(description=_("Tuyến / mục tiêu"))
    def route_site_display(self, obj):
        route_url = _admin_change_url(obj.loai_tuan_tra)
        site = obj.loai_tuan_tra.muc_tieu if obj.loai_tuan_tra else None
        site_text = site.ten_muc_tieu if site else "Chưa gắn mục tiêu"
        return format_html('<a href="{}"><b>{}</b></a><div style="font-size:12px;color:#64748b;">{}</div>', route_url, obj.loai_tuan_tra.ten_loai if obj.loai_tuan_tra else "-", site_text)

    @admin.display(description=_("Thời gian"))
    def time_display(self, obj):
        start_text = timezone.localtime(obj.thoi_gian_bat_dau).strftime("%d/%m/%Y %H:%M") if obj.thoi_gian_bat_dau else "-"
        end_text = timezone.localtime(obj.thoi_gian_ket_thuc).strftime("%d/%m/%Y %H:%M") if obj.thoi_gian_ket_thuc else "Chưa kết thúc"
        return format_html(
            '<div><b>{}</b></div><div style="font-size:12px;color:#64748b;">Kết thúc: {}</div>',
            start_text,
            end_text,
        )

    @admin.display(description=_("Tiến độ"))
    def progress_display(self, obj):
        progress = obj.tien_do
        status_label = obj.get_trang_thai_doi_soat_display() if getattr(obj, "trang_thai_doi_soat", None) else obj.get_trang_thai_display()
        color = "#047857" if getattr(obj, "trang_thai_doi_soat", "") == "COMPLETED_VALID" else "#b45309" if progress > 0 else "#991b1b"
        scan_count = getattr(obj, "so_diem_da_quet", None)
        if scan_count is None:
            scan_count = getattr(obj, "scan_count", 0)
        return format_html(
            '<div><b style="color:{};">{}%</b> · {}</div><div style="font-size:12px;color:#64748b;">{} điểm quét · {} cảnh báo · {} phút</div>',
            color,
            progress,
            status_label,
            scan_count,
            getattr(obj, "so_diem_canh_bao", 0),
            obj.thoi_gian_thuc_hien,
        )

    @admin.display(description=_("GPS / bằng chứng"))
    def evidence_display(self, obj):
        gps = getattr(obj, "gps_warning_count", 0)
        photo = getattr(obj, "photo_count", 0)
        gps_badge = ("#fee2e2", "#991b1b", f"{gps} cảnh báo") if gps else ("#dcfce7", "#166534", "GPS ổn")
        photo_badge = ("#dbeafe", "#1d4ed8", f"{photo} ảnh") if photo else ("#f1f5f9", "#475569", "Chưa có ảnh")
        return format_html_join(
            " ",
            '<span style="display:inline-block;padding:3px 7px;border-radius:999px;background:{};color:{};font-size:11px;font-weight:700;">{}</span>',
            [gps_badge, photo_badge],
        )

    @admin.display(description=_("Thao tác"))
    def row_actions(self, obj):
        edit_url = _admin_change_url(obj)
        route_url = _admin_change_url(obj.loai_tuan_tra)
        scans_url = f"{_admin_changelist_url('inspection', 'ghinhantuantra')}?luot_tuan_tra__id__exact={obj.pk}"
        mobile_url = _safe_reverse("operations:thuc_hien_tuan_tra", args=[obj.pk], fallback=_safe_reverse("operations:mobile_tuan_tra_list", fallback=_admin_changelist_url("inspection", "luottuantra")))
        return format_html(
            '<div style="display:flex;gap:6px;flex-wrap:wrap;">'
            '<a class="button" href="{}">Sửa</a>'
            '<a class="button" href="{}">Tuyến</a>'
            '<a class="button" href="{}">Quét QR</a>'
            '<a class="button" href="{}">Mobile</a>'
            '</div>',
            edit_url,
            route_url,
            scans_url,
            mobile_url,
        )

    @admin.action(description=_("Đánh dấu hoàn thành hợp lệ các lượt đủ checkpoint"))
    def mark_completed(self, request, queryset):
        updated = 0
        skipped = 0
        now = timezone.now()
        with transaction.atomic():
            for obj in queryset.filter(trang_thai="DANG_DI").select_for_update().prefetch_related("loai_tuan_tra__cac_diem", "ghi_nhan"):
                required_count = obj.loai_tuan_tra.cac_diem.count() if obj.loai_tuan_tra_id else 0
                scanned_count = obj.ghi_nhan.values("diem_tuan_tra_id").distinct().count()
                warning_count = obj.ghi_nhan.exclude(ket_qua="HOP_LE").count()
                if not required_count or scanned_count < required_count:
                    skipped += 1
                    continue
                before = {
                    "trang_thai": obj.trang_thai,
                    "trang_thai_doi_soat": obj.trang_thai_doi_soat,
                    "so_diem_da_quet": obj.so_diem_da_quet,
                }
                obj.trang_thai = "HOAN_THANH"
                obj.thoi_gian_ket_thuc = now
                obj.trang_thai_doi_soat = "COMPLETED_WITH_WARNINGS" if warning_count else "COMPLETED_VALID"
                obj.so_diem_bat_buoc = required_count
                obj.so_diem_da_quet = scanned_count
                obj.so_diem_canh_bao = warning_count
                obj.save(update_fields=[
                    "trang_thai",
                    "thoi_gian_ket_thuc",
                    "trang_thai_doi_soat",
                    "so_diem_bat_buoc",
                    "so_diem_da_quet",
                    "so_diem_canh_bao",
                ])
                after = {
                    "trang_thai": obj.trang_thai,
                    "trang_thai_doi_soat": obj.trang_thai_doi_soat,
                    "so_diem_da_quet": obj.so_diem_da_quet,
                }
                self._audit_admin_change(
                    request,
                    obj,
                    before,
                    after,
                    "Đánh dấu hoàn thành hợp lệ lượt tuần tra từ bulk action Django Admin sau khi đủ checkpoint.",
                )
                updated += 1
        self.message_user(
            request,
            _("Đã hoàn thành hợp lệ %(count)s lượt; bỏ qua %(skipped)s lượt chưa đủ checkpoint.") % {"count": updated, "skipped": skipped},
            messages.SUCCESS if updated else messages.WARNING,
        )

    @admin.action(description=_("Đánh dấu bỏ dở các lượt đang thực hiện"))
    def mark_abandoned(self, request, queryset):
        self._bulk_update_records(
            request,
            queryset,
            updates={"trang_thai": "BO_DO", "trang_thai_doi_soat": "MISSED", "thoi_gian_ket_thuc": timezone.now()},
            note="Đánh dấu bỏ dở lượt tuần tra từ bulk action Django Admin.",
            success_message=_("Đã đánh dấu bỏ dở %(count)s lượt đang thực hiện."),
            level=messages.WARNING,
        )


class DotThanhTraOperationalFilter(admin.SimpleListFilter):
    title = _("Tác nghiệp thanh tra")
    parameter_name = "inspection_ops"

    def lookups(self, request, model_admin):
        return (
            ("today", _("Thanh tra hôm nay")),
            ("failed", _("Không đạt")),
            ("passed", _("Đạt yêu cầu")),
            ("short_staff", _("Thiếu quân số")),
            ("checklist_fail", _("Fail checklist")),
            ("missing_image", _("Thiếu ảnh hiện trường")),
            ("missing_note", _("Thiếu nhận xét/kiến nghị")),
            ("month", _("Trong tháng này")),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        value = self.value()
        if value == "today":
            return queryset.filter(thoi_gian_den__date=today)
        if value == "failed":
            return queryset.filter(ket_qua="KHONG_DAT")
        if value == "passed":
            return queryset.filter(ket_qua="DAT")
        if value == "short_staff":
            return queryset.filter(quan_so_thuc_te__lt=F("quan_so_bao_cao"))
        if value == "checklist_fail":
            return queryset.filter(Q(kiem_tra_so_sach=False) | Q(kiem_tra_dong_phuc=False) | Q(kiem_tra_cong_cu=False))
        if value == "missing_image":
            return queryset.filter(Q(hinh_anh_tong_quan__isnull=True) | Q(hinh_anh_tong_quan=""))
        if value == "missing_note":
            return queryset.filter(Q(danh_gia_chung__isnull=True) | Q(danh_gia_chung=""))
        if value in {"month", "this_month"}:
            return queryset.filter(thoi_gian_den__date__gte=month_start)
        return queryset


@admin.register(DotThanhTra)
class DotThanhTraAdmin(admin.ModelAdmin):
    change_list_template = "admin/inspection/dotthanhtra/change_list.html"
    list_display = ("inspection_display", "site_display", "staffing_display", "checklist_display", "result_display", "evidence_display", "row_actions")
    list_filter = (DotThanhTraOperationalFilter, "ket_qua", "thoi_gian_den", "muc_tieu")
    list_select_related = ("can_bo", "muc_tieu", "muc_tieu__hop_dong", "muc_tieu__hop_dong__khach_hang_cu")
    autocomplete_fields = ("can_bo", "muc_tieu")
    list_per_page = 25
    save_on_top = True
    search_fields = (
        "can_bo__ma_nhan_vien",
        "can_bo__ho_ten",
        "can_bo__sdt_chinh",
        "muc_tieu__ten_muc_tieu",
        "muc_tieu__dia_chi",
        "muc_tieu__hop_dong__so_hop_dong",
        "muc_tieu__hop_dong__khach_hang_cu__ten_cong_ty",
        "danh_gia_chung",
    )
    date_hierarchy = "thoi_gian_den"
    actions = ("mark_passed", "mark_failed")
    fieldsets = (
        (_("Thông tin thanh tra"), {"fields": (("can_bo", "muc_tieu"), "thoi_gian_den", "ket_qua")} ),
        (_("Đối soát quân số"), {"fields": (("quan_so_bao_cao", "quan_so_thuc_te"),)}),
        (_("Checklist hiện trường"), {"fields": (("kiem_tra_so_sach", "kiem_tra_dong_phuc", "kiem_tra_cong_cu"),)}),
        (_("Bằng chứng và kiến nghị"), {"fields": ("hinh_anh_tong_quan", "danh_gia_chung")} ),
    )



    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inspection_dotthanhtra_export_csv",
            ),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("can_bo", "muc_tieu", "muc_tieu__hop_dong", "muc_tieu__hop_dong__khach_hang_cu")
        )

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        failed_q = qs.filter(ket_qua="KHONG_DAT")
        checklist_fail_q = qs.filter(Q(kiem_tra_so_sach=False) | Q(kiem_tra_dong_phuc=False) | Q(kiem_tra_cong_cu=False))
        base_url = _admin_changelist_url("inspection", "dotthanhtra")
        export_url = _safe_reverse("admin:inspection_dotthanhtra_export_csv")
        current_query = request.GET.urlencode()
        if current_query:
            export_url = f"{export_url}?{current_query}"
        extra_context = extra_context or {}
        extra_context.update(
            {
                "scmd_inspection_run_stats": {
                    "total": qs.count(),
                    "today": qs.filter(thoi_gian_den__date=today).count(),
                    "month": qs.filter(thoi_gian_den__date__gte=month_start).count(),
                    "passed": qs.filter(ket_qua="DAT").count(),
                    "failed": failed_q.count(),
                    "short_staff": qs.filter(quan_so_thuc_te__lt=F("quan_so_bao_cao")).count(),
                    "checklist_fail": checklist_fail_q.count(),
                    "missing_image": qs.filter(Q(hinh_anh_tong_quan__isnull=True) | Q(hinh_anh_tong_quan="")).count(),
                    "missing_note": qs.filter(Q(danh_gia_chung__isnull=True) | Q(danh_gia_chung="")).count(),
                },
                "scmd_inspection_run_links": {
                    "list": base_url,
                    "add": _safe_reverse("admin:inspection_dotthanhtra_add"),
                    "export_csv": export_url,
                    "violations": _admin_changelist_url("inspection", "bienbanvipham"),
                    "patrol_sessions": _admin_changelist_url("inspection", "luottuantra"),
                    "targets": _admin_changelist_url("clients", "muctieu"),
                    "dashboard": _safe_reverse("inspection:dashboard", fallback=base_url),
                    "mobile": _safe_reverse("inspection:mobile_dot_thanh_tra", fallback=base_url),
                    "today": _append_query(base_url, {"inspection_ops": "today"}),
                    "month": _append_query(base_url, {"inspection_ops": "month"}),
                    "passed": _append_query(base_url, {"inspection_ops": "passed"}),
                    "failed": _append_query(base_url, {"inspection_ops": "failed"}),
                    "short_staff": _append_query(base_url, {"inspection_ops": "short_staff"}),
                    "checklist_fail": _append_query(base_url, {"inspection_ops": "checklist_fail"}),
                    "missing_image": _append_query(base_url, {"inspection_ops": "missing_image"}),
                    "missing_note": _append_query(base_url, {"inspection_ops": "missing_note"}),
                },
            }
        )
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="scmd-pro-dot-thanh-tra.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Thời gian kiểm tra",
            "Cán bộ kiểm tra",
            "Mã nhân viên",
            "Mục tiêu",
            "Hợp đồng",
            "Quân số theo lịch",
            "Quân số thực tế",
            "Chênh lệch quân số",
            "Sổ sách",
            "Đồng phục/tác phong",
            "Công cụ hỗ trợ",
            "Kết luận",
            "Có ảnh hiện trường",
            "Nhận xét/Kiến nghị",
        ])
        for obj in queryset.iterator(chunk_size=200):
            officer = obj.can_bo
            target = obj.muc_tieu
            contract = getattr(target, "hop_dong", None) if target else None
            diff = (obj.quan_so_thuc_te or 0) - (obj.quan_so_bao_cao or 0)
            writer.writerow([
                timezone.localtime(obj.thoi_gian_den).strftime("%d/%m/%Y %H:%M") if obj.thoi_gian_den else "",
                getattr(officer, "ho_ten", "") or "",
                getattr(officer, "ma_nv", None) or getattr(officer, "ma_nhan_vien", "") or "",
                getattr(target, "ten_muc_tieu", "") or "",
                getattr(contract, "so_hop_dong", "") or "",
                obj.quan_so_bao_cao,
                obj.quan_so_thuc_te,
                diff,
                "Đạt" if obj.kiem_tra_so_sach else "Không đạt",
                "Đạt" if obj.kiem_tra_dong_phuc else "Không đạt",
                "Đạt" if obj.kiem_tra_cong_cu else "Không đạt",
                obj.get_ket_qua_display(),
                "Có" if obj.hinh_anh_tong_quan else "Không",
                obj.danh_gia_chung or "",
            ])
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.ACCESS,
            module="inspection",
            model_name="DotThanhTra",
            object_id="bulk-export",
            changes={"count": queryset.count(), "filters": request.GET.dict()},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xuất CSV danh sách đợt thanh tra từ Django Admin.",
        )
        return response

    def _audit_admin_change(self, request, obj, before: dict, after: dict, note: str):
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.UPDATE,
            module="inspection",
            model_name="DotThanhTra",
            object_id=str(obj.pk),
            changes={"before": before, "after": after},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note=note,
        )

    def _bulk_update_records(self, request, queryset, *, updates: dict, note: str, success_message: str, level=messages.SUCCESS):
        updated = 0
        with transaction.atomic():
            for obj in queryset.select_for_update():
                current_values = {field: getattr(obj, field) for field in updates.keys()}
                if current_values == updates:
                    continue
                for field, value in updates.items():
                    setattr(obj, field, value)
                obj.save(update_fields=[*updates.keys()])
                before = {field: _audit_json_value(value) for field, value in current_values.items()}
                after = {field: _audit_json_value(value) for field, value in updates.items()}
                self._audit_admin_change(request, obj, before, after, note)
                updated += 1
        self.message_user(request, success_message % {"count": updated}, level)

    @admin.display(description=_("Đợt thanh tra"))
    def inspection_display(self, obj):
        officer_url = _admin_change_url(obj.can_bo)
        time_text = timezone.localtime(obj.thoi_gian_den).strftime("%d/%m/%Y %H:%M") if obj.thoi_gian_den else "-"
        officer_name = obj.can_bo.ho_ten if obj.can_bo else "Chưa rõ cán bộ"
        officer_code = (getattr(obj.can_bo, "ma_nv", None) or getattr(obj.can_bo, "ma_nhan_vien", "")) if obj.can_bo else ""
        return format_html(
            '<div><a href="{}"><b>{}</b></a></div><div style="font-size:12px;color:#64748b;">{}</div><div style="font-size:12px;color:#64748b;">{}</div>',
            officer_url,
            officer_name,
            officer_code,
            time_text,
        )

    @admin.display(description=_("Mục tiêu / hợp đồng"))
    def site_display(self, obj):
        target = obj.muc_tieu
        if not target:
            return format_html('<span style="color:#b45309;font-weight:700;">Chưa gắn mục tiêu</span>')
        target_url = _admin_change_url(target)
        contract = getattr(target, "hop_dong", None)
        contract_text = getattr(contract, "so_hop_dong", "Chưa có HĐ") if contract else "Chưa có HĐ"
        customer = getattr(getattr(contract, "khach_hang_cu", None), "ten_cong_ty", "") if contract else ""
        return format_html(
            '<a href="{}"><b>{}</b></a><div style="font-size:12px;color:#64748b;">{}</div><div style="font-size:12px;color:#64748b;">{}</div>',
            target_url,
            target.ten_muc_tieu,
            contract_text,
            customer,
        )

    @admin.display(description=_("Quân số"))
    def staffing_display(self, obj):
        diff = (obj.quan_so_thuc_te or 0) - (obj.quan_so_bao_cao or 0)
        color = "#047857" if diff >= 0 else "#b91c1c"
        note = "Đủ quân" if diff >= 0 else f"Thiếu {abs(diff)}"
        return format_html(
            '<b style="color:{};">{}/{}</b><div style="font-size:12px;color:#64748b;">{}</div>',
            color,
            obj.quan_so_thuc_te,
            obj.quan_so_bao_cao,
            note,
        )

    @admin.display(description=_("Checklist"))
    def checklist_display(self, obj):
        items = [
            ("Sổ sách", obj.kiem_tra_so_sach),
            ("Đồng phục", obj.kiem_tra_dong_phuc),
            ("Công cụ", obj.kiem_tra_cong_cu),
        ]
        badges = [
            ("#dcfce7", "#166534", f"{label}: Đạt") if ok else ("#fee2e2", "#991b1b", f"{label}: Lỗi")
            for label, ok in items
        ]
        return format_html_join(
            " ",
            '<span style="display:inline-block;padding:3px 7px;border-radius:999px;background:{};color:{};font-size:11px;font-weight:700;margin-bottom:3px;">{}</span>',
            badges,
        )

    @admin.display(description=_("Kết luận"))
    def result_display(self, obj):
        if obj.ket_qua == "DAT":
            return format_html('<span style="display:inline-block;padding:4px 8px;border-radius:999px;background:#dcfce7;color:#166534;font-weight:800;">Đạt</span>')
        return format_html('<span style="display:inline-block;padding:4px 8px;border-radius:999px;background:#fee2e2;color:#991b1b;font-weight:800;">Không đạt</span>')

    @admin.display(description=_("Bằng chứng / ghi chú"))
    def evidence_display(self, obj):
        image = bool(obj.hinh_anh_tong_quan)
        note = bool((obj.danh_gia_chung or "").strip())
        badges = [
            ("#dbeafe", "#1d4ed8", "Có ảnh") if image else ("#fef3c7", "#92400e", "Thiếu ảnh"),
            ("#dcfce7", "#166534", "Có nhận xét") if note else ("#fef3c7", "#92400e", "Thiếu nhận xét"),
        ]
        return format_html_join(
            " ",
            '<span style="display:inline-block;padding:3px 7px;border-radius:999px;background:{};color:{};font-size:11px;font-weight:700;">{}</span>',
            badges,
        )

    @admin.display(description=_("Thao tác"))
    def row_actions(self, obj):
        edit_url = _admin_change_url(obj)
        target_url = _admin_change_url(obj.muc_tieu) if obj.muc_tieu else _admin_changelist_url("clients", "muctieu")
        violation_url = _admin_changelist_url("inspection", "bienbanvipham")
        if obj.muc_tieu_id:
            violation_url = f"{violation_url}?muc_tieu__id__exact={obj.muc_tieu_id}"
        image_action = (
            format_html('<a class="button" href="{}" target="_blank" rel="noopener">Ảnh</a>', obj.hinh_anh_tong_quan.url)
            if obj.hinh_anh_tong_quan
            else format_html('<span style="display:inline-block;padding:5px 8px;color:#92400e;font-size:12px;font-weight:800;">Thiếu ảnh</span>')
        )
        return format_html(
            '<div style="display:flex;gap:6px;flex-wrap:wrap;">'
            '<a class="button" href="{}">Sửa</a>'
            '<a class="button" href="{}">Mục tiêu</a>'
            '<a class="button" href="{}">Vi phạm</a>'
            '{}'
            '</div>',
            edit_url,
            target_url,
            violation_url,
            image_action,
        )

    @admin.action(description=_("Đánh dấu Đạt yêu cầu"))
    def mark_passed(self, request, queryset):
        self._bulk_update_records(
            request,
            queryset.exclude(ket_qua="DAT"),
            updates={"ket_qua": "DAT"},
            note="Admin bulk action: đánh dấu đợt thanh tra đạt yêu cầu.",
            success_message=_("Đã đánh dấu Đạt yêu cầu cho %(count)s đợt thanh tra."),
            level=messages.SUCCESS,
        )

    @admin.action(description=_("Đánh dấu Không đạt yêu cầu"))
    def mark_failed(self, request, queryset):
        self._bulk_update_records(
            request,
            queryset.exclude(ket_qua="KHONG_DAT"),
            updates={"ket_qua": "KHONG_DAT"},
            note="Admin bulk action: đánh dấu đợt thanh tra không đạt yêu cầu.",
            success_message=_("Đã đánh dấu Không đạt yêu cầu cho %(count)s đợt thanh tra."),
            level=messages.WARNING,
        )


class BienBanViPhamOperationalFilter(admin.SimpleListFilter):
    title = _("Tình trạng xử lý")
    parameter_name = "operational_status"

    def lookups(self, request, model_admin):
        return (
            ("today", _("Lập hôm nay")),
            ("month", _("Lập trong tháng")),
            ("pending", _("Chờ duyệt")),
            ("approved", _("Đã duyệt")),
            ("rejected", _("Từ chối / hủy")),
            ("money_penalty", _("Có phạt tiền")),
            ("missing_evidence", _("Thiếu ảnh bằng chứng")),
            ("missing_target", _("Chưa gắn mục tiêu")),
            ("missing_offender", _("Chưa gắn nhân viên vi phạm")),
            ("missing_reporter", _("Chưa gắn người lập")),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        value = self.value()
        if value == "today":
            return queryset.filter(ngay_vi_pham__date=today)
        if value == "month":
            return queryset.filter(ngay_vi_pham__date__gte=today.replace(day=1))
        if value == "pending":
            return queryset.filter(trang_thai="CHO_DUYET")
        if value == "approved":
            return queryset.filter(trang_thai="DA_DUYET")
        if value == "rejected":
            return queryset.filter(trang_thai="TU_CHOI")
        if value == "money_penalty":
            return queryset.filter(hinh_thuc_xu_ly="PHAT_TIEN", so_tien_phat__gt=0)
        if value == "missing_evidence":
            return queryset.filter(Q(bang_chung_anh="") | Q(bang_chung_anh__isnull=True))
        if value == "missing_target":
            return queryset.filter(muc_tieu__isnull=True)
        if value == "missing_offender":
            return queryset.filter(doi_tuong_vi_pham__isnull=True)
        if value == "missing_reporter":
            return queryset.filter(nguoi_lap__isnull=True)
        return queryset


@admin.register(BienBanViPham)
class BienBanViPhamAdmin(admin.ModelAdmin):
    change_list_template = "admin/inspection/bienbanvipham/change_list.html"
    list_display = ("record_display", "people_display", "target_display", "violation_display", "decision_display", "evidence_display", "row_actions")
    list_filter = (BienBanViPhamOperationalFilter, "trang_thai", "hinh_thuc_xu_ly", "loai_loi", "ngay_vi_pham", "created_at")
    list_select_related = (
        "doi_tuong_vi_pham",
        "doi_tuong_vi_pham__phong_ban",
        "doi_tuong_vi_pham__chuc_danh",
        "muc_tieu",
        "muc_tieu__hop_dong",
        "muc_tieu__hop_dong__khach_hang_cu",
        "nguoi_lap",
    )
    autocomplete_fields = ("doi_tuong_vi_pham", "nguoi_lap", "muc_tieu")
    readonly_fields = ("ma_bien_ban", "created_at")
    list_per_page = 25
    save_on_top = True
    search_fields = (
        "ma_bien_ban",
        "doi_tuong_vi_pham__ho_ten",
        "doi_tuong_vi_pham__ma_nv",
        "doi_tuong_vi_pham__so_dien_thoai",
        "nguoi_lap__ho_ten",
        "nguoi_lap__ma_nv",
        "muc_tieu__ten_muc_tieu",
        "muc_tieu__dia_chi",
        "muc_tieu__hop_dong__so_hop_dong",
        "muc_tieu__hop_dong__khach_hang_cu__ten_cong_ty",
        "mo_ta",
    )
    date_hierarchy = "ngay_vi_pham"
    actions = ("approve_records", "reject_records", "mark_warning", "mark_money_penalty")
    fieldsets = (
        (_("Thông tin biên bản"), {"fields": (("ma_bien_ban", "trang_thai"), ("ngay_vi_pham", "created_at"))}),
        (_("Nhân sự và địa điểm"), {"fields": (("doi_tuong_vi_pham", "nguoi_lap"), "muc_tieu")}),
        (_("Nội dung vi phạm"), {"fields": ("loai_loi", "mo_ta", "bang_chung_anh")}),
        (_("Hình thức xử lý"), {"fields": (("hinh_thuc_xu_ly", "so_tien_phat"),)}),
    )



    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inspection_bienbanvipham_export_csv",
            ),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "doi_tuong_vi_pham",
                "doi_tuong_vi_pham__phong_ban",
                "doi_tuong_vi_pham__chuc_danh",
                "muc_tieu",
                "muc_tieu__hop_dong",
                "muc_tieu__hop_dong__khach_hang_cu",
                "nguoi_lap",
            )
        )

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        total_penalty = qs.filter(hinh_thuc_xu_ly="PHAT_TIEN").aggregate(total=Sum("so_tien_phat"))["total"] or 0
        base_url = _admin_changelist_url("inspection", "bienbanvipham")
        current_query = request.GET.urlencode()
        export_url = _safe_reverse("admin:inspection_bienbanvipham_export_csv")
        if current_query:
            export_url = f"{export_url}?{current_query}"
        extra_context = extra_context or {}
        extra_context.update(
            {
                "scmd_violation_stats": {
                    "total": qs.count(),
                    "today": qs.filter(ngay_vi_pham__date=today).count(),
                    "month": qs.filter(ngay_vi_pham__date__gte=month_start).count(),
                    "pending": qs.filter(trang_thai="CHO_DUYET").count(),
                    "approved": qs.filter(trang_thai="DA_DUYET").count(),
                    "rejected": qs.filter(trang_thai="TU_CHOI").count(),
                    "money_penalty": qs.filter(hinh_thuc_xu_ly="PHAT_TIEN", so_tien_phat__gt=0).count(),
                    "missing_evidence": qs.filter(Q(bang_chung_anh="") | Q(bang_chung_anh__isnull=True)).count(),
                    "missing_target": qs.filter(muc_tieu__isnull=True).count(),
                    "missing_offender": qs.filter(doi_tuong_vi_pham__isnull=True).count(),
                    "total_penalty": f"{total_penalty:,.0f} VNĐ",
                },
                "scmd_violation_links": {
                    "add": _safe_reverse("admin:inspection_bienbanvipham_add"),
                    "export_csv": export_url,
                    "inspection_runs": _admin_changelist_url("inspection", "dotthanhtra"),
                    "incidents": _admin_changelist_url("operations", "baocaosuco"),
                    "attendance": _admin_changelist_url("operations", "chamcong"),
                    "employees": _admin_changelist_url("users", "nhanvien"),
                    "workflow": _safe_reverse("workflow:proposal_create", fallback=_admin_changelist_url("workflow", "proposal")),
                    "dashboard": _safe_reverse("inspection:dashboard", fallback=base_url),
                    "training": _admin_changelist_url("inspection", "buoihuanluyen"),
                    "payroll": _admin_changelist_url("accounting", "chitietluong"),
                    "pending": _append_query(base_url, {"operational_status": "pending"}),
                    "approved": _append_query(base_url, {"operational_status": "approved"}),
                    "rejected": _append_query(base_url, {"operational_status": "rejected"}),
                    "today": _append_query(base_url, {"operational_status": "today"}),
                    "month": _append_query(base_url, {"operational_status": "month"}),
                    "money_penalty": _append_query(base_url, {"operational_status": "money_penalty"}),
                    "missing_evidence": _append_query(base_url, {"operational_status": "missing_evidence"}),
                    "missing_target": _append_query(base_url, {"operational_status": "missing_target"}),
                    "missing_offender": _append_query(base_url, {"operational_status": "missing_offender"}),
                },
            }
        )
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="scmd-pro-bien-ban-vi-pham.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Mã biên bản",
            "Thời điểm vi phạm",
            "Nhân viên vi phạm",
            "Mã NV",
            "Người lập",
            "Mục tiêu",
            "Hợp đồng",
            "Hành vi",
            "Mô tả",
            "Hình thức xử lý",
            "Số tiền phạt",
            "Trạng thái",
            "Có ảnh bằng chứng",
            "Ngày tạo",
        ])
        for obj in queryset.iterator(chunk_size=200):
            offender = obj.doi_tuong_vi_pham
            reporter = obj.nguoi_lap
            target = obj.muc_tieu
            contract = getattr(target, "hop_dong", None) if target else None
            writer.writerow([
                obj.ma_bien_ban,
                timezone.localtime(obj.ngay_vi_pham).strftime("%d/%m/%Y %H:%M") if obj.ngay_vi_pham else "",
                getattr(offender, "ho_ten", "") or "",
                getattr(offender, "ma_nv", None) or getattr(offender, "ma_nhan_vien", "") or "",
                getattr(reporter, "ho_ten", "") or "",
                getattr(target, "ten_muc_tieu", "") or "",
                getattr(contract, "so_hop_dong", "") or "",
                obj.get_loai_loi_display(),
                obj.mo_ta or "",
                obj.get_hinh_thuc_xu_ly_display(),
                obj.so_tien_phat or 0,
                obj.get_trang_thai_display(),
                "Có" if obj.bang_chung_anh else "Không",
                timezone.localtime(obj.created_at).strftime("%d/%m/%Y %H:%M") if obj.created_at else "",
            ])
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.ACCESS,
            module="inspection",
            model_name="BienBanViPham",
            object_id="bulk-export",
            changes={"count": queryset.count(), "filters": request.GET.dict()},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xuất CSV danh sách biên bản vi phạm từ Django Admin.",
        )
        return response

    def _audit_admin_change(self, request, obj, before: dict, after: dict, note: str):
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.UPDATE,
            module="inspection",
            model_name="BienBanViPham",
            object_id=str(obj.pk),
            changes={"before": before, "after": after},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note=note,
        )

    def _bulk_update_records(self, request, queryset, *, updates: dict, note: str, success_message: str, level=messages.SUCCESS):
        updated = 0
        with transaction.atomic():
            for obj in queryset.select_for_update():
                current_values = {field: getattr(obj, field) for field in updates.keys()}
                if current_values == updates:
                    continue
                for field, value in updates.items():
                    setattr(obj, field, value)
                obj.save(update_fields=[*updates.keys()])
                before = {field: _audit_json_value(value) for field, value in current_values.items()}
                after = {field: _audit_json_value(value) for field, value in updates.items()}
                self._audit_admin_change(request, obj, before, after, note)
                updated += 1
        self.message_user(request, success_message % {"count": updated}, level)

    @admin.display(description=_("Biên bản"))
    def record_display(self, obj):
        created = timezone.localtime(obj.created_at).strftime("%d/%m/%Y %H:%M") if obj.created_at else "-"
        violation_time = timezone.localtime(obj.ngay_vi_pham).strftime("%d/%m/%Y %H:%M") if obj.ngay_vi_pham else "-"
        return format_html(
            '<div><b>{}</b><div style="font-size:12px;color:#64748b;">Vi phạm: {}</div><div style="font-size:12px;color:#64748b;">Lập: {}</div></div>',
            obj.ma_bien_ban,
            violation_time,
            created,
        )

    @admin.display(description=_("Nhân sự / người lập"))
    def people_display(self, obj):
        offender = obj.doi_tuong_vi_pham
        reporter = obj.nguoi_lap
        offender_text = offender.ho_ten if offender else "Chưa gắn nhân viên"
        offender_code = (getattr(offender, "ma_nv", None) or getattr(offender, "ma_nhan_vien", "")) if offender else ""
        reporter_text = reporter.ho_ten if reporter else "Chưa có người lập"
        return format_html(
            '<div><b>{}</b><div style="font-size:12px;color:#64748b;">{}</div><div style="font-size:12px;color:#475569;">Người lập: {}</div></div>',
            offender_text,
            offender_code,
            reporter_text,
        )

    @admin.display(description=_("Mục tiêu / hợp đồng"))
    def target_display(self, obj):
        if not obj.muc_tieu:
            return format_html('<span style="color:#b45309;font-weight:800;">Chưa gắn mục tiêu</span>')
        target_url = _admin_change_url(obj.muc_tieu)
        contract = getattr(obj.muc_tieu, "hop_dong", None)
        contract_text = getattr(contract, "so_hop_dong", "Chưa có HĐ") if contract else "Chưa có HĐ"
        return format_html(
            '<a href="{}"><b>{}</b></a><div style="font-size:12px;color:#64748b;">{}</div>',
            target_url,
            obj.muc_tieu.ten_muc_tieu,
            contract_text,
        )

    @admin.display(description=_("Hành vi"))
    def violation_display(self, obj):
        desc = (obj.mo_ta or "").strip()
        short_desc = desc[:90] + "..." if len(desc) > 90 else desc
        return format_html(
            '<div><b>{}</b><div style="font-size:12px;color:#64748b;">{}</div></div>',
            obj.get_loai_loi_display(),
            short_desc or "Chưa có mô tả chi tiết",
        )

    @admin.display(description=_("Xử lý"))
    def decision_display(self, obj):
        status_map = {
            "CHO_DUYET": ("#fef3c7", "#92400e"),
            "DA_DUYET": ("#dcfce7", "#166534"),
            "TU_CHOI": ("#fee2e2", "#991b1b"),
        }
        bg, fg = status_map.get(obj.trang_thai, ("#f1f5f9", "#334155"))
        amount = f"{obj.so_tien_phat or 0:,.0f} VNĐ"
        amount_line = f"Phạt: {amount}" if obj.hinh_thuc_xu_ly == "PHAT_TIEN" else "Không phạt tiền"
        return format_html(
            '<div><span style="display:inline-block;padding:4px 8px;border-radius:999px;background:{};color:{};font-size:11px;font-weight:800;">{}</span>'
            '<div style="font-size:12px;color:#0f172a;margin-top:4px;font-weight:700;">{}</div>'
            '<div style="font-size:12px;color:#64748b;">{}</div></div>',
            bg,
            fg,
            obj.get_trang_thai_display(),
            obj.get_hinh_thuc_xu_ly_display(),
            amount_line,
        )

    @admin.display(description=_("Bằng chứng"))
    def evidence_display(self, obj):
        if obj.bang_chung_anh:
            return format_html('<a class="button" href="{}" target="_blank" rel="noopener">Xem ảnh</a>', obj.bang_chung_anh.url)
        return format_html('<span style="color:#b45309;font-weight:800;">Thiếu ảnh</span>')

    @admin.display(description=_("Thao tác"))
    def row_actions(self, obj):
        edit_url = _admin_change_url(obj)
        offender_url = _admin_change_url(obj.doi_tuong_vi_pham) if obj.doi_tuong_vi_pham else _admin_changelist_url("users", "nhanvien")
        target_url = _admin_change_url(obj.muc_tieu) if obj.muc_tieu else _admin_changelist_url("clients", "muctieu")
        workflow_url = _safe_reverse("workflow:proposal_create", fallback=_admin_changelist_url("workflow", "proposal"))
        payroll_url = _admin_changelist_url("accounting", "chitietluong")
        links = [
            (edit_url, "Sửa"),
            (offender_url, "Nhân sự"),
            (target_url, "Mục tiêu"),
            (workflow_url, "Tờ trình"),
            (payroll_url, "Lương"),
        ]
        return format_html(
            '<div style="display:flex;gap:6px;flex-wrap:wrap;min-width:220px;">{}</div>',
            format_html_join(
                "",
                '<a href="{}" style="display:inline-flex;align-items:center;padding:5px 8px;border-radius:8px;'
                'background:#f8fafc;border:1px solid #e2e8f0;color:#0f2544;font-size:12px;'
                'font-weight:800;text-decoration:none;white-space:nowrap;">{}</a>',
                links,
            ),
        )

    @admin.display(description=_("Số tiền phạt"))
    def so_tien_phat_vnd(self, obj):
        amount = f"{obj.so_tien_phat or 0:,.0f} VNĐ"
        return format_html("{}", amount)

    @admin.action(description=_("Duyệt biên bản đã chọn"))
    def approve_records(self, request, queryset):
        self._bulk_update_records(
            request,
            queryset.exclude(trang_thai="DA_DUYET"),
            updates={"trang_thai": "DA_DUYET"},
            note="Duyệt biên bản vi phạm bằng bulk action trong Django Admin.",
            success_message=_("Đã duyệt %(count)s biên bản vi phạm."),
            level=messages.SUCCESS,
        )

    @admin.action(description=_("Từ chối / hủy biên bản đã chọn"))
    def reject_records(self, request, queryset):
        self._bulk_update_records(
            request,
            queryset.exclude(trang_thai="TU_CHOI"),
            updates={"trang_thai": "TU_CHOI"},
            note="Từ chối/hủy biên bản vi phạm bằng bulk action trong Django Admin.",
            success_message=_("Đã từ chối/hủy %(count)s biên bản vi phạm."),
            level=messages.WARNING,
        )

    @admin.action(description=_("Chuyển hình thức xử lý sang Cảnh cáo"))
    def mark_warning(self, request, queryset):
        self._bulk_update_records(
            request,
            queryset,
            updates={"hinh_thuc_xu_ly": "CANH_CAO", "so_tien_phat": 0},
            note="Chuyển biên bản vi phạm sang hình thức cảnh cáo bằng bulk action trong Django Admin.",
            success_message=_("Đã chuyển %(count)s biên bản sang Cảnh cáo."),
            level=messages.SUCCESS,
        )

    @admin.action(description=_("Chuyển hình thức xử lý sang Phạt tiền"))
    def mark_money_penalty(self, request, queryset):
        self._bulk_update_records(
            request,
            queryset.exclude(hinh_thuc_xu_ly="PHAT_TIEN"),
            updates={"hinh_thuc_xu_ly": "PHAT_TIEN"},
            note="Chuyển biên bản vi phạm sang hình thức phạt tiền bằng bulk action trong Django Admin.",
            success_message=_("Đã chuyển %(count)s biên bản sang hình thức Phạt tiền. Vui lòng rà soát số tiền phạt."),
            level=messages.WARNING,
        )



class KetQuaKiemTraInline(admin.TabularInline):
    model = KetQuaKiemTra
    extra = 0
    fields = ("hang_muc", "dat_yeu_cau", "ghi_chu")
    verbose_name = _("Kết quả kiểm tra")
    verbose_name_plural = _("Chi tiết hạng mục kiểm tra")


class BienBanThanhTraStatusFilter(admin.SimpleListFilter):
    title = _("Tình trạng biên bản")
    parameter_name = "ops"

    def lookups(self, request, model_admin):
        return (
            ("today", _("Hôm nay")),
            ("month", _("Tháng này")),
            ("good_score", _("Điểm tốt")),
            ("low_score", _("Điểm thấp")),
            ("failed_items", _("Có hạng mục không đạt")),
            ("missing_target", _("Thiếu mục tiêu")),
            ("missing_inspector", _("Thiếu thanh tra viên")),
            ("missing_conclusion", _("Thiếu kết luận")),
            ("no_details", _("Chưa có chi tiết")),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        value = self.value()
        if value == "today":
            return queryset.filter(thoi_gian__date=today)
        if value == "month":
            return queryset.filter(thoi_gian__date__gte=month_start)
        if value == "good_score":
            return queryset.filter(diem_danh_gia__gte=90)
        if value == "low_score":
            return queryset.filter(diem_danh_gia__lt=70)
        if value == "failed_items":
            return queryset.filter(failed_items_count__gt=0)
        if value == "missing_target":
            return queryset.filter(muc_tieu__isnull=True)
        if value == "missing_inspector":
            return queryset.filter(thanh_tra_vien__isnull=True)
        if value == "missing_conclusion":
            return queryset.filter(Q(ket_luan="") | Q(ket_luan__isnull=True))
        if value == "no_details":
            return queryset.filter(detail_items_count=0)
        return queryset


@admin.register(BienBanThanhTra)
class BienBanThanhTraAdmin(admin.ModelAdmin):
    change_list_template = "admin/inspection/bienbanthanhtra/change_list.html"
    list_display = ("record_display", "target_display", "inspector_display", "score_display", "checklist_display", "row_actions")
    list_filter = (BienBanThanhTraStatusFilter, "thoi_gian", "muc_tieu", "thanh_tra_vien")
    list_select_related = (
        "thanh_tra_vien",
        "thanh_tra_vien__phong_ban",
        "thanh_tra_vien__chuc_danh",
        "muc_tieu",
        "muc_tieu__hop_dong",
        "muc_tieu__hop_dong__khach_hang_cu",
    )
    search_fields = (
        "id",
        "ket_luan",
        "thanh_tra_vien__ho_ten",
        "thanh_tra_vien__ma_nv",
        "muc_tieu__ten_muc_tieu",
        "muc_tieu__dia_chi",
        "muc_tieu__hop_dong__so_hop_dong",
        "muc_tieu__hop_dong__khach_hang_cu__ten_cong_ty",
        "chi_tiet__hang_muc__ten_hang_muc",
        "chi_tiet__ghi_chu",
    )
    autocomplete_fields = ("thanh_tra_vien", "muc_tieu")
    readonly_fields = ("created_record_hint",)
    date_hierarchy = "thoi_gian"
    list_per_page = 25
    save_on_top = True
    inlines = [KetQuaKiemTraInline]
    fieldsets = (
        (_("Thông tin biên bản"), {"fields": (("thoi_gian", "diem_danh_gia"), ("thanh_tra_vien", "muc_tieu"), "created_record_hint")} ),
        (_("Kết luận thanh tra"), {"fields": ("ket_luan",), "description": _("Kết luận cần đủ rõ để đối soát với hạng mục kiểm tra, biên bản vi phạm và xử lý vận hành nếu có.")}),
    )



    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inspection_bienbanthanhtra_export_csv",
            ),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "thanh_tra_vien",
                "thanh_tra_vien__phong_ban",
                "thanh_tra_vien__chuc_danh",
                "muc_tieu",
                "muc_tieu__hop_dong",
                "muc_tieu__hop_dong__khach_hang_cu",
            )
            .annotate(
                detail_items_count=Count("chi_tiet", distinct=True),
                failed_items_count=Count("chi_tiet", filter=Q(chi_tiet__dat_yeu_cau=False), distinct=True),
                passed_items_count=Count("chi_tiet", filter=Q(chi_tiet__dat_yeu_cau=True), distinct=True),
            )
        )

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        base_url = _admin_changelist_url("inspection", "bienbanthanhtra")
        current_query = request.GET.urlencode()
        export_url = _safe_reverse("admin:inspection_bienbanthanhtra_export_csv", fallback=base_url)
        if current_query:
            export_url = f"{export_url}?{current_query}"
        extra_context = extra_context or {}
        extra_context.update(
            {
                "scmd_inspection_report_stats": {
                    "total": qs.count(),
                    "today": qs.filter(thoi_gian__date=today).count(),
                    "month": qs.filter(thoi_gian__date__gte=month_start).count(),
                    "good_score": qs.filter(diem_danh_gia__gte=90).count(),
                    "low_score": qs.filter(diem_danh_gia__lt=70).count(),
                    "failed_items": qs.filter(failed_items_count__gt=0).count(),
                    "missing_target": qs.filter(muc_tieu__isnull=True).count(),
                    "missing_inspector": qs.filter(thanh_tra_vien__isnull=True).count(),
                    "missing_conclusion": qs.filter(Q(ket_luan="") | Q(ket_luan__isnull=True)).count(),
                    "no_details": qs.filter(detail_items_count=0).count(),
                },
                "scmd_inspection_report_links": {
                    "list": base_url,
                    "add": _safe_reverse("admin:inspection_bienbanthanhtra_add", fallback=base_url),
                    "export_csv": export_url,
                    "inspection_runs": _admin_changelist_url("inspection", "dotthanhtra", fallback=base_url),
                    "violations": _admin_changelist_url("inspection", "bienbanvipham", fallback=base_url),
                    "categories": _admin_changelist_url("inspection", "hangmuckiemtra", fallback=base_url),
                    "targets": _admin_changelist_url("clients", "muctieu", fallback=base_url),
                    "employees": _admin_changelist_url("users", "nhanvien", fallback=base_url),
                    "dashboard": _safe_reverse("inspection:dashboard", fallback=base_url),
                    "today": _append_query(base_url, {"ops": "today"}),
                    "month": _append_query(base_url, {"ops": "month"}),
                    "good_score": _append_query(base_url, {"ops": "good_score"}),
                    "low_score": _append_query(base_url, {"ops": "low_score"}),
                    "failed_items": _append_query(base_url, {"ops": "failed_items"}),
                    "missing_target": _append_query(base_url, {"ops": "missing_target"}),
                    "missing_inspector": _append_query(base_url, {"ops": "missing_inspector"}),
                    "missing_conclusion": _append_query(base_url, {"ops": "missing_conclusion"}),
                    "no_details": _append_query(base_url, {"ops": "no_details"}),
                },
            }
        )
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="scmd-pro-bien-ban-thanh-tra.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Mã biên bản",
            "Thời gian",
            "Thanh tra viên",
            "Mã nhân viên",
            "Mục tiêu",
            "Hợp đồng",
            "Khách hàng",
            "Điểm đánh giá",
            "Tổng hạng mục",
            "Hạng mục đạt",
            "Hạng mục không đạt",
            "Kết luận",
        ])
        for obj in queryset.iterator(chunk_size=200):
            inspector = obj.thanh_tra_vien
            target = obj.muc_tieu
            contract = getattr(target, "hop_dong", None) if target else None
            customer = getattr(contract, "khach_hang_cu", None) if contract else None
            writer.writerow([
                f"BBTT-{obj.pk}",
                timezone.localtime(obj.thoi_gian).strftime("%d/%m/%Y %H:%M") if obj.thoi_gian else "",
                getattr(inspector, "ho_ten", "") or "",
                getattr(inspector, "ma_nv", None) or getattr(inspector, "ma_nhan_vien", "") or "",
                getattr(target, "ten_muc_tieu", "") or "",
                getattr(contract, "so_hop_dong", "") or "",
                getattr(customer, "ten_cong_ty", "") or "",
                obj.diem_danh_gia,
                getattr(obj, "detail_items_count", 0),
                getattr(obj, "passed_items_count", 0),
                getattr(obj, "failed_items_count", 0),
                (obj.ket_luan or "").replace("\r", " ").replace("\n", " "),
            ])
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.ACCESS,
            module="inspection",
            model_name="BienBanThanhTra",
            object_id="bulk-export",
            changes={"count": queryset.count(), "filters": request.GET.dict()},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xuất CSV danh sách biên bản thanh tra từ Django Admin.",
        )
        return response

    def save_model(self, request, obj, form, change):
        before = {}
        if change and obj.pk:
            old = type(obj).objects.filter(pk=obj.pk).first()
            if old:
                before = {
                    "thanh_tra_vien_id": old.thanh_tra_vien_id,
                    "muc_tieu_id": old.muc_tieu_id,
                    "thoi_gian": _audit_json_value(old.thoi_gian),
                    "diem_danh_gia": old.diem_danh_gia,
                    "ket_luan": old.ket_luan,
                }
        super().save_model(request, obj, form, change)
        after = {
            "thanh_tra_vien_id": obj.thanh_tra_vien_id,
            "muc_tieu_id": obj.muc_tieu_id,
            "thoi_gian": _audit_json_value(obj.thoi_gian),
            "diem_danh_gia": obj.diem_danh_gia,
            "ket_luan": obj.ket_luan,
        }
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
            module="inspection",
            model_name="BienBanThanhTra",
            object_id=str(obj.pk),
            changes={"before": before, "after": after},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Ghi nhận thay đổi biên bản thanh tra qua Django Admin.",
        )

    def delete_model(self, request, obj):
        snapshot = {
            "thanh_tra_vien_id": obj.thanh_tra_vien_id,
            "muc_tieu_id": obj.muc_tieu_id,
            "thoi_gian": _audit_json_value(obj.thoi_gian),
            "diem_danh_gia": obj.diem_danh_gia,
            "ket_luan": obj.ket_luan,
        }
        pk = obj.pk
        super().delete_model(request, obj)
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.DELETE,
            module="inspection",
            model_name="BienBanThanhTra",
            object_id=str(pk),
            changes={"before": snapshot, "after": None},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xóa biên bản thanh tra qua Django Admin.",
        )

    @admin.display(description=_("Biên bản"))
    def record_display(self, obj):
        when = timezone.localtime(obj.thoi_gian).strftime("%d/%m/%Y %H:%M") if obj.thoi_gian else "-"
        return format_html(
            '<div><b>BBTT-{}</b><div style="font-size:12px;color:#64748b;">{}</div></div>',
            obj.pk,
            when,
        )

    @admin.display(description=_("Mục tiêu / hợp đồng"))
    def target_display(self, obj):
        if not obj.muc_tieu:
            return format_html('<span style="color:#b45309;font-weight:800;">Chưa gắn mục tiêu</span>')
        target_url = _admin_change_url(obj.muc_tieu)
        contract = getattr(obj.muc_tieu, "hop_dong", None)
        contract_text = getattr(contract, "so_hop_dong", "Chưa có HĐ") if contract else "Chưa có HĐ"
        customer = getattr(contract, "khach_hang_cu", None) if contract else None
        customer_text = getattr(customer, "ten_cong_ty", "") if customer else ""
        return format_html(
            '<a href="{}"><b>{}</b></a><div style="font-size:12px;color:#64748b;">{}</div><div style="font-size:12px;color:#64748b;">{}</div>',
            target_url,
            obj.muc_tieu.ten_muc_tieu,
            contract_text,
            customer_text,
        )

    @admin.display(description=_("Thanh tra viên"))
    def inspector_display(self, obj):
        if not obj.thanh_tra_vien:
            return format_html('<span style="color:#b45309;font-weight:800;">Chưa gắn thanh tra viên</span>')
        employee_url = _admin_change_url(obj.thanh_tra_vien)
        employee_code = getattr(obj.thanh_tra_vien, "ma_nv", None) or getattr(obj.thanh_tra_vien, "ma_nhan_vien", "") or ""
        title = getattr(getattr(obj.thanh_tra_vien, "chuc_danh", None), "ten_chuc_danh", "")
        return format_html(
            '<a href="{}"><b>{}</b></a><div style="font-size:12px;color:#64748b;">{}</div><div style="font-size:12px;color:#64748b;">{}</div>',
            employee_url,
            obj.thanh_tra_vien.ho_ten,
            employee_code,
            title,
        )

    @admin.display(description=_("Điểm"), ordering="diem_danh_gia")
    def score_display(self, obj):
        score = obj.diem_danh_gia or 0
        if score >= 90:
            bg, fg, label = "#dcfce7", "#166534", "Tốt"
        elif score >= 70:
            bg, fg, label = "#dbeafe", "#1e40af", "Cần theo dõi"
        else:
            bg, fg, label = "#fee2e2", "#991b1b", "Cần xử lý"
        return format_html(
            '<div><span style="display:inline-block;padding:4px 8px;border-radius:999px;background:{};color:{};font-size:11px;font-weight:800;">{} điểm</span>'
            '<div style="font-size:12px;color:{};font-weight:800;margin-top:4px;">{}</div></div>',
            bg, fg, score, fg, label,
        )

    @admin.display(description=_("Checklist"))
    def checklist_display(self, obj):
        detail_count = getattr(obj, "detail_items_count", 0)
        failed_count = getattr(obj, "failed_items_count", 0)
        if detail_count == 0:
            return format_html('<span style="color:#b45309;font-weight:800;">Chưa có chi tiết</span>')
        return format_html(
            '<div><b>{}/{} đạt</b><div style="font-size:12px;color:{};font-weight:800;">{} không đạt</div></div>',
            getattr(obj, "passed_items_count", 0),
            detail_count,
            "#991b1b" if failed_count else "#166534",
            failed_count,
        )

    @admin.display(description=_("Thao tác"))
    def row_actions(self, obj):
        edit_url = _admin_change_url(obj)
        target_url = _admin_change_url(obj.muc_tieu) if obj.muc_tieu else _admin_changelist_url("clients", "muctieu")
        employee_url = _admin_change_url(obj.thanh_tra_vien) if obj.thanh_tra_vien else _admin_changelist_url("users", "nhanvien")
        violations_url = _append_query(_admin_changelist_url("inspection", "bienbanvipham"), {"muc_tieu__id__exact": obj.muc_tieu_id}) if obj.muc_tieu_id else _admin_changelist_url("inspection", "bienbanvipham")
        runs_url = _append_query(_admin_changelist_url("inspection", "dotthanhtra"), {"muc_tieu__id__exact": obj.muc_tieu_id}) if obj.muc_tieu_id else _admin_changelist_url("inspection", "dotthanhtra")
        links = [
            (edit_url, "Sửa"),
            (target_url, "Mục tiêu"),
            (employee_url, "Nhân sự"),
            (runs_url, "Đợt TT"),
            (violations_url, "Vi phạm"),
        ]
        return format_html(
            '<div style="display:flex;gap:6px;flex-wrap:wrap;min-width:220px;">{}</div>',
            format_html_join(
                "",
                '<a href="{}" style="display:inline-flex;align-items:center;padding:5px 8px;border-radius:8px;'
                'background:#f8fafc;border:1px solid #e2e8f0;color:#0f2544;font-size:12px;'
                'font-weight:800;text-decoration:none;white-space:nowrap;">{}</a>',
                links,
            ),
        )

    @admin.display(description=_("Gợi ý"))
    def created_record_hint(self, obj=None):
        return _("Biên bản thanh tra nên có đầy đủ mục tiêu, thanh tra viên, điểm đánh giá, kết luận và chi tiết hạng mục để phục vụ đối soát vận hành.")


class TrainingOperationalFilter(admin.SimpleListFilter):
    title = _("Tình trạng huấn luyện")
    parameter_name = "ops"

    def lookups(self, request, model_admin):
        return (
            ("today", _("Hôm nay")),
            ("month", _("Tháng này")),
            ("missing_topic", _("Thiếu chủ đề")),
            ("missing_trainer", _("Thiếu người đào tạo")),
            ("missing_location", _("Thiếu địa điểm")),
            ("no_participants", _("Chưa có học viên")),
            ("small_class", _("Lớp nhỏ")),
            ("large_class", _("Lớp đông")),
        )

    def queryset(self, request, queryset):
        value = self.value()
        today = timezone.localdate()
        month_start = today.replace(day=1)
        if value == "today":
            return queryset.filter(thoi_gian__date=today)
        if value == "month":
            return queryset.filter(thoi_gian__date__gte=month_start)
        if value == "missing_topic":
            return queryset.filter(Q(chu_de="") | Q(chu_de__isnull=True))
        if value == "missing_trainer":
            return queryset.filter(nguoi_dao_tao__isnull=True)
        if value == "missing_location":
            return queryset.filter(Q(dia_diem="") | Q(dia_diem__isnull=True))
        if value == "no_participants":
            return queryset.filter(participant_count=0)
        if value == "small_class":
            return queryset.filter(participant_count__gt=0, participant_count__lt=5)
        if value == "large_class":
            return queryset.filter(participant_count__gte=20)
        return queryset

@admin.register(BuoiHuanLuyen)
class BuoiHuanLuyenAdmin(admin.ModelAdmin):
    change_list_template = "admin/inspection/buoihuanluyen/change_list.html"
    list_display = ("training_display", "trainer_display", "thoi_gian", "dia_diem_display", "participants_display", "row_actions")
    list_filter = (TrainingOperationalFilter, "thoi_gian", "nguoi_dao_tao")
    list_select_related = ("nguoi_dao_tao", "nguoi_dao_tao__phong_ban", "nguoi_dao_tao__chuc_danh")
    search_fields = (
        "chu_de",
        "dia_diem",
        "nguoi_dao_tao__ho_ten",
        "nguoi_dao_tao__ma_nv",
        "danh_sach_tham_gia__ho_ten",
        "danh_sach_tham_gia__ma_nv",
    )
    filter_horizontal = ("danh_sach_tham_gia",)
    autocomplete_fields = ("nguoi_dao_tao",)
    readonly_fields = ("created_record_hint",)
    date_hierarchy = "thoi_gian"
    list_per_page = 25
    save_on_top = True
    fieldsets = (
        (_("Thông tin huấn luyện"), {"fields": (("chu_de", "thoi_gian"), ("nguoi_dao_tao", "dia_diem"), "created_record_hint")}),
        (_("Học viên tham gia"), {"fields": ("danh_sach_tham_gia",), "description": _("Danh sách tham gia là dữ liệu đối soát năng lực, kỷ luật và tuân thủ đào tạo nội bộ.")}),
    )



    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inspection_buoihuanluyen_export_csv",
            ),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("nguoi_dao_tao", "nguoi_dao_tao__phong_ban", "nguoi_dao_tao__chuc_danh")
            .prefetch_related("danh_sach_tham_gia")
            .annotate(participant_count=Count("danh_sach_tham_gia", distinct=True))
        )

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        base_url = _admin_changelist_url("inspection", "buoihuanluyen")
        current_query = request.GET.urlencode()
        export_url = _safe_reverse("admin:inspection_buoihuanluyen_export_csv", fallback=base_url)
        if current_query:
            export_url = f"{export_url}?{current_query}"

        extra_context = extra_context or {}
        extra_context.update(
            {
                "scmd_training_stats": {
                    "total": qs.count(),
                    "today": qs.filter(thoi_gian__date=today).count(),
                    "month": qs.filter(thoi_gian__date__gte=month_start).count(),
                    "missing_topic": qs.filter(Q(chu_de="") | Q(chu_de__isnull=True)).count(),
                    "missing_trainer": qs.filter(nguoi_dao_tao__isnull=True).count(),
                    "missing_location": qs.filter(Q(dia_diem="") | Q(dia_diem__isnull=True)).count(),
                    "no_participants": qs.filter(participant_count=0).count(),
                    "small_class": qs.filter(participant_count__gt=0, participant_count__lt=5).count(),
                    "large_class": qs.filter(participant_count__gte=20).count(),
                },
                "scmd_training_links": {
                    "list": base_url,
                    "add": _safe_reverse("admin:inspection_buoihuanluyen_add", fallback=base_url),
                    "export_csv": export_url,
                    "employees": _admin_changelist_url("users", "nhanvien", fallback=base_url),
                    "violations": _admin_changelist_url("inspection", "bienbanvipham", fallback=base_url),
                    "inspection_reports": _admin_changelist_url("inspection", "bienbanthanhtra", fallback=base_url),
                    "inspection_runs": _admin_changelist_url("inspection", "dotthanhtra", fallback=base_url),
                    "dashboard": _safe_reverse("inspection:dashboard", fallback=base_url),
                    "today": _append_query(base_url, {"ops": "today"}),
                    "month": _append_query(base_url, {"ops": "month"}),
                    "missing_topic": _append_query(base_url, {"ops": "missing_topic"}),
                    "missing_trainer": _append_query(base_url, {"ops": "missing_trainer"}),
                    "missing_location": _append_query(base_url, {"ops": "missing_location"}),
                    "no_participants": _append_query(base_url, {"ops": "no_participants"}),
                    "small_class": _append_query(base_url, {"ops": "small_class"}),
                    "large_class": _append_query(base_url, {"ops": "large_class"}),
                },
            }
        )
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="scmd-pro-buoi-huan-luyen.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Mã buổi",
            "Chủ đề",
            "Thời gian",
            "Địa điểm",
            "Người đào tạo",
            "Mã người đào tạo",
            "Phòng ban người đào tạo",
            "Chức danh người đào tạo",
            "Số học viên",
            "Danh sách học viên",
        ])
        for obj in queryset.iterator(chunk_size=200):
            trainer = obj.nguoi_dao_tao
            participants = list(obj.danh_sach_tham_gia.all())
            writer.writerow([
                f"HL-{obj.pk}",
                obj.chu_de or "",
                timezone.localtime(obj.thoi_gian).strftime("%d/%m/%Y %H:%M") if obj.thoi_gian else "",
                obj.dia_diem or "",
                getattr(trainer, "ho_ten", "") or "",
                getattr(trainer, "ma_nv", None) or getattr(trainer, "ma_nhan_vien", "") or "",
                getattr(getattr(trainer, "phong_ban", None), "ten_phong_ban", "") if trainer else "",
                getattr(getattr(trainer, "chuc_danh", None), "ten_chuc_danh", "") if trainer else "",
                len(participants),
                "; ".join(getattr(item, "ho_ten", "") for item in participants),
            ])
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.ACCESS,
            module="inspection",
            model_name="BuoiHuanLuyen",
            object_id="bulk-export",
            changes={"count": queryset.count(), "filters": request.GET.dict()},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xuất CSV danh sách buổi huấn luyện từ Django Admin.",
        )
        return response

    def save_model(self, request, obj, form, change):
        before = {}
        if change and obj.pk:
            old = type(obj).objects.filter(pk=obj.pk).first()
            if old:
                before = {
                    "chu_de": old.chu_de,
                    "nguoi_dao_tao_id": old.nguoi_dao_tao_id,
                    "thoi_gian": _audit_json_value(old.thoi_gian),
                    "dia_diem": old.dia_diem,
                }
        super().save_model(request, obj, form, change)
        after = {
            "chu_de": obj.chu_de,
            "nguoi_dao_tao_id": obj.nguoi_dao_tao_id,
            "thoi_gian": _audit_json_value(obj.thoi_gian),
            "dia_diem": obj.dia_diem,
        }
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
            module="inspection",
            model_name="BuoiHuanLuyen",
            object_id=str(obj.pk),
            changes={"before": before, "after": after},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Ghi nhận thay đổi buổi huấn luyện qua Django Admin.",
        )

    def save_related(self, request, form, formsets, change):
        before_ids = []
        if change and form.instance.pk:
            before_ids = list(type(form.instance).objects.get(pk=form.instance.pk).danh_sach_tham_gia.values_list("pk", flat=True))
        super().save_related(request, form, formsets, change)
        after_ids = list(form.instance.danh_sach_tham_gia.values_list("pk", flat=True))
        if before_ids != after_ids:
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action=AuditLog.Action.UPDATE,
                module="inspection",
                model_name="BuoiHuanLuyen",
                object_id=str(form.instance.pk),
                changes={"participants_before": before_ids, "participants_after": after_ids},
                ip_address=_request_ip(request) or None,
                user_agent=_request_ua(request),
                note="Cập nhật danh sách học viên tham gia buổi huấn luyện qua Django Admin.",
            )

    def delete_model(self, request, obj):
        snapshot = {
            "chu_de": obj.chu_de,
            "nguoi_dao_tao_id": obj.nguoi_dao_tao_id,
            "thoi_gian": _audit_json_value(obj.thoi_gian),
            "dia_diem": obj.dia_diem,
            "participants": list(obj.danh_sach_tham_gia.values_list("pk", flat=True)),
        }
        pk = obj.pk
        super().delete_model(request, obj)
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.DELETE,
            module="inspection",
            model_name="BuoiHuanLuyen",
            object_id=str(pk),
            changes={"before": snapshot, "after": None},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xóa buổi huấn luyện qua Django Admin.",
        )

    @admin.display(description=_("Buổi huấn luyện"), ordering="chu_de")
    def training_display(self, obj):
        topic = obj.chu_de or "Chưa có chủ đề"
        when = timezone.localtime(obj.thoi_gian).strftime("%d/%m/%Y %H:%M") if obj.thoi_gian else "-"
        return format_html(
            '<div><b>{}</b><div style="font-size:12px;color:#64748b;">HL-{} · {}</div></div>',
            topic,
            obj.pk,
            when,
        )

    @admin.display(description=_("Người đào tạo"), ordering="nguoi_dao_tao__ho_ten")
    def trainer_display(self, obj):
        if not obj.nguoi_dao_tao:
            return format_html('<span style="color:#b45309;font-weight:800;">Chưa gắn người đào tạo</span>')
        trainer_url = _admin_change_url(obj.nguoi_dao_tao)
        employee_code = getattr(obj.nguoi_dao_tao, "ma_nv", None) or getattr(obj.nguoi_dao_tao, "ma_nhan_vien", "") or ""
        title = getattr(getattr(obj.nguoi_dao_tao, "chuc_danh", None), "ten_chuc_danh", "")
        return format_html(
            '<a href="{}"><b>{}</b></a><div style="font-size:12px;color:#64748b;">{}</div><div style="font-size:12px;color:#64748b;">{}</div>',
            trainer_url,
            obj.nguoi_dao_tao.ho_ten,
            employee_code,
            title,
        )

    @admin.display(description=_("Địa điểm"), ordering="dia_diem")
    def dia_diem_display(self, obj):
        if obj.dia_diem:
            return obj.dia_diem
        return format_html('<span style="color:#b45309;font-weight:800;">Chưa có địa điểm</span>')

    @admin.display(description=_("Học viên"), ordering="participant_count")
    def participants_display(self, obj):
        count = getattr(obj, "participant_count", None)
        if count is None:
            count = obj.danh_sach_tham_gia.count()
        if count == 0:
            return format_html('<span style="color:#991b1b;font-weight:800;">Chưa có học viên</span>')
        tone = "#166534" if count >= 5 else "#b45309"
        label = "Đủ nhóm" if count >= 5 else "Lớp nhỏ"
        return format_html(
            '<div><b>{} học viên</b><div style="font-size:12px;color:{};font-weight:800;">{}</div></div>',
            count,
            tone,
            label,
        )

    @admin.display(description=_("Thao tác"))
    def row_actions(self, obj):
        edit_url = _admin_change_url(obj)
        trainer_url = _admin_change_url(obj.nguoi_dao_tao) if obj.nguoi_dao_tao else _admin_changelist_url("users", "nhanvien")
        employees_url = _admin_changelist_url("users", "nhanvien")
        violations_url = _admin_changelist_url("inspection", "bienbanvipham")
        links = [
            (edit_url, "Sửa"),
            (trainer_url, "Giảng viên"),
            (employees_url, "Nhân sự"),
            (violations_url, "Vi phạm"),
        ]
        return format_html(
            '<div style="display:flex;gap:6px;flex-wrap:wrap;min-width:190px;">{}</div>',
            format_html_join(
                "",
                '<a href="{}" style="display:inline-flex;align-items:center;padding:5px 8px;border-radius:8px;'
                'background:#f8fafc;border:1px solid #e2e8f0;color:#0f2544;font-size:12px;'
                'font-weight:800;text-decoration:none;white-space:nowrap;">{}</a>',
                links,
            ),
        )

    @admin.display(description=_("Gợi ý"))
    def created_record_hint(self, obj=None):
        return _("Buổi huấn luyện cần có chủ đề, người đào tạo, thời gian, địa điểm và danh sách học viên để phục vụ đối soát năng lực và tuân thủ nội bộ.")


class HangMucKiemTraOperationalFilter(admin.SimpleListFilter):
    title = _("Tình trạng cấu hình")
    parameter_name = "ops"

    def lookups(self, request, model_admin):
        return (
            ("missing_description", _("Thiếu tiêu chuẩn đánh giá")),
            ("used", _("Đã dùng trong biên bản")),
            ("unused", _("Chưa dùng trong biên bản")),
            ("has_failures", _("Có lần không đạt")),
            ("only_passed", _("Chưa phát sinh không đạt")),
            ("many_reports", _("Dùng nhiều")),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "missing_description":
            return queryset.filter(Q(mo_ta="") | Q(mo_ta__isnull=True))
        if value == "used":
            return queryset.filter(result_count__gt=0)
        if value == "unused":
            return queryset.filter(result_count=0)
        if value == "has_failures":
            return queryset.filter(failed_count__gt=0)
        if value == "only_passed":
            return queryset.filter(result_count__gt=0, failed_count=0)
        if value == "many_reports":
            return queryset.filter(report_count__gte=5)
        return queryset


@admin.register(HangMucKiemTra)
class HangMucKiemTraAdmin(admin.ModelAdmin):
    change_list_template = "admin/inspection/hangmuckiemtra/change_list.html"
    list_display = ("category_display", "description_display", "usage_display", "quality_display", "row_actions")
    list_filter = (HangMucKiemTraOperationalFilter,)
    search_fields = (
        "ten_hang_muc",
        "mo_ta",
        "ketquakiemtra__ghi_chu",
        "ketquakiemtra__bien_ban__ket_luan",
        "ketquakiemtra__bien_ban__muc_tieu__ten_muc_tieu",
    )
    readonly_fields = ("created_record_hint",)
    list_per_page = 25
    save_on_top = True
    fieldsets = (
        (_("Thông tin hạng mục"), {"fields": ("ten_hang_muc", "mo_ta", "created_record_hint")} ),
    )



    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inspection_hangmuckiemtra_export_csv",
            ),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                result_count=Count("ketquakiemtra", distinct=True),
                passed_count=Count("ketquakiemtra", filter=Q(ketquakiemtra__dat_yeu_cau=True), distinct=True),
                failed_count=Count("ketquakiemtra", filter=Q(ketquakiemtra__dat_yeu_cau=False), distinct=True),
                report_count=Count("ketquakiemtra__bien_ban", distinct=True),
            )
        )

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        base_url = _admin_changelist_url("inspection", "hangmuckiemtra")
        current_query = request.GET.urlencode()
        export_url = _safe_reverse("admin:inspection_hangmuckiemtra_export_csv", fallback=base_url)
        if current_query:
            export_url = f"{export_url}?{current_query}"
        extra_context = extra_context or {}
        extra_context.update(
            {
                "scmd_check_item_stats": {
                    "total": qs.count(),
                    "missing_description": qs.filter(Q(mo_ta="") | Q(mo_ta__isnull=True)).count(),
                    "used": qs.filter(result_count__gt=0).count(),
                    "unused": qs.filter(result_count=0).count(),
                    "has_failures": qs.filter(failed_count__gt=0).count(),
                    "only_passed": qs.filter(result_count__gt=0, failed_count=0).count(),
                    "many_reports": qs.filter(report_count__gte=5).count(),
                },
                "scmd_check_item_links": {
                    "list": base_url,
                    "add": _safe_reverse("admin:inspection_hangmuckiemtra_add", fallback=base_url),
                    "export_csv": export_url,
                    "inspection_reports": _admin_changelist_url("inspection", "bienbanthanhtra", fallback=base_url),
                    "inspection_runs": _admin_changelist_url("inspection", "dotthanhtra", fallback=base_url),
                    "violations": _admin_changelist_url("inspection", "bienbanvipham", fallback=base_url),
                    "targets": _admin_changelist_url("clients", "muctieu", fallback=base_url),
                    "dashboard": _safe_reverse("inspection:dashboard", fallback=base_url),
                    "missing_description": _append_query(base_url, {"ops": "missing_description"}),
                    "used": _append_query(base_url, {"ops": "used"}),
                    "unused": _append_query(base_url, {"ops": "unused"}),
                    "has_failures": _append_query(base_url, {"ops": "has_failures"}),
                    "only_passed": _append_query(base_url, {"ops": "only_passed"}),
                    "many_reports": _append_query(base_url, {"ops": "many_reports"}),
                },
            }
        )
        return super().changelist_view(request, extra_context=extra_context)

    def export_csv_view(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="scmd-pro-hang-muc-kiem-tra.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Mã hạng mục",
            "Tên hạng mục",
            "Tiêu chuẩn đánh giá",
            "Số lần dùng",
            "Số biên bản liên quan",
            "Số lần đạt",
            "Số lần không đạt",
            "Tình trạng",
        ])
        for obj in queryset.iterator(chunk_size=200):
            result_count = getattr(obj, "result_count", 0)
            failed_count = getattr(obj, "failed_count", 0)
            if result_count == 0:
                status = "Chưa dùng"
            elif failed_count:
                status = "Có lần không đạt"
            else:
                status = "Đang đạt"
            writer.writerow([
                f"HMKT-{obj.pk}",
                obj.ten_hang_muc,
                (obj.mo_ta or "").replace("\r", " ").replace("\n", " "),
                result_count,
                getattr(obj, "report_count", 0),
                getattr(obj, "passed_count", 0),
                failed_count,
                status,
            ])
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.ACCESS,
            module="inspection",
            model_name="HangMucKiemTra",
            object_id="bulk-export",
            changes={"count": queryset.count(), "filters": request.GET.dict()},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xuất CSV danh sách hạng mục kiểm tra từ Django Admin.",
        )
        return response

    def save_model(self, request, obj, form, change):
        before = {}
        if change and obj.pk:
            old = type(obj).objects.filter(pk=obj.pk).first()
            if old:
                before = {"ten_hang_muc": old.ten_hang_muc, "mo_ta": old.mo_ta}
        super().save_model(request, obj, form, change)
        after = {"ten_hang_muc": obj.ten_hang_muc, "mo_ta": obj.mo_ta}
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
            module="inspection",
            model_name="HangMucKiemTra",
            object_id=str(obj.pk),
            changes={"before": before, "after": after},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Ghi nhận thay đổi hạng mục kiểm tra qua Django Admin.",
        )

    def delete_model(self, request, obj):
        snapshot = {"ten_hang_muc": obj.ten_hang_muc, "mo_ta": obj.mo_ta}
        pk = obj.pk
        super().delete_model(request, obj)
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.DELETE,
            module="inspection",
            model_name="HangMucKiemTra",
            object_id=str(pk),
            changes={"before": snapshot, "after": None},
            ip_address=_request_ip(request) or None,
            user_agent=_request_ua(request),
            note="Xóa hạng mục kiểm tra qua Django Admin.",
        )

    @admin.display(description=_("Hạng mục"), ordering="ten_hang_muc")
    def category_display(self, obj):
        return format_html(
            '<div><b>{}</b><div style="font-size:12px;color:#64748b;">HMKT-{}</div></div>',
            obj.ten_hang_muc,
            obj.pk,
        )

    @admin.display(description=_("Tiêu chuẩn đánh giá"), ordering="mo_ta")
    def description_display(self, obj):
        if obj.mo_ta:
            return format_html(
                '<div style="max-width:420px;white-space:normal;line-height:1.35;color:#334155;">{}</div>',
                obj.mo_ta,
            )
        return format_html('<span style="color:#b45309;font-weight:800;">Chưa có tiêu chuẩn</span>')

    @admin.display(description=_("Tần suất sử dụng"), ordering="result_count")
    def usage_display(self, obj):
        result_count = getattr(obj, "result_count", 0)
        report_count = getattr(obj, "report_count", 0)
        if result_count == 0:
            return format_html('<span style="color:#b45309;font-weight:800;">Chưa dùng trong biên bản</span>')
        return format_html(
            '<div><b>{} lần kiểm tra</b><div style="font-size:12px;color:#64748b;">{} biên bản liên quan</div></div>',
            result_count,
            report_count,
        )

    @admin.display(description=_("Kết quả"), ordering="failed_count")
    def quality_display(self, obj):
        result_count = getattr(obj, "result_count", 0)
        passed_count = getattr(obj, "passed_count", 0)
        failed_count = getattr(obj, "failed_count", 0)
        if result_count == 0:
            return format_html('<span style="color:#64748b;font-weight:800;">Chưa có dữ liệu</span>')
        tone = "#991b1b" if failed_count else "#166534"
        return format_html(
            '<div><b>{}/{} đạt</b><div style="font-size:12px;color:{};font-weight:800;">{} không đạt</div></div>',
            passed_count,
            result_count,
            tone,
            failed_count,
        )

    @admin.display(description=_("Thao tác"))
    def row_actions(self, obj):
        edit_url = _admin_change_url(obj)
        report_url = _append_query(_admin_changelist_url("inspection", "bienbanthanhtra"), {"q": obj.ten_hang_muc})
        violation_url = _admin_changelist_url("inspection", "bienbanvipham")
        links = [
            (edit_url, "Sửa"),
            (report_url, "Biên bản"),
            (violation_url, "Vi phạm"),
        ]
        return format_html(
            '<div style="display:flex;gap:6px;flex-wrap:wrap;min-width:170px;">{}</div>',
            format_html_join(
                "",
                '<a href="{}" style="display:inline-flex;align-items:center;padding:5px 8px;border-radius:8px;'
                'background:#f8fafc;border:1px solid #e2e8f0;color:#0f2544;font-size:12px;'
                'font-weight:800;text-decoration:none;white-space:nowrap;">{}</a>',
                links,
            ),
        )

    @admin.display(description=_("Gợi ý"))
    def created_record_hint(self, obj=None):
        return _("Hạng mục kiểm tra nên có tiêu chuẩn đánh giá rõ ràng để thanh tra viên chấm điểm nhất quán và đối soát được với biên bản thanh tra.")
