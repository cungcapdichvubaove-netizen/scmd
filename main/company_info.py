# -*- coding: utf-8 -*-
"""Company profile helpers used by print/export templates.

The configured company profile is the single source of truth for legal/header
information rendered into payroll, employee profile, contracts and inventory
forms.  Helpers in this module are deliberately defensive so templates and
export services keep working during first deploy before the admin has filled in
company data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db import OperationalError, ProgrammingError


DEFAULT_COMPANY_NAME = "CÔNG TY DỊCH VỤ BẢO VỆ SCMD"
DEFAULT_COMPANY_ADDRESS = "Chưa cấu hình địa chỉ công ty"
DEFAULT_COMPANY_PHONE = "Chưa cấu hình số điện thoại"
DEFAULT_COMPANY_EMAIL = ""
DEFAULT_COMPANY_WEBSITE = ""
COMPANY_INFO_CACHE_TIMEOUT = 300


def _company_info_cache_key(tenant_id: Any | None = None) -> str:
    org_id = tenant_id or getattr(settings, "SCMD_ORGANIZATION_ID", "default")
    return f"company_info:{org_id}"


def invalidate_company_info_cache(tenant_id: Any | None = None) -> None:
    """Invalidate cached company profile after admin/import updates."""

    cache.delete(_company_info_cache_key(tenant_id))



@dataclass(frozen=True)
class CompanyInfoFallback:
    """Safe null-object for company information before database setup."""

    ten_cong_ty: str = DEFAULT_COMPANY_NAME
    ten_phap_ly: str = ""
    ma_so_thue: str = ""
    dia_chi: str = DEFAULT_COMPANY_ADDRESS
    dien_thoai: str = DEFAULT_COMPANY_PHONE
    hotline: str = ""
    email: str = DEFAULT_COMPANY_EMAIL
    website: str = DEFAULT_COMPANY_WEBSITE
    nguoi_dai_dien: str = ""
    chuc_vu_nguoi_dai_dien: str = ""
    so_tai_khoan: str = ""
    ngan_hang: str = ""
    logo: Any = None

    @property
    def display_name(self) -> str:
        return self.ten_phap_ly or self.ten_cong_ty

    @property
    def contact_phone(self) -> str:
        return self.hotline or self.dien_thoai

    def as_report_context(self) -> dict[str, Any]:
        return {
            "name": self.display_name,
            "legal_name": self.ten_phap_ly or self.ten_cong_ty,
            "trade_name": self.ten_cong_ty,
            "tax_code": self.ma_so_thue,
            "address": self.dia_chi,
            "phone": self.dien_thoai,
            "hotline": self.contact_phone,
            "email": self.email,
            "website": self.website,
            "representative": self.nguoi_dai_dien,
            "representative_title": self.chuc_vu_nguoi_dai_dien,
            "bank_account": self.so_tai_khoan,
            "bank_name": self.ngan_hang,
            "logo": self.logo,
            "logo_url": getattr(self.logo, "url", "") if self.logo else "",
            "logo_path": getattr(self.logo, "path", "") if self.logo else "",
        }


def get_company_info():
    """Return the configured singleton company profile or a safe fallback.

    The profile is cached briefly because this context is needed by many
    templates, while company information changes rarely and is invalidated on
    CompanyInfo.save()/delete().
    """

    tenant_id = getattr(settings, "SCMD_ORGANIZATION_ID", None)
    cache_key = _company_info_cache_key(tenant_id)
    cached_profile = cache.get(cache_key)
    if cached_profile is not None:
        return cached_profile

    try:
        from main.models import CompanyInfo

        if tenant_id and hasattr(CompanyInfo.objects, "for_tenant"):
            profile = CompanyInfo.objects.for_tenant(tenant_id).get()
        else:
            profile = CompanyInfo.objects.get()
        cache.set(cache_key, profile, COMPANY_INFO_CACHE_TIMEOUT)
        return profile
    except (ObjectDoesNotExist, OperationalError, ProgrammingError, ImproperlyConfigured):
        fallback = CompanyInfoFallback()
        cache.set(cache_key, fallback, COMPANY_INFO_CACHE_TIMEOUT)
        return fallback


def build_company_report_context(profile) -> dict[str, Any]:
    """Return normalized dict shape for report/export code from an object already loaded."""

    if hasattr(profile, "as_report_context"):
        return profile.as_report_context()
    return CompanyInfoFallback().as_report_context()


def get_company_report_context() -> dict[str, Any]:
    """Return normalized dict shape for report/export code."""

    return build_company_report_context(get_company_info())
