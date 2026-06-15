# file: inventory/views.py
from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import (
    Count,
    DecimalField,
    F,
    IntegerField,
    Max,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from main.dashboard_cta import admin_url_if_permitted, reverse_or_none
from main.dashboard_router import dashboard_access_required

from .cache_utils import build_category_cache_key
from .models import (
    ChiTietPhieuNhap,
    ChiTietPhieuXuat,
    CongCuTaiMucTieu,
    LoaiVatTu,
    PhieuNhap,
    PhieuXuat,
    VatTu,
)
from .models_ledger import InventoryLedgerEntry


INT_ZERO = Value(0, output_field=IntegerField())
DECIMAL_ZERO = Value(Decimal("0"), output_field=DecimalField(max_digits=15, decimal_places=0))


def _safe_reverse(viewname, *, args=None, kwargs=None):
    """Reverse an toàn để dashboard không vỡ khi admin/route chưa sẵn sàng."""
    return reverse_or_none(viewname, args=args, kwargs=kwargs)


def _admin_url_if_permitted(user, viewname, permission_codename, *, args=None, kwargs=None):
    return admin_url_if_permitted(user, viewname, permission_codename, args=args, kwargs=kwargs)


def _month_start(value):
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _period_from_request(request):
    today = timezone.localdate()
    now = timezone.localtime()
    period = request.GET.get("period", "month")
    if period == "today":
        return period, "Hôm nay", timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    if period == "7d":
        date_from = today - timedelta(days=6)
        return period, "7 ngày gần nhất", timezone.make_aware(timezone.datetime.combine(date_from, timezone.datetime.min.time()))
    return "month", "Tháng này", _month_start(now)


def _format_money(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


@dashboard_access_required("inventory:dashboard")
def dashboard_view(request):
    """Warehouse Workbench cho bộ phận kho."""
    period, period_label, date_from = _period_from_request(request)
    now = timezone.localtime()
    today = timezone.localdate()

    add_receipt_url = _admin_url_if_permitted(request.user, "admin:inventory_phieunhap_add", "inventory.add_phieunhap")
    add_issue_url = _admin_url_if_permitted(request.user, "admin:inventory_phieuxuat_add", "inventory.add_phieuxuat")
    receipts_url = _admin_url_if_permitted(request.user, "admin:inventory_phieunhap_changelist", "inventory.view_phieunhap")
    issues_url = _admin_url_if_permitted(request.user, "admin:inventory_phieuxuat_changelist", "inventory.view_phieuxuat")
    stock_admin_url = _admin_url_if_permitted(request.user, "admin:inventory_vattu_changelist", "inventory.view_vattu")
    target_tools_admin_url = _admin_url_if_permitted(
        request.user,
        "admin:inventory_congcutaimuctieu_changelist",
        "inventory.view_congcutaimuctieu",
    )
    ledger_url = _safe_reverse("admin:inventory_inventoryledgerentry_changelist") if request.user.is_superuser else None
    stock_report_url = _safe_reverse("inventory:bao_cao_ton")
    target_tools_url = _safe_reverse("inventory:cong_cu_muc_tieu")

    latest_purchase_price = (
        ChiTietPhieuNhap.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(vat_tu=OuterRef("pk"))
        .order_by("-phieu_nhap__ngay_nhap", "-id")
        .values("don_gia")[:1]
    )

    stock_items = VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_related("loai_vat_tu").annotate(
        gia_moi_nhat=Coalesce(
            Subquery(latest_purchase_price),
            F("gia_nhap"),
            output_field=DecimalField(max_digits=12, decimal_places=0),
        )
    )

    total_items = stock_items.count()
    total_stock_quantity = (
        stock_items.aggregate(total=Coalesce(Sum("so_luong_ton"), INT_ZERO, output_field=IntegerField()))["total"] or 0
    )
    total_inventory_value = Decimal("0")
    for item in stock_items.iterator(chunk_size=300):
        total_inventory_value += Decimal(item.so_luong_ton or 0) * Decimal(item.gia_moi_nhat or 0)

    low_stock_qs = stock_items.filter(so_luong_ton__lte=F("muc_canh_bao")).order_by("so_luong_ton", "ten_vat_tu")
    low_stock = list(low_stock_qs[:10])
    for item in low_stock:
        item.dashboard_url = _admin_url_if_permitted(
            request.user,
            "admin:inventory_vattu_change",
            "inventory.view_vattu",
            args=[item.pk],
        )
    low_stock_count = low_stock_qs.count()
    out_of_stock_count = stock_items.filter(so_luong_ton__lte=0).count()

    receipts_period = PhieuNhap.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(ngay_nhap__gte=date_from)
    issues_period = PhieuXuat.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(ngay_xuat__gte=date_from)

    receipt_draft_count = (
        PhieuNhap.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(trang_thai=PhieuNhap.TrangThai.DRAFT)
        .count()
    )
    issue_draft_count = (
        PhieuXuat.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(trang_thai=PhieuXuat.TrangThai.DRAFT)
        .count()
    )
    voided_docs_count = (
        PhieuNhap.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(trang_thai=PhieuNhap.TrangThai.VOIDED, ngay_nhap__gte=date_from)
        .count()
        + PhieuXuat.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(trang_thai=PhieuXuat.TrangThai.VOIDED, ngay_xuat__gte=date_from)
        .count()
    )

    incoming_qty = (
        ChiTietPhieuNhap.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(phieu_nhap__trang_thai=PhieuNhap.TrangThai.POSTED, phieu_nhap__ngay_nhap__gte=date_from)
        .aggregate(total=Coalesce(Sum("so_luong"), INT_ZERO, output_field=IntegerField()))["total"]
        or 0
    )
    outgoing_qty = (
        ChiTietPhieuXuat.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(phieu_xuat__trang_thai=PhieuXuat.TrangThai.POSTED, phieu_xuat__ngay_xuat__gte=date_from)
        .aggregate(total=Coalesce(Sum("so_luong"), INT_ZERO, output_field=IntegerField()))["total"]
        or 0
    )

    payroll_deduction_pending = (
        PhieuXuat.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(
            loai_xuat="BAN_TRU_LUONG",
            trang_thai=PhieuXuat.TrangThai.POSTED,
            trang_thai_thanh_toan="CHUA_TRU",
        )
        .select_related("nhan_vien_nhan")
        .order_by("-ngay_xuat")
    )
    payroll_deduction_count = payroll_deduction_pending.count()
    payroll_deduction_total = (
        payroll_deduction_pending.aggregate(
            total=Coalesce(
                Sum("tong_tien_phai_thu"),
                DECIMAL_ZERO,
                output_field=DecimalField(max_digits=15, decimal_places=0),
            )
        )["total"]
        or 0
    )

    target_tools_count = CongCuTaiMucTieu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).count()
    target_tools_quantity = (
        CongCuTaiMucTieu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .aggregate(total=Coalesce(Sum("so_luong_dang_giu"), INT_ZERO, output_field=IntegerField()))["total"]
        or 0
    )
    stale_before = today - timedelta(days=30)
    stale_target_tools_qs = (
        CongCuTaiMucTieu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .select_related("muc_tieu", "vat_tu")
        .filter(ngay_cap_gan_nhat__lte=stale_before)
        .order_by("ngay_cap_gan_nhat", "muc_tieu__ten_muc_tieu", "vat_tu__ten_vat_tu")
    )
    stale_target_tools_count = stale_target_tools_qs.count()

    recent_receipts = list(
        PhieuNhap.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .select_related("nguoi_nhap")
        .prefetch_related("chi_tiet")
        .order_by("-ngay_nhap")[:6]
    )
    recent_issues = list(
        PhieuXuat.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .select_related("nhan_vien_nhan", "muc_tieu_nhan")
        .prefetch_related("chi_tiet")
        .order_by("-ngay_xuat")[:8]
    )

    recent_documents = []
    for receipt in recent_receipts:
        recent_documents.append(
            {
                "kind": "Nhập kho",
                "code": receipt.ma_phieu,
                "time": receipt.ngay_nhap,
                "status": receipt.trang_thai,
                "status_label": receipt.get_trang_thai_display(),
                "subject": receipt.nguoi_nhap.ho_ten if receipt.nguoi_nhap else "Chưa rõ thủ kho",
                "qty": sum((line.so_luong or 0) for line in receipt.chi_tiet.all()),
                "admin_url": _admin_url_if_permitted(
                    request.user,
                    "admin:inventory_phieunhap_change",
                    "inventory.view_phieunhap",
                    args=[receipt.pk],
                ),
                "print_url": _safe_reverse("inventory:phieu_nhap_detail", args=[receipt.pk]),
            }
        )
    for issue in recent_issues:
        recipient = "Chưa rõ nơi nhận"
        if issue.loai_xuat in ["CAP_PHAT", "BAN_TRU_LUONG"] and issue.nhan_vien_nhan:
            recipient = issue.nhan_vien_nhan.ho_ten
        elif issue.loai_xuat == "CONG_CU" and issue.muc_tieu_nhan:
            recipient = issue.muc_tieu_nhan.ten_muc_tieu
        recent_documents.append(
            {
                "kind": issue.get_loai_xuat_display(),
                "code": issue.ma_phieu,
                "time": issue.ngay_xuat,
                "status": issue.trang_thai,
                "status_label": issue.get_trang_thai_display(),
                "subject": recipient,
                "qty": sum((line.so_luong or 0) for line in issue.chi_tiet.all()),
                "admin_url": _admin_url_if_permitted(
                    request.user,
                    "admin:inventory_phieuxuat_change",
                    "inventory.view_phieuxuat",
                    args=[issue.pk],
                ),
                "print_url": _safe_reverse("inventory:phieu_xuat_detail", args=[issue.pk]),
            }
        )
    recent_documents = sorted(recent_documents, key=lambda item: item["time"], reverse=True)
    reference_documents = [doc for doc in recent_documents if doc["status"] != "DRAFT"][:6]

    action_items = []
    for receipt in (
        PhieuNhap.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(trang_thai=PhieuNhap.TrangThai.DRAFT)
        .select_related("nguoi_nhap")
        .order_by("-ngay_nhap")[:4]
    ):
        action_items.append(
            {
                "priority": "Cao",
                "business": "nhap",
                "type": "Ghi sổ phiếu nhập",
                "title": receipt.ma_phieu,
                "target": receipt.nguoi_nhap.ho_ten if receipt.nguoi_nhap else "Chưa rõ thủ kho",
                "status": receipt.get_trang_thai_display(),
                "due_label": receipt.ngay_nhap.strftime("%d/%m %H:%M"),
                "time": receipt.ngay_nhap,
                "url": _admin_url_if_permitted(
                    request.user,
                    "admin:inventory_phieunhap_change",
                    "inventory.change_phieunhap",
                    args=[receipt.pk],
                ),
                "cta": "Ghi sổ",
                "tone": "warning",
            }
        )

    for issue in (
        PhieuXuat.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(trang_thai=PhieuXuat.TrangThai.DRAFT)
        .select_related("nhan_vien_nhan", "muc_tieu_nhan")
        .order_by("-ngay_xuat")[:4]
    ):
        issue_target = "Chưa rõ nơi nhận"
        if issue.loai_xuat in ["CAP_PHAT", "BAN_TRU_LUONG"] and issue.nhan_vien_nhan:
            issue_target = issue.nhan_vien_nhan.ho_ten
        elif issue.muc_tieu_nhan:
            issue_target = issue.muc_tieu_nhan.ten_muc_tieu
        action_items.append(
            {
                "priority": "Cao",
                "business": "xuat",
                "type": "Ghi sổ phiếu xuất",
                "title": issue.ma_phieu,
                "target": issue_target,
                "status": issue.get_trang_thai_display(),
                "due_label": issue.ngay_xuat.strftime("%d/%m %H:%M"),
                "time": issue.ngay_xuat,
                "url": _admin_url_if_permitted(
                    request.user,
                    "admin:inventory_phieuxuat_change",
                    "inventory.change_phieuxuat",
                    args=[issue.pk],
                ),
                "cta": "Ghi sổ",
                "tone": "danger",
            }
        )

    for item in low_stock[:4]:
        action_items.append(
            {
                "priority": "Cao" if (item.so_luong_ton or 0) <= 0 else "Vừa",
                "business": "ton",
                "type": "Kiểm tra tồn kho",
                "title": item.ten_vat_tu,
                "target": "Kho tổng",
                "status": "Hết hàng" if (item.so_luong_ton or 0) <= 0 else "Dưới định mức",
                "due_label": "—",
                "time": now - timedelta(minutes=1),
                "url": item.dashboard_url,
                "cta": "Xem tồn",
                "tone": "warning",
            }
        )

    for issue in payroll_deduction_pending[:3]:
        action_items.append(
            {
                "priority": "Vừa",
                "business": "khau-tru",
                "type": "Đối soát khấu trừ",
                "title": issue.ma_phieu,
                "target": issue.nhan_vien_nhan.ho_ten if issue.nhan_vien_nhan else "Kế toán",
                "status": "Chờ đối soát",
                "due_label": "—",
                "time": issue.ngay_xuat,
                "url": _admin_url_if_permitted(
                    request.user,
                    "admin:inventory_phieuxuat_change",
                    "inventory.view_phieuxuat",
                    args=[issue.pk],
                ),
                "cta": "Mở phiếu",
                "tone": "amber",
            }
        )

    for item in stale_target_tools_qs[:3]:
        action_items.append(
            {
                "priority": "Vừa",
                "business": "ccht",
                "type": "Kiểm tra CCHT",
                "title": item.muc_tieu.ten_muc_tieu,
                "target": item.vat_tu.ten_vat_tu,
                "status": "Cần kiểm tra",
                "due_label": "—",
                "time": timezone.make_aware(timezone.datetime.combine(item.ngay_cap_gan_nhat, timezone.datetime.min.time())),
                "url": _safe_reverse("admin:inventory_congcutaimuctieu_change", args=[item.pk]),
                "cta": "Xem CCHT",
                "tone": "blue",
            }
        )

    action_items = [item for item in action_items if item.get("url")]
    action_items = sorted(action_items, key=lambda item: item["time"], reverse=True)[:8]

    category_stock = list(
        VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .select_related("loai_vat_tu")
        .values("loai_vat_tu__ten_loai")
        .annotate(
            total_stock=Coalesce(Sum("so_luong_ton"), INT_ZERO, output_field=IntegerField()),
            item_count=Count("id"),
        )
        .order_by("-total_stock")[:6]
    )
    max_category_stock = max([row["total_stock"] for row in category_stock] or [1]) or 1
    for row in category_stock:
        row["label"] = row["loai_vat_tu__ten_loai"] or "Chưa phân loại"
        row["percent"] = round((row["total_stock"] / max_category_stock) * 100) if max_category_stock else 0

    recent_ledger = list(
        InventoryLedgerEntry.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .select_related("vat_tu", "phieu_nhap", "phieu_xuat")
        .order_by("-created_at")[:8]
    )

    metric_cards = [
        {
            "label": "Phiếu nhập nháp",
            "value": receipt_draft_count,
            "status": "Chờ ghi sổ" if receipt_draft_count else "Tốt",
            "cta": "Mở",
            "url": receipts_url,
        },
        {
            "label": "Phiếu xuất nháp",
            "value": issue_draft_count,
            "status": "Chờ ghi sổ" if issue_draft_count else "Tốt",
            "cta": "Mở",
            "url": issues_url,
        },
        {
            "label": "Cảnh báo tồn",
            "value": low_stock_count,
            "status": "Cảnh báo" if low_stock_count else "Ổn định",
            "cta": "Xem",
            "url": stock_report_url,
        },
        {
            "label": "Khấu trừ chờ đối soát",
            "value": payroll_deduction_count,
            "status": "Chờ đối soát" if payroll_deduction_count else "Không có",
            "cta": "Mở",
            "url": issues_url,
        },
        {
            "label": "CCHT tại mục tiêu",
            "value": target_tools_count,
            "status": "Đang theo dõi" if target_tools_count else "Không có",
            "cta": "Xem",
            "url": target_tools_url,
        },
        {
            "label": "Tồn hiện có",
            "value": total_stock_quantity,
            "status": f"{total_items} mã",
            "cta": "Báo cáo",
            "url": stock_report_url,
        },
    ]

    utility_cards = []
    if low_stock_count:
        utility_cards.append(
            {
                "title": "Cảnh báo tồn kho",
                "count": low_stock_count,
                "status": "Cảnh báo",
                "cta": "Xem tồn",
                "url": stock_report_url,
                "items": [{"title": item.ten_vat_tu, "meta": f"Còn {item.so_luong_ton}/{item.muc_canh_bao}"} for item in low_stock[:3]],
            }
        )
    if payroll_deduction_count:
        utility_cards.append(
            {
                "title": "Khấu trừ chờ đối soát",
                "count": payroll_deduction_count,
                "status": f"{_format_money(payroll_deduction_total):,} đ".replace(",", "."),
                "cta": "Mở phiếu",
                "url": issues_url,
                "items": [
                    {
                        "title": issue.ma_phieu,
                        "meta": issue.nhan_vien_nhan.ho_ten if issue.nhan_vien_nhan else "Chưa rõ nhân viên",
                    }
                    for issue in payroll_deduction_pending[:3]
                ],
            }
        )
    if stale_target_tools_count:
        utility_cards.append(
            {
                "title": "CCHT cần kiểm tra",
                "count": stale_target_tools_count,
                "status": "Quá 30 ngày",
                "cta": "Xem CCHT",
                "url": target_tools_url,
                "items": [{"title": item.muc_tieu.ten_muc_tieu, "meta": item.vat_tu.ten_vat_tu} for item in stale_target_tools_qs[:3]],
            }
        )
    if recent_ledger:
        utility_cards.append(
            {
                "title": "Ledger gần đây",
                "count": len(recent_ledger[:3]),
                "status": "Đã ghi sổ",
                "cta": "Mở ledger",
                "url": ledger_url,
                "items": [
                    {
                        "title": entry.vat_tu.ten_vat_tu,
                        "meta": f"{entry.created_at:%d/%m %H:%M} · {entry.stock_before} → {entry.stock_after}",
                    }
                    for entry in recent_ledger[:3]
                ],
            }
        )

    context = {
        "title": "Kho & Vật tư",
        "period": period,
        "period_label": period_label,
        "date_from": date_from,
        "tong_loai": total_items,
        "tong_gia_tri": float(total_inventory_value),
        "total_stock_quantity": total_stock_quantity,
        "sap_het_hang": low_stock,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "phieu_xuat_trong_thang": issues_period.count(),
        "incoming_qty": incoming_qty,
        "outgoing_qty": outgoing_qty,
        "receipt_draft_count": receipt_draft_count,
        "issue_draft_count": issue_draft_count,
        "voided_docs_count": voided_docs_count,
        "payroll_deduction_pending": payroll_deduction_pending[:6],
        "payroll_deduction_count": payroll_deduction_count,
        "payroll_deduction_total": payroll_deduction_total,
        "target_tools_count": target_tools_count,
        "target_tools_quantity": target_tools_quantity,
        "stale_target_tools_count": stale_target_tools_count,
        "lich_su_xuat": recent_issues,
        "recent_documents": reference_documents,
        "recent_ledger": recent_ledger,
        "category_stock": category_stock,
        "action_items": action_items,
        "metric_cards": metric_cards,
        "utility_cards": utility_cards,
        "urls": {
            "add_receipt": add_receipt_url,
            "add_issue": add_issue_url,
            "receipts": receipts_url,
            "issues": issues_url,
            "stock_admin": stock_admin_url,
            "stock_report": stock_report_url,
            "target_tools": target_tools_url,
            "target_tools_admin": target_tools_admin_url,
            "ledger": ledger_url,
        },
    }
    return render(request, "inventory/dashboard_kho.html", context)


@login_required
def cong_cu_muc_tieu(request):
    """Theo dõi CCHT/vật tư đang nằm tại mục tiêu bảo vệ."""
    query = (request.GET.get("q") or "").strip()
    loai_id = (request.GET.get("loai") or "").strip()
    muc_tieu_query = (request.GET.get("muc_tieu") or "").strip()
    status = (request.GET.get("status") or "all").strip()

    ds_loai = list(LoaiVatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).order_by("ten_loai"))
    today = timezone.localdate()
    stale_before = today - timedelta(days=30)

    tools_qs = (
        CongCuTaiMucTieu.objects.select_related("muc_tieu", "vat_tu", "vat_tu__loai_vat_tu")
        .order_by("muc_tieu__ten_muc_tieu", "vat_tu__ten_vat_tu")
    )
    if query:
        tools_qs = tools_qs.filter(
            Q(vat_tu__ten_vat_tu__icontains=query)
            | Q(muc_tieu__ten_muc_tieu__icontains=query)
            | Q(muc_tieu__dia_chi__icontains=query)
        )
    if muc_tieu_query:
        tools_qs = tools_qs.filter(muc_tieu__ten_muc_tieu__icontains=muc_tieu_query)
    if loai_id:
        tools_qs = tools_qs.filter(vat_tu__loai_vat_tu_id=loai_id)
    if status == "stale":
        tools_qs = tools_qs.filter(ngay_cap_gan_nhat__lte=stale_before)
    elif status == "empty_stock":
        tools_qs = tools_qs.filter(vat_tu__so_luong_ton__lte=0)

    all_tools_qs = CongCuTaiMucTieu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_related("muc_tieu", "vat_tu")
    total_quantity = tools_qs.aggregate(total=Coalesce(Sum("so_luong_dang_giu"), INT_ZERO, output_field=IntegerField()))["total"] or 0
    total_sites = tools_qs.values("muc_tieu_id").distinct().count()
    stale_count = all_tools_qs.filter(ngay_cap_gan_nhat__lte=stale_before).count()
    empty_stock_count = all_tools_qs.filter(vat_tu__so_luong_ton__lte=0).count()

    site_rows = list(
        tools_qs.values("muc_tieu_id", "muc_tieu__ten_muc_tieu")
        .annotate(
            tool_lines=Count("id"),
            total_qty=Coalesce(Sum("so_luong_dang_giu"), INT_ZERO, output_field=IntegerField()),
            last_update=Max("ngay_cap_gan_nhat"),
        )
        .order_by("-total_qty", "muc_tieu__ten_muc_tieu")[:8]
    )
    max_site_qty = max([row["total_qty"] for row in site_rows] or [1]) or 1
    for row in site_rows:
        row["percent"] = round((row["total_qty"] / max_site_qty) * 100) if max_site_qty else 0
        row["label"] = row["muc_tieu__ten_muc_tieu"] or "Chưa rõ mục tiêu"
        row["stale"] = bool(row["last_update"] and row["last_update"] <= stale_before)

    category_rows = list(
        tools_qs.values("vat_tu__loai_vat_tu__ten_loai")
        .annotate(total_qty=Coalesce(Sum("so_luong_dang_giu"), INT_ZERO, output_field=IntegerField()), tool_lines=Count("id"))
        .order_by("-total_qty")[:6]
    )
    max_category_qty = max([row["total_qty"] for row in category_rows] or [1]) or 1
    for row in category_rows:
        row["label"] = row["vat_tu__loai_vat_tu__ten_loai"] or "Chưa phân loại"
        row["percent"] = round((row["total_qty"] / max_category_qty) * 100) if max_category_qty else 0

    paginator = Paginator(tools_qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    for item in page_obj.object_list:
        item.is_stale = bool(item.ngay_cap_gan_nhat and item.ngay_cap_gan_nhat <= stale_before)
        item.stock_empty = (item.vat_tu.so_luong_ton or 0) <= 0
        item.admin_url = _safe_reverse("admin:inventory_congcutaimuctieu_change", args=[item.pk])

    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "title": "CCHT tại mục tiêu",
        "page_obj": page_obj,
        "cong_cu_list": page_obj.object_list,
        "ds_loai": ds_loai,
        "query": query,
        "muc_tieu_query": muc_tieu_query,
        "selected_loai": int(loai_id) if loai_id.isdigit() else None,
        "status": status,
        "total_quantity": total_quantity,
        "total_sites": total_sites,
        "stale_count": stale_count,
        "empty_stock_count": empty_stock_count,
        "site_rows": site_rows,
        "category_rows": category_rows,
        "current_querystring": query_params.urlencode(),
        "urls": {
            "dashboard": _safe_reverse("inventory:dashboard"),
            "stock_report": _safe_reverse("inventory:bao_cao_ton"),
            "add_issue": _safe_reverse("admin:inventory_phieuxuat_add"),
            "add_target_tool": _safe_reverse("admin:inventory_congcutaimuctieu_add"),
            "target_tool_admin": _safe_reverse("admin:inventory_congcutaimuctieu_changelist"),
        },
    }
    return render(request, "inventory/cong_cu_muc_tieu.html", context)


