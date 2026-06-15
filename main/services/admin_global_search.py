# -*- coding: utf-8 -*-
"""Unified admin search service for the SCMD Pro operations console.

This module intentionally does not use Jazzmin's ``search_model`` setting.
Jazzmin renders one compact topbar search widget per configured model, which
caused the repeated search/icon regression in browser QA.  SCMD Pro needs one
quiet command-style search that fans out server-side to the core operational
entities and then returns scoped result groups.

Important security rule:
Global search must never widen object visibility compared with Django Admin
changelists.  The default queryset is therefore the registered ModelAdmin's
``get_queryset(request)``, never the model default manager.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Callable, Iterable

from django.apps import apps
from django.contrib import admin
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse
from django.utils.text import Truncator


logger = logging.getLogger(__name__)

QuerysetFactory = Callable[[HttpRequest, type], QuerySet]


@dataclass(frozen=True)
class AdminSearchTarget:
    """Configuration for one searchable admin entity."""

    app_label: str
    model_name: str
    label: str
    fields: tuple[str, ...]
    title_field: str | None = None
    subtitle_fields: tuple[str, ...] = ()
    queryset_factory: QuerysetFactory | None = None

    @property
    def model_path(self) -> str:
        return f"{self.app_label}.{self.model_name}"

    @property
    def permission_codename(self) -> str:
        return f"{self.app_label}.view_{self.model_name.lower()}"

    @property
    def admin_change_url_name(self) -> str:
        return f"admin:{self.app_label}_{self.model_name.lower()}_change"



def _staff_queryset(request: HttpRequest, model: type) -> QuerySet:
    """Return staff records through the existing StaffVisibilityPolicy.

    This is intentionally explicit because employee data is highly sensitive.
    For other targets the default path is the registered ModelAdmin queryset,
    which preserves object-level policies such as SiteVisibilityPolicy and
    IncidentVisibilityPolicy from the changelist implementation.
    """

    from users.access_policies import StaffVisibilityPolicy

    return StaffVisibilityPolicy.visible_staff(request.user)


ADMIN_GLOBAL_SEARCH_TARGETS: tuple[AdminSearchTarget, ...] = (
    AdminSearchTarget(
        app_label="users",
        model_name="NhanVien",
        label="Nhân viên",
        fields=("ho_ten", "ma_nhan_vien", "sdt_chinh", "email"),
        title_field="ho_ten",
        subtitle_fields=("ma_nhan_vien", "sdt_chinh", "email"),
        queryset_factory=_staff_queryset,
    ),
    AdminSearchTarget(
        app_label="clients",
        model_name="MucTieu",
        label="Mục tiêu",
        fields=("ten_muc_tieu", "dia_chi"),
        title_field="ten_muc_tieu",
        subtitle_fields=("dia_chi",),
    ),
    AdminSearchTarget(
        app_label="clients",
        model_name="HopDong",
        label="Hợp đồng",
        fields=("so_hop_dong", "trang_thai"),
        title_field="so_hop_dong",
        subtitle_fields=("trang_thai",),
    ),
    AdminSearchTarget(
        app_label="clients",
        model_name="KhachHangTiemNang",
        label="Khách hàng",
        fields=("ten_cong_ty", "nguoi_lien_he", "sdt", "email"),
        title_field="ten_cong_ty",
        subtitle_fields=("nguoi_lien_he", "sdt", "email"),
    ),
    AdminSearchTarget(
        app_label="operations",
        model_name="BaoCaoSuCo",
        label="Sự cố",
        fields=("ma_su_co", "tieu_de", "mo_ta_chi_tiet", "trang_thai", "muc_do"),
        title_field="tieu_de",
        subtitle_fields=("ma_su_co", "trang_thai", "muc_do"),
    ),
    AdminSearchTarget(
        app_label="inventory",
        model_name="VatTu",
        label="Vật tư",
        fields=("ten_vat_tu", "don_vi_tinh"),
        title_field="ten_vat_tu",
        subtitle_fields=("don_vi_tinh", "so_luong_ton"),
    ),
)


def _safe_model(target: AdminSearchTarget) -> type | None:
    try:
        return apps.get_model(target.app_label, target.model_name)
    except LookupError:
        return None


def _model_admin_for(model: type):
    return admin.site._registry.get(model)


def _searchable_fields(model: type, fields: Iterable[str]) -> tuple[str, ...]:
    concrete_names = {field.name for field in model._meta.get_fields() if hasattr(field, "attname")}
    return tuple(field for field in fields if field in concrete_names)


def _admin_can_view(request: HttpRequest, model: type, target: AdminSearchTarget) -> bool:
    model_admin = _model_admin_for(model)
    if model_admin is not None:
        return model_admin.has_view_permission(request)
    return request.user.has_perm(target.permission_codename)


def _scoped_admin_queryset(request: HttpRequest, model: type, target: AdminSearchTarget) -> QuerySet:
    """Return the exact object scope allowed for an admin search target.

    The registered ModelAdmin queryset is the source of truth for global search
    because it already carries object-level visibility policies, select_related,
    annotations and tenant filters used by the real changelist.  Falling back to
    the default manager would bypass those constraints and is not allowed.
    """

    if target.queryset_factory is not None:
        return target.queryset_factory(request, model)

    model_admin = _model_admin_for(model)
    if model_admin is None:
        raise LookupError(f"{target.model_path} is not registered in Django Admin")
    return model_admin.get_queryset(request)


def _build_query(fields: Iterable[str], query: str) -> Q:
    criteria = Q()
    for field in fields:
        criteria |= Q(**{f"{field}__icontains": query})
    return criteria


def _title_for(obj: object, target: AdminSearchTarget) -> str:
    if target.title_field and hasattr(obj, target.title_field):
        value = getattr(obj, target.title_field)
        if value not in (None, ""):
            return str(value)
    return str(obj)


def _subtitle_for(obj: object, target: AdminSearchTarget) -> str:
    parts: list[str] = []
    for field in target.subtitle_fields:
        if not hasattr(obj, field):
            continue
        value = getattr(obj, field)
        if value not in (None, ""):
            parts.append(str(value))
    return " · ".join(parts)


def _change_url_for(obj: object, target: AdminSearchTarget) -> str:
    try:
        return reverse(target.admin_change_url_name, args=[obj.pk])
    except NoReverseMatch:
        return "#"


def _can_see_search_source_failures(request: HttpRequest) -> bool:
    user = getattr(request, "user", None)
    return bool(user and (user.is_superuser or user.has_perm("main.view_auditlog")))


def run_admin_global_search(
    request: HttpRequest,
    query: str,
    *,
    per_target_limit: int = 6,
) -> dict[str, object]:
    """Search core operational entities and return render-ready groups."""

    query = (query or "").strip()
    groups: list[dict[str, object]] = []
    failed_source_labels: list[str] = []
    total_count = 0
    show_failed_sources = _can_see_search_source_failures(request)

    if len(query) < 2:
        return {
            "query": query,
            "groups": groups,
            "total_count": 0,
            "too_short": bool(query),
            "targets": ADMIN_GLOBAL_SEARCH_TARGETS,
            "failed_sources": [],
            "has_failed_sources": False,
            "show_failed_sources": show_failed_sources,
        }

    for target in ADMIN_GLOBAL_SEARCH_TARGETS:
        model = _safe_model(target)
        if model is None or not _admin_can_view(request, model, target):
            continue

        fields = _searchable_fields(model, target.fields)
        if not fields:
            continue

        try:
            queryset = _scoped_admin_queryset(request, model, target)
            matches = list(queryset.filter(_build_query(fields, query)).distinct()[: per_target_limit + 1])
        except Exception as exc:
            logger.warning(
                "Admin global search source failed: %s",
                target.model_path,
                exc_info=exc,
                extra={"target": target.model_path, "query": query},
            )
            failed_source_labels.append(target.label)
            continue

        visible_matches = matches[:per_target_limit]
        if not visible_matches:
            continue

        items = [
            {
                "title": Truncator(_title_for(obj, target)).chars(84),
                "subtitle": Truncator(_subtitle_for(obj, target)).chars(128),
                "url": _change_url_for(obj, target),
                "object_id": obj.pk,
            }
            for obj in visible_matches
        ]
        group_count = len(visible_matches)
        total_count += group_count
        groups.append(
            {
                "label": target.label,
                "model_path": target.model_path,
                "items": items,
                "shown_count": group_count,
                "has_more": len(matches) > per_target_limit,
            }
        )

    return {
        "query": query,
        "groups": groups,
        "total_count": total_count,
        "too_short": False,
        "targets": ADMIN_GLOBAL_SEARCH_TARGETS,
        "failed_sources": failed_source_labels if show_failed_sources else [],
        "has_failed_sources": bool(failed_source_labels),
        "show_failed_sources": show_failed_sources,
    }
