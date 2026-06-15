# -*- coding: utf-8 -*-
"""
Access policies for the reports module.
"""

from django.core.exceptions import PermissionDenied
from clients.access_policies import SiteVisibilityPolicy, _has_business_role
from main.dashboard_router import DashboardRouter


class ReportAccessPolicy:
    """SSOT for access control of internal reports."""

    ATTENDANCE_REPORT_ROLES = (
        "ban_giam_doc",
        "ke_toan",
        "quan_ly_vung",
        "doi_truong",
        "nhan_su",
    )
    INCIDENT_REPORT_ROLES = (
        "ban_giam_doc",
        "quan_ly_vung",
        "doi_truong",
        "thanh_tra",
        "nghiep_vu",
    )
    FINANCE_REPORT_ROLES = ("ban_giam_doc", "ke_toan")
    EXPORT_ALLOWED_ROLES = (
        "ban_giam_doc",
        "ke_toan",
        "quan_ly_vung",
        "thanh_tra",
    )

    @staticmethod
    def _has_any_role(user, roles):
        # Use the same business-role resolver as clients/site visibility.
        # rolepermissions.has_role alone is not sufficient for legacy group/role
        # aliases used by dashboard and access-scope fixtures.
        return _has_business_role(user, tuple(roles))

    @staticmethod
    def _has_report_workspace_access(user):
        return DashboardRouter.user_can_access(user, "reports:report_dashboard")

    @staticmethod
    def _has_scoped_operational_report_scope(user):
        if not getattr(user, "is_authenticated", False):
            return False
        try:
            return SiteVisibilityPolicy.managed_sites(user).exists()
        except Exception:
            return False

    @classmethod
    def _has_scoped_report_access(cls, user, roles):
        """Return True for users with a real managed site scope.

        Dashboard/workspace access is not the only valid signal for scoped
        operational reports: legacy object-scope fields such as
        ``MucTieu.quan_ly_vung`` and ``MucTieu.quan_ly_muc_tieu`` are accepted by
        ``SiteVisibilityPolicy``. This helper therefore allows report entry only
        when the user has a business report role *or* a concrete managed site
        scope. The export/query layer still filters rows through
        AttendanceVisibilityPolicy/IncidentVisibilityPolicy, so this does not
        widen data visibility outside the managed sites.
        """
        if not getattr(user, "is_authenticated", False):
            return False
        if cls._has_any_role(user, roles):
            return True
        if cls._has_report_workspace_access(user) and cls._has_scoped_operational_report_scope(user):
            return True
        # Direct target/region manager fallback: object scope itself is a valid
        # business signal, but only if it resolves to at least one managed site.
        return cls._has_scoped_operational_report_scope(user)

    @classmethod
    def can_view_attendance_reports(cls, user):
        if getattr(user, "is_superuser", False):
            return True
        return cls._has_scoped_report_access(user, cls.ATTENDANCE_REPORT_ROLES)

    @classmethod
    def can_view_incident_reports(cls, user):
        if getattr(user, "is_superuser", False):
            return True
        return cls._has_scoped_report_access(user, cls.INCIDENT_REPORT_ROLES)

    @classmethod
    def can_view_finance_reports(cls, user):
        return bool(getattr(user, "is_superuser", False) or cls._has_any_role(user, cls.FINANCE_REPORT_ROLES))

    @classmethod
    def can_export_sensitive_reports(cls, user):
        if getattr(user, "is_superuser", False):
            return True
        if cls._has_any_role(user, cls.EXPORT_ALLOWED_ROLES):
            return True
        # Scoped operations roles may export only the already object-scoped report
        # querysets. This preserves export functionality without widening data
        # access because AttendanceVisibilityPolicy/IncidentVisibilityPolicy still
        # filter rows by the user's managed/assigned sites.
        return cls._has_scoped_report_access(user, cls.EXPORT_ALLOWED_ROLES)

    @classmethod
    def enforce_attendance_report_access(cls, user):
        if cls.can_view_attendance_reports(user):
            return
        raise PermissionDenied("Bạn không có quyền truy cập báo cáo chấm công.")

    @classmethod
    def enforce_incident_report_access(cls, user):
        if cls.can_view_incident_reports(user):
            return
        raise PermissionDenied("Bạn không có quyền truy cập báo cáo sự cố.")

    @classmethod
    def enforce_export_access(cls, user):
        if cls.can_export_sensitive_reports(user):
            return
        raise PermissionDenied("Bạn không có quyền xuất dữ liệu nhạy cảm.")

    @classmethod
    def get_dashboard_permissions(cls, user):
        return {
            "attendance": cls.can_view_attendance_reports(user),
            "incident": cls.can_view_incident_reports(user),
            "finance": cls.can_view_finance_reports(user),
            "export": cls.can_export_sensitive_reports(user),
        }