@login_required
def bao_cao_ton_kho(request):
    """Báo cáo tồn kho thực chiến cho bộ phận kho."""
    query = (request.GET.get("q") or "").strip()
    loai_id = (request.GET.get("loai") or "").strip()
    status = (request.GET.get("status") or "all").strip()
    sort = (request.GET.get("sort") or "warning").strip()

    org_id = getattr(settings, "SCMD_ORGANIZATION_ID", "default")
    cache_key_loai = build_category_cache_key(org_id, request.user.id)
    ds_loai = cache.get(cache_key_loai)
    if not ds_loai:
        ds_loai = list(LoaiVatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).order_by("ten_loai"))
        cache.set(cache_key_loai, ds_loai, 3600)

    latest_purchase_price = (
        ChiTietPhieuNhap.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(vat_tu=OuterRef("pk"))
        .order_by("-phieu_nhap__ngay_nhap", "-id")
        .values("don_gia")[:1]
    )

    vat_tu_list = VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_related("loai_vat_tu").annotate(
        gia_moi_nhat=Coalesce(
            Subquery(latest_purchase_price),
            F("gia_nhap"),
            output_field=DecimalField(max_digits=12, decimal_places=0),
        )
    )

    if query:
        vat_tu_list = vat_tu_list.filter(Q(ten_vat_tu__icontains=query) | Q(don_vi_tinh__icontains=query))
    if loai_id:
        vat_tu_list = vat_tu_list.filter(loai_vat_tu_id=loai_id)
    if status == "out":
        vat_tu_list = vat_tu_list.filter(so_luong_ton__lte=0)
    elif status == "low":
        vat_tu_list = vat_tu_list.filter(so_luong_ton__gt=0, so_luong_ton__lte=F("muc_canh_bao"))
    elif status == "safe":
        vat_tu_list = vat_tu_list.filter(so_luong_ton__gt=F("muc_canh_bao"))

    if sort == "stock_desc":
        vat_tu_list = vat_tu_list.order_by("-so_luong_ton", "ten_vat_tu")
    elif sort == "name":
        vat_tu_list = vat_tu_list.order_by("ten_vat_tu")
    else:
        sort = "warning"
        vat_tu_list = vat_tu_list.order_by("so_luong_ton", "ten_vat_tu")

    total_items = VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).count()
    total_stock_quantity = (
        VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .aggregate(total=Coalesce(Sum("so_luong_ton"), INT_ZERO, output_field=IntegerField()))["total"]
        or 0
    )
    out_of_stock_count = VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(so_luong_ton__lte=0).count()
    low_stock_count = (
        VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .filter(so_luong_ton__gt=0, so_luong_ton__lte=F("muc_canh_bao"))
        .count()
    )
    safe_stock_count = max(total_items - out_of_stock_count - low_stock_count, 0)

    total_inventory_value = Decimal("0")
    value_items = VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).select_related("loai_vat_tu").annotate(
        gia_moi_nhat=Coalesce(
            Subquery(latest_purchase_price),
            F("gia_nhap"),
            output_field=DecimalField(max_digits=12, decimal_places=0),
        )
    )
    for item in value_items.iterator(chunk_size=300):
        total_inventory_value += Decimal(item.so_luong_ton or 0) * Decimal(item.gia_moi_nhat or 0)

    category_rows = list(
        VatTu.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .values("loai_vat_tu__ten_loai")
        .annotate(total_stock=Coalesce(Sum("so_luong_ton"), INT_ZERO, output_field=IntegerField()), item_count=Count("id"))
        .order_by("-total_stock")[:8]
    )
    max_category_stock = max([row["total_stock"] for row in category_rows] or [1]) or 1
    for row in category_rows:
        row["label"] = row["loai_vat_tu__ten_loai"] or "Chưa phân loại"
        row["percent"] = round((row["total_stock"] / max_category_stock) * 100) if max_category_stock else 0

    paginator = Paginator(vat_tu_list, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    for item in page_obj.object_list:
        stock = item.so_luong_ton or 0
        warning = item.muc_canh_bao or 0
        item.gia_tri_ton = Decimal(stock) * Decimal(item.gia_moi_nhat or 0)
        item.stock_admin_url = _safe_reverse("admin:inventory_vattu_change", args=[item.pk])
        item.status_key = "safe"
        item.status_label = "An toàn"
        item.status_note = f"Trên mức cảnh báo {warning}"
        if stock <= 0:
            item.status_key = "out"
            item.status_label = "Hết hàng"
            item.status_note = "Cần lập kế hoạch nhập/bổ sung ngay"
        elif stock <= warning:
            item.status_key = "low"
            item.status_label = "Dưới cảnh báo"
            item.status_note = f"Còn {stock}, ngưỡng tối thiểu {warning}"

    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "title": "Báo cáo tồn kho",
        "page_obj": page_obj,
        "vat_tu_list": page_obj.object_list,
        "ds_loai": ds_loai,
        "query": query,
        "selected_loai": int(loai_id) if loai_id.isdigit() else None,
        "status": status,
        "sort": sort,
        "current_querystring": query_params.urlencode(),
        "total_items": total_items,
        "total_stock_quantity": total_stock_quantity,
        "total_inventory_value": total_inventory_value,
        "out_of_stock_count": out_of_stock_count,
        "low_stock_count": low_stock_count,
        "safe_stock_count": safe_stock_count,
        "category_rows": category_rows,
        "urls": {
            "dashboard": _safe_reverse("inventory:dashboard"),
            "target_tools": _safe_reverse("inventory:cong_cu_muc_tieu"),
            "add_receipt": _safe_reverse("admin:inventory_phieunhap_add"),
            "add_issue": _safe_reverse("admin:inventory_phieuxuat_add"),
            "stock_admin": _safe_reverse("admin:inventory_vattu_changelist"),
        },
    }
    return render(request, "inventory/bao_cao_ton_kho.html", context)


@login_required
def chi_tiet_phieu_nhap(request, pk):
    phieu = get_object_or_404(
        PhieuNhap.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).prefetch_related("chi_tiet__vat_tu"),
        pk=pk,
    )
    return render(request, "inventory/print/phieu_nhap_detail.html", {"phieu": phieu})


@login_required
def chi_tiet_phieu_xuat(request, pk):
    phieu = get_object_or_404(
        PhieuXuat.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
        .select_related("nhan_vien_nhan", "muc_tieu_nhan")
        .prefetch_related("chi_tiet__vat_tu"),
        pk=pk,
    )
    return render(request, "inventory/print/phieu_xuat_detail.html", {"phieu": phieu})
