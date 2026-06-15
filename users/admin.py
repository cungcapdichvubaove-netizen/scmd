# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro
=======
Security Command (SCMD) System
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: users/admin.py
Author: Mr. Anh (CTO) & AI Assistant
Created Date: 2025-12-05
Updated Date: 2026-04-28
Description: Giao diện Admin Users (v1.1.0 - Enterprise HRM Optimized).
             FIXED: Khôi phục đầy đủ tính năng In Lý Lịch & Sửa lỗi IntegrityError.
             ENHANCEMENT: Tối ưu hóa hiệu suất truy vấn và chuyên nghiệp hóa UI.
"""

import logging
import tablib
from django.contrib import admin, messages
<<<<<<< HEAD
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin, UserAdmin as BaseUserAdmin
from django import forms
from django.db import models, transaction
from django.forms import TextInput, Select
from django.utils.html import format_html, format_html_join 
from django.http import HttpResponse
from django.urls import path, reverse
=======
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django import forms
from django.db import models
from django.forms import TextInput, Select
from django.utils.html import format_html 
from django.http import HttpResponse
from django.urls import path
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
<<<<<<< HEAD
from core.workflow_transition_policy import WorkflowTransitionPolicy

from rolepermissions.checkers import has_role
from main.audit_utils import record_export_audit, record_admin_audit_action
from main.models import AuditLog
from main.services.operations_ux import AdminOperationsUXProvider
from users.access_policies import StaffVisibilityPolicy
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

# --- IMPORT/EXPORT LIBRARIES ---
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
<<<<<<< HEAD
from import_export.widgets import ForeignKeyWidget, DateWidget

# IMPORT MODELS
from .models import (
    NhanVien, PhongBan, ChucDanh, LichSuCongTac, HocVan, BangCapChungChi,
    CauHinhMaNhanVien, HopDongLaoDong, PhuLucHopDongLaoDong,
    DonNghiPhep, HoSoBaoHiem, OffboardingChecklist, QuyetDinhNghiViec,
=======
from import_export.widgets import ForeignKeyWidget

# IMPORT MODELS
from .models import (
    NhanVien, PhongBan, ChucDanh, LichSuCongTac, HocVan, BangCapChungChi, 
    CauHinhMaNhanVien
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
)

# Logger cho hệ thống SCMD
logger = logging.getLogger(__name__)

<<<<<<< HEAD

def _bounded_count(queryset, limit=999):
    """Return capped count sentinel; ``limit + 1`` means display as ``limit+``."""
    if queryset is None:
        return 0
    try:
        sample = list(queryset.values_list("pk", flat=True)[: limit + 1])
        return len(sample)
    except Exception:
        logger.warning("Không tính được bounded count cho admin users.", exc_info=True)
        return 0


def _bounded_display(value, limit=999):
    """Display bounded count honestly instead of silently showing the cap as exact."""
    try:
        value = int(value or 0)
    except (TypeError, ValueError):
        return value
    return f"{limit}+" if value > limit else value



class SCMDVietnameseDateWidget(DateWidget):
    """Import/export ngày theo chuẩn Việt Nam nhưng vẫn nhận ISO để tương thích file cũ."""

    def __init__(self):
        super().__init__(format="%d/%m/%Y")

    def clean(self, value, row=None, **kwargs):
        if value in (None, ""):
            return None
        last_error = None
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                self.format = fmt
                return super().clean(value, row=row, **kwargs)
            except (ValueError, TypeError) as exc:
                last_error = exc
        self.format = "%d/%m/%Y"
        raise ValueError("Ngày không hợp lệ. Vui lòng nhập theo định dạng dd/mm/yyyy, ví dụ 06/06/2026.") from last_error

    def render(self, value, obj=None, **kwargs):
        self.format = "%d/%m/%Y"
        return super().render(value, obj=obj, **kwargs)

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
# Import config quyền
try: 
    from .permissions_config import PERMISSION_GROUPS
except ImportError: 
    PERMISSION_GROUPS = {}


<<<<<<< HEAD
SYSTEM_PERMISSION_SECTION = (
    "6. Hệ thống",
    {
        "description": _("Quản trị người dùng, nhật ký hệ thống và tự động hóa tác vụ."),
        "models": [
            ("auth", "user", _("Người dùng")),
            ("auth", "group", _("Nhóm quyền")),
            ("main", "auditlog", _("Nhật ký hệ thống")),
            ("main", "workerheartbeat", _("Giám sát worker")),
            ("django_celery_beat", "periodictask", _("Lịch trình tự động")),
            ("django_celery_results", "taskresult", _("Kết quả tác vụ")),
        ],
    },
)


=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
# --- HELPER: KIỂM TRA QUYỀN TRUY CẬP ---
def is_hr_or_director(user):
    """Kiểm tra người dùng có thuộc nhóm nhân sự hoặc ban giám đốc không."""
    if user.is_superuser: 
        return True
<<<<<<< HEAD
    # SCMD Pro: Enforce role-based access for administrative actions (Rule 8).
    return bool(
        user.is_authenticated and 
        has_role(user, ["ban_giam_doc", "nhan_su", "ke_toan"])
    )




# ==============================================================================
# 0. TECHNICAL USER ADMIN - AUTH.USER
# ==============================================================================
class HasEmployeeProfileFilter(admin.SimpleListFilter):
    title = _('Liên kết hồ sơ nhân sự')
    parameter_name = 'employee_profile'

    def lookups(self, request, model_admin):
        return (
            ('linked', _('Đã liên kết nhân viên')),
            ('missing', _('Chưa liên kết nhân viên')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'linked':
            return queryset.filter(nhan_vien__isnull=False)
        if self.value() == 'missing':
            return queryset.filter(nhan_vien__isnull=True)
        return queryset


class EmployeeDepartmentFilter(admin.SimpleListFilter):
    title = _('Phòng ban nhân sự')
    parameter_name = 'employee_department'

    def lookups(self, request, model_admin):
        return [
            (str(item.pk), item.ten_phong_ban)
            for item in PhongBan.objects.order_by('ten_phong_ban')[:80]
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(nhan_vien__phong_ban_id=self.value())
        return queryset


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class TechnicalUserAdmin(BaseUserAdmin):
    """Quản trị tài khoản kỹ thuật theo hướng dễ rà soát và thao tác an toàn."""

    change_list_template = 'admin/auth/user/change_list.html'
    list_display = (
        'account_identity',
        'employee_profile',
        'group_summary',
        'security_flags',
        'last_login_short',
        'date_joined_short',
    )
    list_display_links = ('account_identity',)
    list_filter = (
        'is_active',
        'is_staff',
        'is_superuser',
        HasEmployeeProfileFilter,
        EmployeeDepartmentFilter,
        'groups',
        ('last_login', admin.DateFieldListFilter),
        ('date_joined', admin.DateFieldListFilter),
    )
    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
        'nhan_vien__ma_nhan_vien',
        'nhan_vien__ho_ten',
        'nhan_vien__sdt_chinh',
    )
    list_select_related = ('nhan_vien', 'nhan_vien__phong_ban', 'nhan_vien__chuc_danh')
    filter_horizontal = ('groups', 'user_permissions')
    actions = ('activate_accounts', 'deactivate_accounts', 'grant_staff_access', 'revoke_staff_access')
    ordering = ('-is_superuser', '-is_staff', '-is_active', 'username')
    list_per_page = 50
    save_on_top = True

    class Media:
        css = {'all': ('common/css/custom_admin.css',)}

    @admin.display(description=_('Tài khoản'), ordering='username')
    def account_identity(self, obj):
        status_class = 'ok' if obj.is_active else 'danger'
        status_text = _('Hoạt động') if obj.is_active else _('Đã khóa')
        email = obj.email or _('Chưa có email')
        return format_html(
            '<div class="scmd-user-cell">'
            '<strong>{}</strong>'
            '<span>{}</span>'
            '<em class="scmd-pill scmd-pill-{}">{}</em>'
            '</div>',
            obj.username,
            email,
            status_class,
            status_text,
        )

    @admin.display(description=_('Hồ sơ nhân sự'))
    def employee_profile(self, obj):
        employee = getattr(obj, 'nhan_vien', None)
        if not employee:
            return format_html('<span class="scmd-muted">{}</span>', _('Chưa liên kết'))

        department = employee.phong_ban.ten_phong_ban if employee.phong_ban else _('Chưa có phòng ban')
        title = employee.chuc_danh.ten_chuc_danh if employee.chuc_danh else _('Chưa có chức danh')
        url = reverse('admin:users_nhanvien_change', args=[employee.pk])
        return format_html(
            '<div class="scmd-user-cell">'
            '<a href="{}"><strong>{} · {}</strong></a>'
            '<span>{}</span>'
            '<span>{}</span>'
            '</div>',
            url,
            employee.ma_nhan_vien,
            employee.ho_ten,
            department,
            title,
        )

    @admin.display(description=_('Nhóm quyền'))
    def group_summary(self, obj):
        groups = list(obj.groups.all()[:4])
        if not groups:
            return format_html('<span class="scmd-muted">{}</span>', _('Chưa gắn nhóm'))
        extra = obj.groups.count() - len(groups)
        badges = format_html_join(
            '',
            '<span class="scmd-pill scmd-pill-info">{}</span>',
            ((group.name,) for group in groups),
        )
        if extra > 0:
            badges = format_html('{}<span class="scmd-pill">+{}</span>', badges, extra)
        return format_html('<div class="scmd-pill-row">{}</div>', badges)

    @admin.display(description=_('Bảo mật'))
    def security_flags(self, obj):
        badges = []
        if obj.is_superuser:
            badges.append('<span class="scmd-pill scmd-pill-danger">Superuser</span>')
        if obj.is_staff:
            badges.append('<span class="scmd-pill scmd-pill-warning">Staff</span>')
        if obj.has_usable_password():
            badges.append('<span class="scmd-pill scmd-pill-ok">Có mật khẩu</span>')
        else:
            badges.append('<span class="scmd-pill">Không mật khẩu</span>')
        return format_html('<div class="scmd-pill-row">{}</div>', format_html(''.join(badges)))

    @admin.display(description=_('Đăng nhập cuối'), ordering='last_login')
    def last_login_short(self, obj):
        if not obj.last_login:
            return format_html('<span class="scmd-muted">{}</span>', _('Chưa đăng nhập'))
        return timezone.localtime(obj.last_login).strftime('%d/%m/%Y %H:%M')

    @admin.display(description=_('Ngày tạo'), ordering='date_joined')
    def date_joined_short(self, obj):
        return timezone.localtime(obj.date_joined).strftime('%d/%m/%Y')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'nhan_vien',
            'nhan_vien__phong_ban',
            'nhan_vien__chuc_danh',
        ).prefetch_related('groups')

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        stats = qs.aggregate(
            total=models.Count('id'),
            active=models.Count('id', filter=models.Q(is_active=True)),
            inactive=models.Count('id', filter=models.Q(is_active=False)),
            staff=models.Count('id', filter=models.Q(is_staff=True)),
            superuser=models.Count('id', filter=models.Q(is_superuser=True)),
            missing_employee=models.Count('id', filter=models.Q(nhan_vien__isnull=True))
        )
        context = {
            'scmd_user_stats': {
                'total': stats['total'],
                'active': stats['active'],
                'inactive': stats['inactive'],
                'staff': stats['staff'],
                'superuser': stats['superuser'],
                'missing_employee': stats['missing_employee'],
            },
            'scmd_user_links': {
                'add_user': reverse('admin:auth_user_add'),
                'groups': reverse('admin:auth_group_changelist'),
                'employees': reverse('admin:users_nhanvien_changelist'),
            },
        }
        if extra_context:
            context.update(extra_context)
        return super().changelist_view(request, extra_context=context)

    def _account_action_confirmation_context(self, request, queryset, *, action_name, title, warning):
        select_across = request.POST.get("select_across", "0")
        selected_ids = request.POST.getlist(ACTION_CHECKBOX_NAME)
        preview = list(queryset.order_by("username")[:25])
        selected_count_value = _bounded_count(queryset)
        return {
            **self.admin_site.each_context(request),
            "title": title,
            "opts": self.model._meta,
            "queryset": preview,
            "selected_count_display": _bounded_display(selected_count_value),
            "preview_has_more": select_across == "1" or selected_count_value > len(preview),
            "selected_ids": selected_ids,
            "action_name": action_name,
            "action_checkbox_name": ACTION_CHECKBOX_NAME,
            "select_across": select_across,
            "warning": warning,
            "changelist_url": reverse("admin:auth_user_changelist"),
        }

    def _apply_account_flag_action(self, request, queryset, *, action_name, field_name, target_value, title, warning, success_message, skip_queryset=None, message_level=messages.SUCCESS):
        """Apply sensitive account bulk actions with confirmation, save(), and audit.

        Account activation/staff changes affect access control.  Do not use
        ``queryset bulk update`` because it bypasses per-object governance and
        gives no AuditLog trail per user.
        """
        if not self.has_change_permission(request):
            self.message_user(request, _("Bạn không có quyền cập nhật tài khoản."), messages.ERROR)
            return None

        if request.POST.get("confirm_account_action") != "1":
            return TemplateResponse(
                request,
                "admin/auth/user/confirm_account_action.html",
                self._account_action_confirmation_context(
                    request,
                    queryset,
                    action_name=action_name,
                    title=title,
                    warning=warning,
                ),
            )

        changed = 0
        skipped = 0
        with transaction.atomic():
            locked_qs = queryset.select_for_update().order_by("pk")
            if skip_queryset is not None:
                skipped = _bounded_count(locked_qs.filter(pk__in=skip_queryset.values_list("pk", flat=True)))
                locked_qs = locked_qs.exclude(pk__in=skip_queryset.values_list("pk", flat=True))
            for account in locked_qs:
                old_value = getattr(account, field_name)
                if old_value == target_value:
                    skipped += 1
                    continue
                setattr(account, field_name, target_value)
                account.save(update_fields=[field_name])
                record_admin_audit_action(
                    request,
                    action=AuditLog.Action.UPDATE,
                    module="auth",
                    model_name="User",
                    object_id=account.pk,
                    note=f"Admin account bulk action: {action_name}",
                    changes={
                        "bulk_action": action_name,
                        "username": account.username,
                        field_name: {"old": old_value, "new": target_value},
                    },
                )
                changed += 1

        self.message_user(request, str(success_message).format(changed=changed, skipped=skipped), message_level)
        if skipped:
            self.message_user(request, _("Đã bỏ qua %(count)s tài khoản không cần đổi hoặc không an toàn để đổi.") % {"count": skipped}, messages.WARNING)
        return None

    @admin.action(description=_("Mở khóa tài khoản đã chọn — cần xác nhận"))
    def activate_accounts(self, request, queryset):
        return self._apply_account_flag_action(
            request, queryset,
            action_name="activate_accounts", field_name="is_active", target_value=True,
            title=_("Xác nhận mở khóa tài khoản"),
            warning=_("Thao tác này cho phép tài khoản đăng nhập lại. Hệ thống sẽ ghi AuditLog từng tài khoản."),
            success_message=_("Đã mở khóa {changed} tài khoản."),
        )

    @admin.action(description=_("Khóa tài khoản đã chọn — cần xác nhận"))
    def deactivate_accounts(self, request, queryset):
        return self._apply_account_flag_action(
            request, queryset,
            action_name="deactivate_accounts", field_name="is_active", target_value=False,
            title=_("Xác nhận khóa tài khoản"),
            warning=_("Không thể tự khóa tài khoản đang đăng nhập. Hãy kiểm tra danh sách trước khi xác nhận."),
            success_message=_("Đã khóa {changed} tài khoản."),
            skip_queryset=queryset.filter(pk=request.user.pk),
            message_level=messages.WARNING,
        )

    @admin.action(description=_("Cấp quyền staff — cần xác nhận"))
    def grant_staff_access(self, request, queryset):
        return self._apply_account_flag_action(
            request, queryset,
            action_name="grant_staff_access", field_name="is_staff", target_value=True,
            title=_("Xác nhận cấp quyền staff"),
            warning=_("Quyền staff cho phép vào khu vực admin. Hệ thống sẽ ghi AuditLog từng tài khoản."),
            success_message=_("Đã cấp quyền staff cho {changed} tài khoản."),
        )

    @admin.action(description=_("Gỡ quyền staff — cần xác nhận"))
    def revoke_staff_access(self, request, queryset):
        return self._apply_account_flag_action(
            request, queryset,
            action_name="revoke_staff_access", field_name="is_staff", target_value=False,
            title=_("Xác nhận gỡ quyền staff"),
            warning=_("Không thể gỡ quyền staff của superuser hoặc tài khoản đang đăng nhập qua thao tác hàng loạt."),
            success_message=_("Đã gỡ quyền staff khỏi {changed} tài khoản."),
            skip_queryset=queryset.filter(models.Q(pk=request.user.pk) | models.Q(is_superuser=True)),
            message_level=messages.WARNING,
        )
=======
    try:
        if not hasattr(user, 'nhan_vien') or not user.nhan_vien.chuc_danh or not user.nhan_vien.chuc_danh.nhom_quyen:
            return False
        group_name = user.nhan_vien.chuc_danh.nhom_quyen.name
        return group_name in ['BAN_GIAM_DOC', 'NHAN_SU', 'HANH_CHINH', 'ADMIN_HE_THONG']
    except Exception as e:
        logger.error(f"Lỗi kiểm tra quyền: {str(e)}")
        return False
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


# ==============================================================================
# 1. CẤU HÌNH IMPORT RESOURCE
# ==============================================================================
class NhanVienResource(resources.ModelResource):
    phong_ban = fields.Field(column_name=_('Phòng ban'), attribute='phong_ban', widget=ForeignKeyWidget(PhongBan, 'ten_phong_ban'))
    chuc_danh = fields.Field(column_name=_('Chức danh'), attribute='chuc_danh', widget=ForeignKeyWidget(ChucDanh, 'ten_chuc_danh'))
    ma_nhan_vien = fields.Field(attribute='ma_nhan_vien', column_name=_('Mã NV'))
    ho_ten = fields.Field(attribute='ho_ten', column_name=_('Họ và Tên'))
    sdt_chinh = fields.Field(attribute='sdt_chinh', column_name=_('Số điện thoại'))
    so_cccd = fields.Field(attribute='so_cccd', column_name=_('CCCD/CMND'))
<<<<<<< HEAD
    ngay_vao_lam = fields.Field(attribute='ngay_vao_lam', column_name=_('Ngày vào làm (dd/mm/yyyy)'), widget=SCMDVietnameseDateWidget())
=======
    ngay_vao_lam = fields.Field(attribute='ngay_vao_lam', column_name=_('Ngày vào làm (YYYY-MM-DD)'))
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

    class Meta:
        model = NhanVien
        fields = ('ma_nhan_vien', 'ho_ten', 'sdt_chinh', 'so_cccd', 'email', 'phong_ban', 'chuc_danh', 'ngay_vao_lam', 'trang_thai_lam_viec')
        export_order = fields
        import_id_fields = ('ma_nhan_vien',)
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, **kwargs):
        """Xử lý làm sạch dữ liệu trước khi nạp vào DB."""
        sdt = row.get(_('Số điện thoại'))
        if sdt:
            sdt_clean = str(sdt).replace(' ', '').replace('.', '').replace('-', '')
            row[_('Số điện thoại')] = sdt_clean
            if not sdt_clean.isdigit(): 
                raise ValidationError(_(f"Số điện thoại không hợp lệ: {sdt}"))
        
        cccd = row.get(_('CCCD/CMND'))
        if cccd:
            cccd_str = str(cccd).strip()
            if not cccd_str.isdigit(): 
                raise ValidationError(_(f"Số CCCD không hợp lệ: {cccd}"))


# ==============================================================================
# 2. CÁC BỘ LỌC TÙY CHỈNH
# ==============================================================================
class BirthdayMonthFilter(admin.SimpleListFilter):
    title = _('Sinh nhật trong tháng')
    parameter_name = 'birthday_month'
    
    def lookups(self, request, model_admin): 
        return [(str(i), f'Tháng {i}') for i in range(1, 13)]
    
    def queryset(self, request, queryset):
        if self.value(): 
            return queryset.filter(ngay_sinh__month=self.value())
        return queryset


<<<<<<< HEAD
class StaffOperationsSmartFilter(admin.SimpleListFilter):
    """Situation-based quick filter for the employee changelist.

    This filter only narrows the queryset that Django Admin already scoped via
    ``NhanVienAdmin.get_queryset``. It must not widen StaffVisibilityPolicy.
    """

    title = _('Tình huống')
    parameter_name = 'staff_ops'

    def lookups(self, request, model_admin):
        choices = [
            ('has_user', _('Có tài khoản')),
            ('missing_user', _('Chưa có tài khoản')),
            ('missing_site', _('Chưa phân mục tiêu')),
            ('missing_phone', _('Thiếu SĐT')),
            ('missing_email', _('Thiếu email')),
        ]
        if model_admin.digital_twin_filter_available(request):
            choices.append(('digital_twin', _('Có thiết bị nhận thông báo')))
        return choices

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'has_user':
            return queryset.filter(user__isnull=False)
        if value == 'missing_user':
            return queryset.filter(user__isnull=True)
        if value == 'missing_site':
            assigned_staff_ids = NhanVienAdmin.current_assignment_staff_ids(queryset)
            return queryset.exclude(pk__in=assigned_staff_ids)
        if value == 'missing_phone':
            return queryset.filter(models.Q(sdt_chinh__isnull=True) | models.Q(sdt_chinh=''))
        if value == 'missing_email':
            return queryset.filter(models.Q(email__isnull=True) | models.Q(email=''))
        if value == 'digital_twin':
            return queryset.exclude(fcm_token__isnull=True).exclude(fcm_token='')
        return queryset


=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
# ==============================================================================
# 3. CẤU HÌNH DANH MỤC & INLINES
# ==============================================================================
@admin.register(CauHinhMaNhanVien)
class CauHinhMaNhanVienAdmin(admin.ModelAdmin):
    list_display = ('tien_to', 'do_dai_so', 'so_hien_tai')


@admin.register(ChucDanh)
class ChucDanhAdmin(admin.ModelAdmin):
<<<<<<< HEAD
    """Quản trị chức danh theo hướng dễ rà soát phân quyền và cơ cấu nhân sự."""

    change_list_template = "admin/users/chucdanh/change_list.html"
    list_display = (
        "position_identity",
        "permission_group_badge",
        "employee_count_badge",
        "active_employee_badge",
        "quick_actions",
    )
    list_display_links = ("position_identity",)
    list_filter = ("nhom_quyen",)
    search_fields = ("ten_chuc_danh", "mo_ta", "nhom_quyen__name")
    list_select_related = ("nhom_quyen",)
    autocomplete_fields = ("nhom_quyen",)
    ordering = ("ten_chuc_danh",)
    list_per_page = 50
    save_on_top = True

    class Media:
        css = {"all": ("common/css/custom_admin.css",)}

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("nhom_quyen")
            .annotate(
                scmd_employee_count=models.Count("cac_nhan_vien", distinct=True),
                scmd_active_employee_count=models.Count(
                    "cac_nhan_vien",
                    filter=~models.Q(cac_nhan_vien__trang_thai_lam_viec="NGHIVIEC"),
                    distinct=True,
                ),
            )
        )

    @admin.display(description=_("Chức danh"), ordering="ten_chuc_danh")
    def position_identity(self, obj):
        description = obj.mo_ta or _("Chưa có mô tả nghiệp vụ")
        return format_html(
            '<div class="scmd-user-cell"><strong>{}</strong><span>{}</span></div>',
            obj.ten_chuc_danh,
            description,
        )

    @admin.display(description=_("Nhóm quyền"), ordering="nhom_quyen__name")
    def permission_group_badge(self, obj):
        if not obj.nhom_quyen:
            return format_html('<span class="scmd-admin-pill scmd-admin-pill-danger">Chưa gắn quyền</span>')
        url = reverse("admin:auth_group_change", args=[obj.nhom_quyen_id])
        return format_html(
            '<a class="scmd-admin-pill scmd-admin-pill-info" href="{}">{}</a>',
            url,
            obj.nhom_quyen.name,
        )

    @admin.display(description=_("Nhân sự"), ordering="scmd_employee_count")
    def employee_count_badge(self, obj):
        count = getattr(obj, "scmd_employee_count", 0)
        tone = "muted" if count == 0 else "success"
        return format_html('<span class="scmd-admin-pill scmd-admin-pill-{}">{} nhân sự</span>', tone, count)

    @admin.display(description=_("Đang làm"), ordering="scmd_active_employee_count")
    def active_employee_badge(self, obj):
        count = getattr(obj, "scmd_active_employee_count", 0)
        return format_html('<span class="scmd-admin-muted">{} còn hiệu lực</span>', count)

    @admin.display(description=_("Thao tác"))
    def quick_actions(self, obj):
        employee_url = f'{reverse("admin:users_nhanvien_changelist")}?chuc_danh__id__exact={obj.pk}'
        change_url = reverse("admin:users_chucdanh_change", args=[obj.pk])
        return format_html(
            '<div class="scmd-admin-actions">'
            '<a class="button scmd-admin-mini-button" href="{}">Sửa</a>'
            '<a class="button scmd-admin-mini-button scmd-admin-mini-button-secondary" href="{}">Nhân sự</a>'
            '</div>',
            change_url,
            employee_url,
        )

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        total_positions = _bounded_count(qs)
        positions_without_group = _bounded_count(qs.filter(nhom_quyen__isnull=True))
        empty_positions = _bounded_count(qs.filter(scmd_employee_count=0))
        active_positions = _bounded_count(qs.filter(scmd_active_employee_count__gt=0))
        extra_context = extra_context or {}
        extra_context.update(
            {
                "scmd_position_stats": {
                    "total_positions": total_positions,
                    "active_positions": active_positions,
                    "positions_without_group": positions_without_group,
                    "empty_positions": empty_positions,
                },
                "scmd_position_links": {
                    "add_position": reverse("admin:users_chucdanh_add"),
                    "employee_list": reverse("admin:users_nhanvien_changelist"),
                    "group_list": reverse("admin:auth_group_changelist"),
                    "department_list": reverse("admin:users_phongban_changelist"),
                },
            }
        )
        return super().changelist_view(request, extra_context=extra_context)
=======
    list_display = ('ten_chuc_danh', 'nhom_quyen')
    search_fields = ('ten_chuc_danh',)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


@admin.register(PhongBan)
class PhongBanAdmin(admin.ModelAdmin):
    list_display = ('ten_phong_ban', 'nhom_quyen')
    search_fields = ('ten_phong_ban',)


class HocVanInline(admin.TabularInline):
    model = HocVan
    extra = 0
    verbose_name_plural = _("🎓 Quá trình Học vấn")
    formfield_overrides = {
<<<<<<< HEAD
        models.CharField: {'widget': TextInput(attrs={'class': 'vTextField'})}
    }

    def get_extra(self, request, obj=None, **kwargs):
        """Hiển thị sẵn một dòng nhập khi tạo mới nhân viên.

        Nếu `extra = 0` ở màn hình add, người dùng không thấy ô nhập nào và
        tưởng phần học vấn bị mất. Khi sửa hồ sơ đã có, vẫn giữ mặc định gọn
        để tránh thêm dòng rỗng không cần thiết.
        """
        return 1 if obj is None else 0

=======
        models.CharField: {'widget': TextInput(attrs={'style': 'width: 250px;'})}
    }

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

class BangCapChungChiInline(admin.TabularInline):
    model = BangCapChungChi
    extra = 0
    verbose_name_plural = _("📜 Bằng cấp & Chứng chỉ")

<<<<<<< HEAD
    def get_extra(self, request, obj=None, **kwargs):
        """Hiển thị sẵn một dòng nhập chứng chỉ trên màn hình thêm mới."""
        return 1 if obj is None else 0

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

class LichSuCongTacInline(admin.TabularInline):
    model = LichSuCongTac
    extra = 0
    fk_name = "nhan_vien"
    verbose_name_plural = _("🏢 Lịch sử Công tác")
    autocomplete_fields = ['muc_tieu']
<<<<<<< HEAD

    def get_extra(self, request, obj=None, **kwargs):
        """Hiển thị sẵn một dòng nhập lịch sử công tác trên màn hình thêm mới."""
        return 1 if obj is None else 0
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    
    def get_readonly_fields(self, request, obj=None):
        return ['ngay_bat_dau'] if obj else []


<<<<<<< HEAD
class HopDongLaoDongInline(admin.TabularInline):
    model = HopDongLaoDong
    extra = 0
    verbose_name_plural = _("🧾 Hợp đồng lao động")
    fields = (
        "so_hop_dong",
        "loai_hop_dong",
        "trang_thai",
        "ngay_ky",
        "ngay_hieu_luc",
        "ngay_het_han",
        "muc_luong_co_ban",
        "phu_cap",
        "file_hop_dong",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("nhan_vien")


class DonNghiPhepInline(admin.TabularInline):
    model = DonNghiPhep
    extra = 0
    verbose_name_plural = _("🌿 Đơn nghỉ phép")
    fields = ("ma_don", "loai_nghi", "tu_ngay", "den_ngay", "so_ngay", "trang_thai")


class HoSoBaoHiemInline(admin.TabularInline):
    model = HoSoBaoHiem
    extra = 0
    verbose_name_plural = _("🛡 Hồ sơ bảo hiểm")
    fields = ("so_bao_hiem", "loai_bao_hiem", "ngay_tham_gia", "ngay_ket_thuc", "trang_thai", "file_ho_so")


class PhuLucHopDongLaoDongInline(admin.TabularInline):
    model = PhuLucHopDongLaoDong
    extra = 0
    fields = ("so_phu_luc", "ngay_ky", "ngay_hieu_luc", "ngay_het_han", "file_phu_luc", "ghi_chu")
    verbose_name_plural = _("Phụ lục hợp đồng lao động")


@admin.register(HopDongLaoDong)
class HopDongLaoDongAdmin(admin.ModelAdmin):
    list_display = (
        "contract_identity",
        "employee_summary",
        "loai_hop_dong",
        "status_badge",
        "ngay_hieu_luc",
        "ngay_het_han",
        "salary_summary",
    )
    list_filter = (
        "trang_thai",
        "loai_hop_dong",
        ("ngay_het_han", admin.DateFieldListFilter),
        ("ngay_hieu_luc", admin.DateFieldListFilter),
    )
    search_fields = ("so_hop_dong", "nhan_vien__ma_nhan_vien", "nhan_vien__ho_ten")
    autocomplete_fields = ("nhan_vien", "nguoi_duyet")
    list_select_related = ("nhan_vien", "nguoi_duyet")
    readonly_fields = ("created_at", "updated_at", "ngay_duyet")
    inlines = [PhuLucHopDongLaoDongInline]
    save_on_top = True
    list_per_page = 50

    fieldsets = (
        (_("1. Thông tin hợp đồng"), {
            "fields": (
                "nhan_vien",
                "so_hop_dong",
                "loai_hop_dong",
                "trang_thai",
                "nguon_ho_so",
            ),
            "classes": ("scmd-form-section", "scmd-form-section-primary"),
        }),
        (_("2. Hiệu lực và ký kết"), {
            "fields": (
                "ngay_ky",
                "ngay_hieu_luc",
                "ngay_het_han",
                "nguoi_duyet",
                "ngay_duyet",
            ),
            "classes": ("scmd-form-section",),
        }),
        (_("3. Lương tham chiếu và bằng chứng"), {
            "fields": (
                "muc_luong_co_ban",
                "phu_cap",
                "file_hop_dong",
                "ghi_chu",
            ),
            "description": _("Các khoản lương/phụ cấp ở đây là dữ liệu hợp đồng nguồn; payroll hiện tại không bị tự động ghi đè."),
            "classes": ("scmd-form-section",),
        }),
        (_("4. Hệ thống"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = HopDongLaoDong.objects.filter(pk=obj.pk).values_list("trang_thai", flat=True).first()
        if obj.trang_thai in HopDongLaoDong.ACTIVE_CONTRACT_STATUSES and not obj.nguoi_duyet_id:
            obj.nguoi_duyet = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
            obj.ngay_duyet = timezone.now()
        if change and old_status != obj.trang_thai:
            WorkflowTransitionPolicy.validate_transition(type(obj).__name__, old_status, obj.trang_thai, obj.ALLOWED_STATUS_TRANSITIONS)
        super().save_model(request, obj, form, change)
        if change and old_status != obj.trang_thai:
            obj.record_status_transition(
                actor=request.user,
                old_status=old_status,
                new_status=obj.trang_thai,
                note="Admin HR labor contract status save",
            )

    @admin.display(description=_("Hợp đồng"), ordering="so_hop_dong")
    def contract_identity(self, obj):
        return format_html("<strong>{}</strong><br><span class='text-muted'>{}</span>", obj.so_hop_dong, obj.get_nguon_ho_so_display())

    @admin.display(description=_("Nhân viên"), ordering="nhan_vien__ho_ten")
    def employee_summary(self, obj):
        return format_html("<strong>{}</strong><br><span class='text-muted'>{}</span>", obj.nhan_vien.ho_ten, obj.nhan_vien.ma_nhan_vien)

    @admin.display(description=_("Trạng thái"), ordering="trang_thai")
    def status_badge(self, obj):
        tone_map = {
            HopDongLaoDong.TrangThai.DRAFT: "secondary",
            HopDongLaoDong.TrangThai.PENDING_SIGNATURE: "warning",
            HopDongLaoDong.TrangThai.ACTIVE: "success",
            HopDongLaoDong.TrangThai.EXPIRING: "warning",
            HopDongLaoDong.TrangThai.EXPIRED: "danger",
            HopDongLaoDong.TrangThai.TERMINATED: "dark",
        }
        return format_html('<span class="badge badge-{}">{}</span>', tone_map.get(obj.trang_thai, "secondary"), obj.get_trang_thai_display())

    @admin.display(description=_("Lương/phụ cấp"))
    def salary_summary(self, obj):
        return format_html("{} / {}", obj.muc_luong_co_ban, obj.phu_cap)


@admin.register(PhuLucHopDongLaoDong)
class PhuLucHopDongLaoDongAdmin(admin.ModelAdmin):
    list_display = ("so_phu_luc", "hop_dong", "ngay_hieu_luc", "ngay_het_han")
    list_filter = (("ngay_hieu_luc", admin.DateFieldListFilter), ("ngay_het_han", admin.DateFieldListFilter))
    search_fields = ("so_phu_luc", "hop_dong__so_hop_dong", "hop_dong__nhan_vien__ma_nhan_vien", "hop_dong__nhan_vien__ho_ten")
    autocomplete_fields = ("hop_dong",)



@admin.register(DonNghiPhep)
class DonNghiPhepAdmin(admin.ModelAdmin):
    list_display = ("ma_don", "employee_summary", "loai_nghi", "tu_ngay", "den_ngay", "so_ngay", "status_badge")
    list_filter = ("trang_thai", "loai_nghi", ("tu_ngay", admin.DateFieldListFilter), ("den_ngay", admin.DateFieldListFilter))
    search_fields = ("ma_don", "nhan_vien__ma_nhan_vien", "nhan_vien__ho_ten", "ly_do")
    autocomplete_fields = ("nhan_vien", "nguoi_duyet")
    list_select_related = ("nhan_vien", "nguoi_duyet")
    readonly_fields = ("created_at", "updated_at", "ngay_duyet")
    save_on_top = True

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = DonNghiPhep.objects.filter(pk=obj.pk).values_list("trang_thai", flat=True).first()
        if obj.trang_thai == DonNghiPhep.TrangThai.APPROVED and not obj.nguoi_duyet_id:
            obj.nguoi_duyet = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
            obj.ngay_duyet = timezone.now()
        if change and old_status != obj.trang_thai:
            WorkflowTransitionPolicy.validate_transition(type(obj).__name__, old_status, obj.trang_thai, obj.ALLOWED_STATUS_TRANSITIONS)
        super().save_model(request, obj, form, change)
        if change and old_status != obj.trang_thai:
            obj.record_status_transition(actor=request.user, old_status=old_status, new_status=obj.trang_thai, note="Admin leave request status save")

    @admin.display(description=_("Nhân viên"), ordering="nhan_vien__ho_ten")
    def employee_summary(self, obj):
        return format_html("<strong>{}</strong><br><span class='text-muted'>{}</span>", obj.nhan_vien.ho_ten, obj.nhan_vien.ma_nhan_vien)

    @admin.display(description=_("Trạng thái"), ordering="trang_thai")
    def status_badge(self, obj):
        tone = "success" if obj.trang_thai == DonNghiPhep.TrangThai.APPROVED else "warning" if obj.trang_thai == DonNghiPhep.TrangThai.PENDING_APPROVAL else "secondary"
        return format_html('<span class="badge badge-{}">{}</span>', tone, obj.get_trang_thai_display())


class OffboardingChecklistInline(admin.StackedInline):
    model = OffboardingChecklist
    extra = 0
    can_delete = False
    verbose_name_plural = _("Checklist bàn giao")


@admin.register(QuyetDinhNghiViec)
class QuyetDinhNghiViecAdmin(admin.ModelAdmin):
    list_display = ("so_quyet_dinh", "employee_summary", "ngay_quyet_dinh", "ngay_hieu_luc", "status_badge")
    list_filter = ("trang_thai", ("ngay_hieu_luc", admin.DateFieldListFilter), ("ngay_quyet_dinh", admin.DateFieldListFilter))
    search_fields = ("so_quyet_dinh", "nhan_vien__ma_nhan_vien", "nhan_vien__ho_ten", "ly_do_nghi")
    autocomplete_fields = ("nhan_vien", "nguoi_duyet")
    list_select_related = ("nhan_vien", "nguoi_duyet")
    readonly_fields = ("created_at", "updated_at", "ngay_duyet")
    inlines = [OffboardingChecklistInline]
    save_on_top = True

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = QuyetDinhNghiViec.objects.filter(pk=obj.pk).values_list("trang_thai", flat=True).first()
        if obj.trang_thai in (QuyetDinhNghiViec.TrangThai.APPROVED, QuyetDinhNghiViec.TrangThai.EFFECTIVE) and not obj.nguoi_duyet_id:
            obj.nguoi_duyet = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
            obj.ngay_duyet = timezone.now()
        if change and old_status != obj.trang_thai:
            WorkflowTransitionPolicy.validate_transition(type(obj).__name__, old_status, obj.trang_thai, obj.ALLOWED_STATUS_TRANSITIONS)
        super().save_model(request, obj, form, change)
        if change and old_status != obj.trang_thai:
            obj.record_status_transition(actor=request.user, old_status=old_status, new_status=obj.trang_thai, note="Admin offboarding decision status save")

    @admin.display(description=_("Nhân viên"), ordering="nhan_vien__ho_ten")
    def employee_summary(self, obj):
        return format_html("<strong>{}</strong><br><span class='text-muted'>{}</span>", obj.nhan_vien.ho_ten, obj.nhan_vien.ma_nhan_vien)

    @admin.display(description=_("Trạng thái"), ordering="trang_thai")
    def status_badge(self, obj):
        tone = "danger" if obj.trang_thai == QuyetDinhNghiViec.TrangThai.EFFECTIVE else "success" if obj.trang_thai == QuyetDinhNghiViec.TrangThai.APPROVED else "warning" if obj.trang_thai == QuyetDinhNghiViec.TrangThai.PENDING_APPROVAL else "secondary"
        return format_html('<span class="badge badge-{}">{}</span>', tone, obj.get_trang_thai_display())


@admin.register(OffboardingChecklist)
class OffboardingChecklistAdmin(admin.ModelAdmin):
    list_display = ("quyet_dinh", "hoan_tat", "thu_hoi_dong_phuc", "ban_giao_tai_san", "khoa_tai_khoan", "chot_cong", "quyet_toan_luong", "asset_recovery_link")
    list_filter = ("hoan_tat", "thu_hoi_dong_phuc", "ban_giao_tai_san", "khoa_tai_khoan", "chot_cong", "quyet_toan_luong")
    search_fields = ("quyet_dinh__so_quyet_dinh", "quyet_dinh__nhan_vien__ma_nhan_vien", "quyet_dinh__nhan_vien__ho_ten")
    autocomplete_fields = ("quyet_dinh", "nguoi_xac_nhan")
    list_select_related = ("quyet_dinh", "quyet_dinh__nhan_vien", "nguoi_xac_nhan")
    readonly_fields = ("asset_recovery_link",)

    @admin.display(description=_("Phiếu thu hồi tài sản"))
    def asset_recovery_link(self, obj):
        if not obj or not obj.pk:
            return "-"
        url = reverse("admin:inventory_phieuthuhoi_changelist") + f"?offboarding_checklist__id__exact={obj.pk}"
        return format_html('<a class="button" href="{}">Mở phiếu thu hồi</a>', url)


@admin.register(HoSoBaoHiem)
class HoSoBaoHiemAdmin(admin.ModelAdmin):
    list_display = ("so_bao_hiem", "employee_summary", "loai_bao_hiem", "ngay_tham_gia", "ngay_ket_thuc", "status_badge")
    list_filter = ("trang_thai", "loai_bao_hiem", ("ngay_tham_gia", admin.DateFieldListFilter), ("ngay_ket_thuc", admin.DateFieldListFilter))
    search_fields = ("so_bao_hiem", "nhan_vien__ma_nhan_vien", "nhan_vien__ho_ten")
    autocomplete_fields = ("nhan_vien", "nguoi_duyet")
    list_select_related = ("nhan_vien", "nguoi_duyet")
    readonly_fields = ("created_at", "updated_at", "ngay_duyet")
    save_on_top = True

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = HoSoBaoHiem.objects.filter(pk=obj.pk).values_list("trang_thai", flat=True).first()
        if obj.trang_thai == HoSoBaoHiem.TrangThai.ACTIVE and not obj.nguoi_duyet_id:
            obj.nguoi_duyet = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
            obj.ngay_duyet = timezone.now()
        if change and old_status != obj.trang_thai:
            WorkflowTransitionPolicy.validate_transition(type(obj).__name__, old_status, obj.trang_thai, obj.ALLOWED_STATUS_TRANSITIONS)
        super().save_model(request, obj, form, change)
        if change and old_status != obj.trang_thai:
            obj.record_status_transition(actor=request.user, old_status=old_status, new_status=obj.trang_thai, note="Admin insurance profile status save")

    @admin.display(description=_("Nhân viên"), ordering="nhan_vien__ho_ten")
    def employee_summary(self, obj):
        return format_html("<strong>{}</strong><br><span class='text-muted'>{}</span>", obj.nhan_vien.ho_ten, obj.nhan_vien.ma_nhan_vien)

    @admin.display(description=_("Trạng thái"), ordering="trang_thai")
    def status_badge(self, obj):
        tone = "success" if obj.trang_thai == HoSoBaoHiem.TrangThai.ACTIVE else "warning" if obj.trang_thai == HoSoBaoHiem.TrangThai.PAUSED else "secondary"
        return format_html('<span class="badge badge-{}">{}</span>', tone, obj.get_trang_thai_display())


=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
# ==============================================================================
# 4. NHÂN VIÊN ADMIN (MAIN VIEW)
# ==============================================================================
@admin.register(NhanVien)
class NhanVienAdmin(ImportExportModelAdmin):
    resource_class = NhanVienResource
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('download-template/', self.download_template_view, name='nhanvien-download-template'),
            path('<int:object_id>/print-profile/', self.admin_site.admin_view(self.print_profile_view), name='nhanvien-print-profile'),
            path('print-profiles-bulk/', self.admin_site.admin_view(self.print_profiles_bulk_view), name='nhanvien-print-profiles-bulk'),
        ]
        return custom_urls + urls

    # --- UI & DISPLAY ---
<<<<<<< HEAD
    list_display = (
        'employee_identity',
        'work_assignment',
        'contact_summary',
        'account_status',
        'status_badge',
        'print_btn',
    )
    list_display_links = ('employee_identity',)
    list_filter = (StaffOperationsSmartFilter, 'trang_thai_lam_viec', 'phong_ban', 'chuc_danh', BirthdayMonthFilter, ('ngay_vao_lam', admin.DateFieldListFilter))
    search_fields = ('ho_ten', 'ma_nhan_vien', 'sdt_chinh', 'email', 'so_cccd')
    list_select_related = ('phong_ban', 'chuc_danh', 'user')
    list_per_page = 50
    save_on_top = True
    inlines = [HopDongLaoDongInline, DonNghiPhepInline, HoSoBaoHiemInline, LichSuCongTacInline, HocVanInline, BangCapChungChiInline]
=======
    list_display = ('avatar_thumb', 'ma_nhan_vien_bold', 'ho_ten', 'chuc_danh', 'phong_ban', 'sdt_action', 'status_badge', 'print_btn')
    list_display_links = ('avatar_thumb', 'ma_nhan_vien_bold', 'ho_ten')
    list_filter = ('trang_thai_lam_viec', 'phong_ban', 'chuc_danh', BirthdayMonthFilter, ('ngay_vao_lam', admin.DateFieldListFilter))
    search_fields = ('ho_ten', 'ma_nhan_vien', 'sdt_chinh', 'so_cccd')
    list_select_related = ('phong_ban', 'chuc_danh', 'user')
    inlines = [LichSuCongTacInline, HocVanInline, BangCapChungChiInline]
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    autocomplete_fields = ['phong_ban', 'chuc_danh']
    readonly_fields = ('ma_nhan_vien', 'image_preview_large')
    actions = ['make_official', 'make_resigned', 'download_template_action', 'print_selected_profiles']

<<<<<<< HEAD
    class Media:
        css = {'all': ('common/css/custom_admin.css', 'common/css/operations_ux.css')}
        js = ('common/js/operations_ux.js',)

    def changelist_view(self, request, extra_context=None):
        """Render operations-first employee changelist context.

        All numbers are computed from ``get_queryset(request)`` so smart filters,
        cards and queue links never widen StaffVisibilityPolicy. Django Admin
        search, filters, actions and pagination remain rendered by ``block.super``.
        """
        scoped_qs = self.get_queryset(request)
        active_statuses = [
            NhanVien.TrangThaiLamViec.CHINH_THUC,
            NhanVien.TrangThaiLamViec.THU_VIEC,
        ]
        assigned_staff_ids = self.current_assignment_staff_ids(scoped_qs)
        stats = scoped_qs.aggregate(
            total=models.Count('pk'),
            active=models.Count('pk', filter=models.Q(trang_thai_lam_viec__in=active_statuses)),
            probation=models.Count('pk', filter=models.Q(trang_thai_lam_viec=NhanVien.TrangThaiLamViec.THU_VIEC)),
            resigned=models.Count('pk', filter=models.Q(trang_thai_lam_viec=NhanVien.TrangThaiLamViec.NGHI_VIEC)),
            has_user=models.Count('pk', filter=models.Q(user__isnull=False)),
            missing_user=models.Count('pk', filter=models.Q(user__isnull=True)),
            missing_contact=models.Count('pk', filter=(models.Q(sdt_chinh__isnull=True) | models.Q(sdt_chinh=''))),
            missing_email=models.Count('pk', filter=(models.Q(email__isnull=True) | models.Q(email=''))),
            missing_assignment=models.Count('pk', filter=(models.Q(phong_ban__isnull=True) | models.Q(chuc_danh__isnull=True))),
            digital_twin=models.Count('pk', filter=(models.Q(fcm_token__isnull=False) & ~models.Q(fcm_token=''))),
        )
        stats['missing_site'] = _bounded_count(scoped_qs.exclude(pk__in=assigned_staff_ids))

        operations_ux = AdminOperationsUXProvider.build(request.user)
        query_string = request.META.get('QUERY_STRING', '')
        export_filtered_url = request.path + 'export/' + (f'?{query_string}' if query_string else '')
        print_selected_url = request.path + 'print-profiles-bulk/'
        missing_data_export_url = request.path + 'export/?staff_ops=missing_phone'

        context = {
            'page_header': {
                'kicker': 'SCMD Pro · Nhân sự vận hành',
                'title': 'Danh sách nhân viên',
                'subtitle': 'Quản lý hồ sơ, tài khoản và phân bổ mục tiêu của nhân sự vận hành.',
                'actions': [
                    {'label': 'Nhập file', 'url': request.path + 'import/', 'icon': 'fas fa-file-import'},
                    {'label': 'Xuất file', 'url': request.path + 'export/', 'icon': 'fas fa-file-export'},
                    {'label': 'Thêm nhân viên', 'url': reverse('admin:users_nhanvien_add'), 'icon': 'fas fa-user-plus', 'primary': True},
                ],
            },
            'summary_cards': [
                {'key': 'total', 'label': 'Tổng hồ sơ', 'value': stats['total'], 'note': 'Trong phạm vi quyền xem hiện tại.', 'tone': 'neutral'},
                {'key': 'active', 'label': 'Còn hiệu lực', 'value': stats['active'], 'note': 'Chính thức và thử việc.', 'tone': 'success' if stats['active'] else 'neutral'},
                {'key': 'missing_site', 'label': 'Chưa phân mục tiêu', 'value': _bounded_display(stats['missing_site']), 'note': 'Cần bổ sung mục tiêu hiện hành.', 'tone': 'warning' if stats['missing_site'] else 'success'},
                {'key': 'missing_contact', 'label': 'Thiếu SĐT', 'value': stats['missing_contact'], 'note': 'Ảnh hưởng liên lạc khẩn cấp.', 'tone': 'warning' if stats['missing_contact'] else 'success'},
            ],
            'smart_filters': self.build_smart_filters(request, stats),
            'work_queue_items': [
                item
                for item in operations_ux.get('work_queue_items', [])
                if str(item.get('key', '')).startswith('staff_')
            ][:2],
            'work_queue_title': 'Việc nhân sự cần xử lý',
            'work_queue_subtitle': 'Chỉ hiển thị việc cần xử lý trong phạm vi StaffVisibilityPolicy.',
            'bulk_bar': {
                'title': 'Thao tác với dòng đã chọn',
                'idle_note': 'Chọn một hoặc nhiều dòng trong bảng để mở thao tác hàng loạt an toàn.',
                'note': 'Có thể in hồ sơ, xuất theo bộ lọc hiện tại hoặc mở Action mặc định. Các Action đổi trạng thái sẽ chuyển sang màn xác nhận và ghi AuditLog từng hồ sơ; thanh này không tự ghi dữ liệu.',
                'safe_actions': ['In hồ sơ đã chọn', 'Xuất danh sách theo filter', 'Tải danh sách thiếu dữ liệu'],
                'print_selected_url': print_selected_url,
                'idle_links': [
                    {'label': 'Xuất danh sách theo filter hiện tại', 'url': export_filtered_url},
                    {'label': 'Tải danh sách thiếu SĐT', 'url': missing_data_export_url},
                ],
                'links': [
                    {'label': 'Tải file mẫu', 'url': reverse('admin:nhanvien-download-template')},
                    {'label': 'Xuất danh sách theo filter', 'url': export_filtered_url},
                    {'label': 'Tài khoản', 'url': reverse('admin:auth_user_changelist')},
                ],
            },
            'scmd_employee_links': {
                'add_employee': reverse('admin:users_nhanvien_add'),
                'download_template': reverse('admin:nhanvien-download-template'),
                'user_list': reverse('admin:auth_user_changelist'),
                'department_list': reverse('admin:users_phongban_changelist'),
                'position_list': reverse('admin:users_chucdanh_changelist'),
            },
            'scmd_employee_stats': stats,
            'scmd_employee_health': {
                'has_missing_user': stats['missing_user'] > 0,
                'has_missing_contact': stats['missing_contact'] > 0,
                'has_missing_assignment': stats['missing_assignment'] > 0 or stats['missing_site'] > 0,
            },
        }
        if extra_context:
            context.update(extra_context)
        return super().changelist_view(request, extra_context=context)

    @staticmethod
    def current_assignment_staff_ids(queryset):
        return (
            LichSuCongTac.objects.filter(
                nhan_vien__in=queryset,
                muc_tieu__isnull=False,
                ngay_ket_thuc__isnull=True,
            )
            .values_list('nhan_vien_id', flat=True)
            .distinct()
        )

    def digital_twin_filter_available(self, request):
        return self.get_queryset(request).exclude(fcm_token__isnull=True).exclude(fcm_token='').exists()

    def build_smart_filters(self, request, stats):
        options = [
            ('', _('Tất cả'), stats['total']),
            ('has_user', _('Có tài khoản'), stats['has_user']),
            ('missing_user', _('Chưa có tài khoản'), stats['missing_user']),
            ('missing_site', _('Chưa phân mục tiêu'), stats['missing_site']),
            ('missing_phone', _('Thiếu SĐT'), stats['missing_contact']),
            ('missing_email', _('Thiếu email'), stats['missing_email']),
        ]
        if stats.get('digital_twin'):
            options.append(('digital_twin', _('Có thiết bị nhận thông báo'), stats['digital_twin']))

        active_value = request.GET.get('staff_ops', '')
        return [
            {
                'key': value or 'all',
                'label': label,
                'count': count,
                'active': active_value == value,
                'url': self.smart_filter_url(request, value),
            }
            for value, label, count in options
        ]

    @staticmethod
    def smart_filter_url(request, value):
        params = request.GET.copy()
        params.pop('p', None)
        if value:
            params['staff_ops'] = value
        else:
            params.pop('staff_ops', None)
        query_string = params.urlencode()
        return f"{request.path}?{query_string}" if query_string else request.path



    def _employee_audit_snapshot(self, obj):
        return {
            "ho_ten": obj.ho_ten,
            "phong_ban_id": obj.phong_ban_id,
            "chuc_danh_id": obj.chuc_danh_id,
            "trang_thai_lam_viec": obj.trang_thai_lam_viec,
            "sdt_chinh": obj.sdt_chinh,
            "email": obj.email,
        }

    def save_model(self, request, obj, form, change):
        before = None
        if change and obj.pk:
            before_obj = self.get_queryset(request).filter(pk=obj.pk).first()
            if before_obj is not None:
                before = self._employee_audit_snapshot(before_obj)

        super().save_model(request, obj, form, change)

        try:
            AuditLog.objects.create(
                user=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
                action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
                module="users",
                model_name="NhanVien",
                object_id=str(obj.pk),
                tenant_id=getattr(obj, "tenant_id", None),
                changes={
                    "before": before,
                    "after": self._employee_audit_snapshot(obj),
                },
                note="Admin HR profile save",
            )
        except Exception as exc:
            logger.error("Failed to audit NhanVien admin save: %s", exc)

    formfield_overrides = {
        # Width is controlled by SCMD admin CSS so the same form remains compact
        # on desktop and still thumb-friendly on mobile. Avoid inline width here.
        models.CharField: {'widget': TextInput(attrs={'class': 'vTextField'})},
        models.EmailField: {'widget': TextInput(attrs={'class': 'vTextField'})},
        models.ForeignKey: {'widget': Select(attrs={'class': 'vSelectField'})},
=======
    class Media: 
        css = { 'all': ('css/custom_admin.css',) }

    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'class': 'vTextField', 'style': 'width: 100%; max-width: 400px;'})},
        models.EmailField: {'widget': TextInput(attrs={'class': 'vTextField', 'style': 'width: 100%; max-width: 400px;'})},
        models.ForeignKey: {'widget': Select(attrs={'style': 'width: 100%; max-width: 405px;'})},
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    }

    # --- CORE BUSINESS: IN LÝ LỊCH ---
    @admin.display(description=_('In hồ sơ'))
    def print_btn(self, obj):
        """Nút in lý lịch cá nhân nhanh trên list view."""
        return format_html(
<<<<<<< HEAD
            '<a class="scmd-employee-row-action" href="{}" target="_blank" rel="noopener">'
            '<i class="fas fa-print" aria-hidden="true"></i><span>{}</span></a>',
            f'./{obj.pk}/print-profile/',
            _('In hồ sơ'),
=======
            '<a class="button" href="{}" target="_blank" style="background-color: #4f46e5; color: white; '
            'padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 600;">'
            '<i class="fas fa-print"></i> IN LÝ LỊCH</a>',
            f'./{obj.pk}/print-profile/'
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        )

    def print_profile_view(self, request, object_id):
        """View xử lý in lý lịch chi tiết nhân viên."""
        obj = self.get_object(request, object_id)
<<<<<<< HEAD
        if obj is not None:
            record_export_audit(
                request,
                module="users",
                model_name="NhanVien",
                object_id=obj.pk,
                note="Export print ho so nhan vien",
                changes={"ma_nhan_vien": obj.ma_nhan_vien},
            )
        return TemplateResponse(request, "admin/users/nhanvien/print_profile.html", {"nhan_vien": obj})

    @admin.action(description=_('In lý lịch trích ngang đã chọn'))
    def print_selected_profiles(self, request, queryset):
        """Action in hàng loạt lý lịch nhân viên đã chọn."""
        selected_ids = list(queryset.values_list("id", flat=True))
        record_export_audit(
            request,
            module="users",
            model_name="NhanVien",
            note="Export print ho so nhan vien hang loat",
            changes={"selected_ids": selected_ids, "count": len(selected_ids)},
        )
=======
        return TemplateResponse(request, "admin/users/nhanvien/print_profile.html", {"nhan_vien": obj})

    @admin.action(description=_('🖨️ In lý lịch trích ngang đã chọn'))
    def print_selected_profiles(self, request, queryset):
        """Action in hàng loạt lý lịch nhân viên đã chọn."""
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        return TemplateResponse(request, "admin/users/nhanvien/print_profile_bulk.html", {"queryset": queryset})

    def print_profiles_bulk_view(self, request):
        """Xử lý dữ liệu đầu vào cho in hàng loạt qua URL."""
        ids = request.GET.get('ids', '').split(',')
<<<<<<< HEAD
        queryset = self.get_queryset(request).filter(pk__in=ids)
        return self.print_selected_profiles(request, queryset)

    # --- DISPLAY METHODS ---
    @admin.display(description=_('Nhân viên'), ordering='ho_ten')
    def employee_identity(self, obj):
        """Compact identity cell for the employee changelist.

        Keep visual sizing in the shared admin component CSS so this row follows
        the same design system as other operational tables.
        """
        return format_html(
            '<div class="scmd-employee-cell scmd-employee-identity">'
            '<img class="scmd-employee-avatar" src="{}" alt="" '
            'width="40" height="40" loading="lazy" decoding="async" />'
            '<div><strong>{}</strong><span>{}</span></div>'
            '</div>',
            obj.avatar_url,
            obj.ho_ten,
            obj.ma_nhan_vien,
        )

    @admin.display(description=_('Vị trí công tác'), ordering='chuc_danh')
    def work_assignment(self, obj):
        department = obj.phong_ban.ten_phong_ban if obj.phong_ban else _('Chưa có phòng ban')
        title = obj.chuc_danh.ten_chuc_danh if obj.chuc_danh else _('Chưa có chức danh')
        tone = 'warning' if (not obj.phong_ban or not obj.chuc_danh) else 'neutral'
        return format_html(
            '<div class="scmd-employee-cell">'
            '<strong>{}</strong><span class="scmd-employee-muted scmd-employee-{}">{}</span>'
            '</div>',
            title,
            tone,
            department,
        )

    @admin.display(description=_('Liên hệ'))
    def contact_summary(self, obj):
        phone = obj.sdt_chinh or ''
        email = obj.email or _('Chưa có email')
        if not phone:
            return format_html(
                '<div class="scmd-employee-cell"><strong class="scmd-employee-warning">{}</strong><span>{}</span></div>',
                _('Thiếu SĐT'),
                email,
            )
        return format_html(
            '<div class="scmd-employee-cell"><a class="scmd-employee-phone" href="tel:{}">{}</a><span>{}</span></div>',
            phone,
            phone,
            email,
        )

    @admin.display(description=_('Tài khoản'))
    def account_status(self, obj):
        if not obj.user_id:
            return format_html('<span class="scmd-employee-pill scmd-employee-pill-warning">{}</span>', _('Chưa liên kết'))
        if not obj.user.is_active:
            return format_html('<span class="scmd-employee-pill scmd-employee-pill-danger">{}</span>', _('Đã khóa'))
        return format_html('<span class="scmd-employee-pill scmd-employee-pill-success">{}</span>', _('Đang hoạt động'))

    @admin.display(description=_('Ảnh thẻ'))
    def image_preview_large(self, obj):
        if obj.anh_the:
            return format_html('<img src="{}" class="scmd-employee-preview" alt="{}" />', obj.anh_the.url, _('Ảnh thẻ nhân viên'))
        return "-"

    @admin.display(description=_('Trạng thái'), ordering='trang_thai_lam_viec')
    def status_badge(self, obj):
        css_map = {
            NhanVien.TrangThaiLamViec.CHINH_THUC: 'success',
            NhanVien.TrangThaiLamViec.THU_VIEC: 'info',
            NhanVien.TrangThaiLamViec.TAM_HOAN: 'warning',
            NhanVien.TrangThaiLamViec.NGHI_VIEC: 'neutral',
        }
        tone = css_map.get(obj.trang_thai_lam_viec, 'neutral')
        return format_html(
            '<span class="scmd-employee-pill scmd-employee-pill-{}">{}</span>',
            tone,
            obj.get_trang_thai_lam_viec_display(),
        )

    # --- ACTION HANDLERS ---
    @admin.action(description=_('Tải file mẫu nhập liệu'))
    def download_template_action(self, request, queryset): 
        return self.download_template_view(request)

    def _status_action_confirmation_context(self, request, queryset, *, action_name, target_status, title, warning):
        select_across = request.POST.get("select_across", "0")
        # Do not materialize every selected PK when Django Admin select-across is used.
        # Keep posted page IDs only and preserve select_across semantics for the final submit.
        selected_ids = request.POST.getlist(ACTION_CHECKBOX_NAME)
        preview = list(queryset.order_by("ma_nhan_vien")[:25])
        selected_count_value = _bounded_count(queryset)
        return {
            **self.admin_site.each_context(request),
            "title": title,
            "opts": self.model._meta,
            "queryset": preview,
            "selected_count_display": _bounded_display(selected_count_value),
            "preview_has_more": select_across == "1" or selected_count_value > len(preview),
            "selected_ids": selected_ids,
            "action_name": action_name,
            "target_status": target_status,
            "target_status_label": dict(NhanVien.TrangThaiLamViec.choices).get(target_status, target_status),
            "action_checkbox_name": ACTION_CHECKBOX_NAME,
            "select_across": select_across,
            "warning": warning,
            "changelist_url": reverse("admin:users_nhanvien_changelist"),
        }

    def _apply_staff_status_action(self, request, queryset, *, action_name, target_status, title, warning, success_message, message_level=messages.SUCCESS):
        """Confirm and apply sensitive staff-status bulk updates with per-object audit.

        This intentionally avoids ``queryset bulk update`` because staff status is
        operationally sensitive.  Each object is locked, minimally validated,
        saved through model ``save()``, and recorded in AuditLog.
        """
        if not self.has_change_permission(request):
            self.message_user(request, _("Bạn không có quyền cập nhật trạng thái nhân viên."), messages.ERROR)
            return None

        if request.POST.get("confirm_staff_status_action") != "1":
            return TemplateResponse(
                request,
                "admin/users/nhanvien/confirm_status_action.html",
                self._status_action_confirmation_context(
                    request,
                    queryset,
                    action_name=action_name,
                    target_status=target_status,
                    title=title,
                    warning=warning,
                ),
            )

        changed = 0
        skipped = 0
        with transaction.atomic():
            # The admin changelist queryset may carry nullable select_related() joins.
            # PostgreSQL rejects a plain FOR UPDATE across the nullable side of an
            # OUTER JOIN, so lock only the NhanVien rows while preserving the exact
            # filtered/admin-selected queryset.
            locked_qs = queryset.select_for_update(of=("self",)).order_by("pk")
            for staff in locked_qs:
                old_status = staff.trang_thai_lam_viec
                if old_status == target_status:
                    skipped += 1
                    continue

                staff.trang_thai_lam_viec = target_status
                staff.full_clean(
                    exclude=[field.name for field in staff._meta.fields if field.name != "trang_thai_lam_viec"],
                    validate_unique=False,
                )
                staff.save(update_fields=["trang_thai_lam_viec"])
                record_admin_audit_action(
                    request,
                    action=AuditLog.Action.UPDATE,
                    module="users",
                    model_name="NhanVien",
                    object_id=staff.pk,
                    note=f"Admin bulk status action: {action_name}",
                    changes={
                        "bulk_action": action_name,
                        "ma_nhan_vien": staff.ma_nhan_vien,
                        "ho_ten": staff.ho_ten,
                        "trang_thai_lam_viec": {"old": old_status, "new": target_status},
                    },
                )
                changed += 1

        if changed:
            self.message_user(request, str(success_message).format(changed=changed, skipped=skipped), message_level)
        else:
            self.message_user(request, _("Không có nhân viên nào cần đổi trạng thái."), messages.INFO)
        if skipped:
            self.message_user(request, _("Đã bỏ qua %(count)s nhân viên vì đã ở trạng thái đích.") % {"count": skipped}, messages.WARNING)
        return None

    @admin.action(description=_("Chuyển sang Chính thức — cần xác nhận"))
    def make_official(self, request, queryset):
        return self._apply_staff_status_action(
            request,
            queryset,
            action_name="make_official",
            target_status=NhanVien.TrangThaiLamViec.CHINH_THUC,
            title=_("Xác nhận chuyển nhân viên sang chính thức"),
            warning=_("Thao tác này thay đổi trạng thái làm việc của nhân viên. Hệ thống sẽ ghi AuditLog riêng cho từng hồ sơ."),
            success_message=_("Đã chuyển {changed} nhân viên sang chính thức."),
        )

    @admin.action(description=_("Đánh dấu Đã nghỉ việc — cần xác nhận"))
    def make_resigned(self, request, queryset):
        return self._apply_staff_status_action(
            request,
            queryset,
            action_name="make_resigned",
            target_status=NhanVien.TrangThaiLamViec.NGHI_VIEC,
            title=_("Xác nhận đánh dấu nhân viên đã nghỉ việc"),
            warning=_("Đây là dữ liệu nghiệp vụ nhạy cảm. Hãy kiểm tra danh sách trước khi xác nhận; hệ thống sẽ ghi AuditLog riêng cho từng hồ sơ."),
            success_message=_("Đã đánh dấu nghỉ việc cho {changed} nhân viên."),
            message_level=messages.WARNING,
        )

    # --- LOGIC XỬ LÝ LỖI INTEGRITY ---
    def save_formset(self, request, form, formset, change):
        """Kiểm soát inline nghiệp vụ HR và ghi audit khi đổi trạng thái HĐLĐ."""
=======
        queryset = NhanVien.objects.filter(pk__in=ids)
        return self.print_selected_profiles(request, queryset)

    # --- DISPLAY METHODS ---
    @admin.display(description=_('Avatar'))
    def avatar_thumb(self, obj):
        return format_html(
            '<img src="{}" style="width: 38px; height: 38px; border-radius: 50%; object-fit: cover; '
            'border: 1px solid #e2e8f0;" />', 
            obj.avatar_url
        )

    @admin.display(description=_('Ảnh thẻ'))
    def image_preview_large(self, obj):
        if obj.anh_the:
            return format_html('<img src="{}" style="max-height: 200px; border-radius: 8px;" />', obj.anh_the.url)
        return "-"

    @admin.display(description=_('Mã NV'), ordering='ma_nhan_vien')
    def ma_nhan_vien_bold(self, obj):
        return format_html('<b style="color: #1e293b;">{}</b>', obj.ma_nhan_vien)

    @admin.display(description=_('Trạng thái'), ordering='trang_thai_lam_viec')
    def status_badge(self, obj):
        colors = {
            'CHINHTHUC': ('#059669', '#ecfdf5'), 
            'THUVIEC': ('#2563eb', '#eff6ff'), 
            'TAMHOAN': ('#d97706', '#fffbeb'), 
            'NGHIVIEC': ('#4b5563', '#f3f4f6')
        }
        text_color, bg_color = colors.get(obj.trang_thai_lam_viec, ('#64748b', '#f8fafc'))
        return format_html(
            '<span style="background: {}; color: {}; padding: 4px 10px; border-radius: 8px; '
            'font-size: 10px; font-weight: 700; border: 1px solid currentColor;">{}</span>', 
            bg_color, text_color, obj.get_trang_thai_lam_viec_display()
        )

    @admin.display(description=_('Liên hệ'))
    def sdt_action(self, obj):
        s = str(obj.sdt_chinh)
        if not s or s == 'None': 
            return "-"
        return format_html(
            '<a href="tel:{}" style="color: #4f46e5; font-weight: 600; text-decoration: none;">'
            '<i class="fas fa-phone"></i> {}</a>', s, s
        )

    # --- ACTION HANDLERS ---
    @admin.action(description=_('⬇️ Tải file mẫu nhập liệu'))
    def download_template_action(self, request, queryset): 
        return self.download_template_view(request)

    @admin.action(description=_('✅ Chuyển sang Chính thức'))
    def make_official(self, request, queryset):
        queryset.update(trang_thai_lam_viec='CHINHTHUC')
        self.message_user(request, _("Đã cập nhật trạng thái nhân viên thành chính thức."))

    @admin.action(description=_('❌ Đánh dấu Đã nghỉ việc'))
    def make_resigned(self, request, queryset):
        queryset.update(trang_thai_lam_viec='NGHIVIEC')
        self.message_user(request, _("Đã đánh dấu trạng thái nghỉ việc cho các nhân sự đã chọn."), messages.WARNING)

    # --- LOGIC XỬ LÝ LỖI INTEGRITY ---
    def save_formset(self, request, form, formset, change):
        """Kiểm soát việc lưu inline để tránh lỗi IntegrityError khi thiếu ngày bắt đầu."""
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        if formset.model == LichSuCongTac:
            instances = formset.save(commit=False)
            for instance in instances:
                if not instance.pk and not instance.ngay_bat_dau:
                    instance.ngay_bat_dau = timezone.now().date()
                instance.save()
<<<<<<< HEAD
            for deleted in formset.deleted_objects:
                deleted.delete()
            formset.save_m2m()
            return

        if formset.model == HopDongLaoDong:
            instances = formset.save(commit=False)
            for deleted in formset.deleted_objects:
                deleted.delete()
            for instance in instances:
                old_status = None
                if instance.pk:
                    old_status = HopDongLaoDong.objects.filter(pk=instance.pk).values_list("trang_thai", flat=True).first()
                if instance.trang_thai in HopDongLaoDong.ACTIVE_CONTRACT_STATUSES and not instance.nguoi_duyet_id:
                    instance.nguoi_duyet = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
                    instance.ngay_duyet = timezone.now()
                instance.save()
                if old_status is not None and old_status != instance.trang_thai:
                    instance.record_status_transition(
                        actor=request.user,
                        old_status=old_status,
                        new_status=instance.trang_thai,
                        note="NhanVien admin inline labor contract status save",
                    )
            formset.save_m2m()
            return

        super().save_formset(request, form, formset, change)
=======
            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

    def download_template_view(self, request):
        """Xuất file Excel mẫu với định dạng chuẩn hệ thống HRM."""
        dataset = tablib.Dataset()
        dataset.headers = [
            _('Mã NV'), _('Họ và Tên'), _('Số điện thoại'), _('CCCD/CMND'), 
            _('Email'), _('Phòng ban'), _('Chức danh'), _('Ngày vào làm')
        ]
        dataset.append(['', 'Nguyễn Văn A', '0909123456', '079090000001', 'a.nguyen@email.com', 'Phòng Bảo vệ', 'Nhân viên', '2025-01-01'])
        
        response = HttpResponse(dataset.xlsx, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Mau_Nhap_Lieu_Nhan_Vien_SCMD.xlsx"'
        return response

    # --- PERMISSIONS & FIELDSETS ---
    def has_import_permission(self, request): 
        return is_hr_or_director(request.user)
    
    def has_export_permission(self, request): 
        return is_hr_or_director(request.user)

<<<<<<< HEAD
    def get_readonly_fields(self, request, obj=None):
        """Không hiển thị placeholder '-' của mã nhân viên khi đang thêm mới.

        Mã nhân viên được cấp sau khi lưu, nên đưa field này vào màn hình add làm
        người dùng tưởng có ô cần nhập hoặc dữ liệu bị thiếu. Ở màn hình sửa vẫn
        hiển thị mã và ảnh xem trước như trước đây.
        """
        if obj is None:
            return ()
        return ('ma_nhan_vien', 'image_preview_large')

    def get_inline_instances(self, request, obj=None):
        """Luôn giữ đủ inline hồ sơ phụ trên cả màn hình thêm mới và chỉnh sửa.

        Django Admin có thể lưu parent object trước rồi lưu formset inline trong
        cùng request, nên không cần ẩn Lịch sử công tác, Học vấn, Bằng cấp ở
        `/add/`. Việc ẩn các inline này làm mất chức năng người dùng đang cần
        và tạo cảm giác dữ liệu hồ sơ nhân sự bị thiếu.
        """
        return super().get_inline_instances(request, obj)

    def get_fieldsets(self, request, obj=None):
        """Tổ chức form theo luồng nhập liệu rõ ràng, tránh tab và row ghép gây rối.

        Không dùng tuple field trong các fieldsets chính vì Django Admin/Jazzmin
        render fieldBox khác nhau theo theme. Khi kết hợp với responsive CSS, row
        ghép dễ làm label và input lệch cột, đặc biệt ở màn hình thêm mới.
        """
        identity_fields = ['ho_ten', 'anh_the', 'ngay_sinh', 'gioi_tinh']
        if obj is not None:
            identity_fields = ['ma_nhan_vien', 'ho_ten', 'anh_the', 'image_preview_large', 'ngay_sinh', 'gioi_tinh']

        fieldsets = [
            (_("1. Thông tin định danh"), {
                'fields': tuple(identity_fields),
                'description': _("Nhập hồ sơ chính trước. Mã nhân viên được hệ thống cấp tự động sau khi lưu."),
                'classes': ('scmd-form-section', 'scmd-form-section-primary'),
            }),
            (_("2. Tổ chức và trạng thái"), {
                'fields': (
                    'phong_ban',
                    'chuc_danh',
                    'ngay_vao_lam',
                    'trang_thai_lam_viec',
                ),
                'classes': ('scmd-form-section',),
            }),
        ]

        if is_hr_or_director(request.user):
            fieldsets.extend([
                (_("3. Liên hệ và giấy tờ"), {
                    'fields': (
                        'sdt_chinh',
                        'email',
                        'so_cccd',
                        'dia_chi_thuong_tru',
                        'dia_chi_tam_tru',
                        'nguoi_lien_he_khan_cap',
                        'sdt_khan_cap',
                    ),
                    'description': _("Dữ liệu định danh và liên hệ là dữ liệu nhạy cảm; chỉ nhập khi có nguồn đối soát rõ."),
                    'classes': ('scmd-form-section',),
                }),
                (_("4. Hợp đồng, tài khoản và thanh toán"), {
                    'fields': (
                        'loai_hop_dong',
                        'user',
                        'so_tai_khoan',
                        'ngan_hang',
                        'chi_nhanh_ngan_hang',
                    ),
                    'description': _("Nhóm thông tin phục vụ quản trị tài khoản và đối soát tài chính. Kiểm tra kỹ trước khi lưu."),
                    'classes': ('scmd-form-section',),
                }),
            ])
        else:
            fieldsets.append(
                (_("3. Liên hệ"), {
                    'fields': ('email',),
                    'classes': ('scmd-form-section',),
                })
            )

        return fieldsets
    
    def get_queryset(self, request):
        """Admin staff list must use object-scope policy, not role-only RBAC."""
        scoped_ids = StaffVisibilityPolicy.visible_staff(request.user).values_list("pk", flat=True)
        return super().get_queryset(request).filter(pk__in=scoped_ids)

    def has_view_permission(self, request, obj=None):
        # Role-based permission enforcement (F-01 Residual)
        if not (super().has_view_permission(request, obj) or 
                request.user.has_perm('users.xem_ho_so_nhan_su')):
            return False
        if obj is None:
            return True
        return StaffVisibilityPolicy.visible_staff(request.user).filter(pk=obj.pk).exists()

    def has_change_permission(self, request, obj=None):
        # Role-based permission enforcement (F-01 Residual)
        if not (super().has_change_permission(request, obj) or 
                request.user.has_perm('users.cap_nhat_ho_so_nhan_su')):
            return False
        if obj is None:
            return True
        return StaffVisibilityPolicy.visible_staff(request.user).filter(pk=obj.pk).exists()

    def has_delete_permission(self, request, obj=None):
        # Personnel delete is intentionally not enabled through broad admin scope.
        if obj is None:
            return False
        return False
=======
    def get_fieldsets(self, request, obj=None):
        """Phân nhóm trường thông tin dựa trên quyền hạn của người dùng."""
        fields_list = [
            'ma_nhan_vien', 'image_preview_large', 'ho_ten', 'anh_the', 
            'ngay_sinh', 'gioi_tinh', 'phong_ban', 'chuc_danh', 
            'ngay_vao_lam', 'trang_thai_lam_viec'
        ]
        
        if is_hr_or_director(request.user):
            fields_list.extend([
                'loai_hop_dong', 'sdt_chinh', 'email', 'so_cccd', 
                'dia_chi_thuong_tru', 'dia_chi_tam_tru', 'nguoi_lien_he_khan_cap', 
                'sdt_khan_cap', 'so_tai_khoan', 'ngan_hang', 'chi_nhanh_ngan_hang', 'user'
            ])
        else: 
            fields_list.append('email')
            
        return [(_("HỒ SƠ NHÂN SỰ CHI TIẾT"), {'fields': fields_list, 'classes': ('wide', 'extrapretty')})]
    
    def get_queryset(self, request):
        """Giới hạn dữ liệu: Nhân viên chỉ thấy chính mình, HR thấy tất cả."""
        qs = super().get_queryset(request)
        if is_hr_or_director(request.user): 
            return qs 
        try: 
            return qs.filter(id=request.user.nhan_vien.id)
        except Exception: 
            return qs.none()
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34


# ==============================================================================
# 5. CUSTOM GROUP ADMIN (SECURITY PROTOCOL)
# ==============================================================================
admin.site.unregister(Group)

<<<<<<< HEAD
class PermissionGroupedChoiceField(forms.ModelMultipleChoiceField):
    ACTION_LABELS = {
        "view": _("Xem"),
        "add": _("Tạo"),
        "change": _("Cập nhật"),
        "delete": _("Xóa"),
    }

    def __init__(self, *args, model_labels=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_labels = model_labels or {}

    def label_from_instance(self, obj):
        action = obj.codename.split("_", 1)[0]
        action_label = self.ACTION_LABELS.get(action)
        model_label = self.model_labels.get((obj.content_type.app_label, obj.content_type.model))
        if action_label and model_label:
            return f"{action_label} {model_label}"
        return str(obj.name)


class CustomGroupForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        required=False,
        widget=forms.MultipleHiddenInput,
    )

    class Meta:
        model = Group
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].help_text = _("Đặt tên nhóm quyền ngắn gọn, phản ánh đúng vai trò nghiệp vụ.")
        self.section_fields = []
        self.section_metadata = []

        selected_permission_ids = set()
        if self.instance.pk:
            selected_permission_ids = set(self.instance.permissions.values_list("id", flat=True))

        for index, (section_title, section_config) in enumerate(self._build_permission_sections(), start=1):
            queryset = self._build_section_queryset(section_config["models"])
            if not queryset.exists():
                continue

            field_name = f"permission_section_{index}"
            self.fields[field_name] = PermissionGroupedChoiceField(
                queryset=queryset,
                required=False,
                widget=forms.CheckboxSelectMultiple,
                model_labels={
                    (app_label, model_name): str(model_label)
                    for app_label, model_name, model_label in section_config["models"]
                },
                label=section_title,
                help_text=section_config["description"],
            )
            self.fields[field_name].initial = [
                permission_id for permission_id in selected_permission_ids if queryset.filter(pk=permission_id).exists()
            ]
            self.section_fields.append(field_name)
            self.section_metadata.append(
                {
                    "field_name": field_name,
                    "title": section_title,
                    "description": section_config["description"],
                }
            )

        covered_permission_ids = set()
        for field_name in self.section_fields:
            covered_permission_ids.update(self.fields[field_name].queryset.values_list("id", flat=True))

        advanced_queryset = Permission.objects.exclude(id__in=covered_permission_ids).select_related("content_type").order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        )
        if advanced_queryset.exists():
            self.fields["advanced_permissions"] = PermissionGroupedChoiceField(
                queryset=advanced_queryset,
                required=False,
                widget=forms.CheckboxSelectMultiple,
                label=_("Quyền nâng cao"),
                help_text=_("Chỉ dùng khi cần cấp quyền ngoài ma trận chuẩn của SCMD."),
            )
            self.fields["advanced_permissions"].initial = [
                permission_id
                for permission_id in selected_permission_ids
                if advanced_queryset.filter(pk=permission_id).exists()
            ]
            self.section_fields.append("advanced_permissions")
            self.section_metadata.append(
                {
                    "field_name": "advanced_permissions",
                    "title": _("Quyền nâng cao"),
                    "description": _("Chỉ dùng khi cần cấp quyền ngoài ma trận chuẩn của SCMD."),
                }
            )

    def _build_permission_sections(self):
        sections = list(PERMISSION_GROUPS.items())
        sections.append(SYSTEM_PERMISSION_SECTION)
        return sections

    def _build_section_queryset(self, models_in_section):
        criteria = models.Q()
        for app_label, model_name, _ in models_in_section:
            criteria |= models.Q(content_type__app_label=app_label, content_type__model=model_name)
        return Permission.objects.filter(criteria).select_related("content_type").order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        )

    def clean_permissions(self):
        permission_ids = set()
        for field_name in self.section_fields:
            selected = self.cleaned_data.get(field_name)
            if selected is not None:
                permission_ids.update(selected.values_list("id", flat=True))
        return Permission.objects.filter(id__in=permission_ids)

    class Media:
        css = {"all": ("common/css/custom_admin.css", "css/admin_group_permissions.css")}
        js = ("js/admin_group_permissions.js",)
=======
class CustomGroupForm(forms.ModelForm):
    class Meta: 
        model = Group
        fields = '__all__'
    
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(), 
        widget=admin.widgets.FilteredSelectMultiple(_("Quyền hạn"), is_stacked=False), 
        required=False
    )
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

@admin.register(Group)
class CustomGroupAdmin(BaseGroupAdmin):
    form = CustomGroupForm
<<<<<<< HEAD
    change_form_template = "admin/auth/group/change_form.html"
    change_list_template = "admin/auth/group/change_list.html"
    list_display = (
        "name",
        "permission_matrix_summary",
        "linked_organization_units",
        "count_users",
        "quick_actions",
    )
    search_fields = ("name", "permissions__name", "permissions__codename")
    list_filter = ("permissions__content_type__app_label",)
    ordering = ("name",)
    list_per_page = 50

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                scmd_user_count=models.Count("user", distinct=True),
                scmd_permission_count=models.Count("permissions", distinct=True),
                scmd_department_count=models.Count("phongban", distinct=True),
                scmd_position_count=models.Count("chucdanh", distinct=True),
            )
        )

    @admin.display(description=_("Người dùng"), ordering="scmd_user_count")
    def count_users(self, obj):
        count = getattr(obj, "scmd_user_count", None)
        if count is None:
            count = obj.user_set.count()
        return format_html('<span class="scmd-admin-pill scmd-admin-pill-info">{} tài khoản</span>', count)

    @admin.display(description=_("Ma trận quyền"), ordering="scmd_permission_count")
    def permission_matrix_summary(self, obj):
        count = getattr(obj, "scmd_permission_count", None)
        if count is None:
            count = obj.permissions.count()
        tone = "danger" if count >= 80 else "warning" if count >= 35 else "success" if count else "muted"
        return format_html(
            '<span class="scmd-admin-pill scmd-admin-pill-{}">{} quyền</span>',
            tone,
            count,
        )

    @admin.display(description=_("Đang gắn với"))
    def linked_organization_units(self, obj):
        departments = getattr(obj, "scmd_department_count", None)
        positions = getattr(obj, "scmd_position_count", None)
        if departments is None:
            departments = obj.phongban_set.count()
        if positions is None:
            positions = obj.chucdanh_set.count()
        return format_html(
            '<span class="scmd-admin-muted">{} phòng ban · {} chức danh</span>',
            departments,
            positions,
        )

    @admin.display(description=_("Thao tác"))
    def quick_actions(self, obj):
        change_url = reverse("admin:auth_group_change", args=[obj.pk])
        return format_html(
            '<a class="button scmd-admin-mini-button" href="{}">Cấu hình quyền</a>',
            change_url,
        )

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)
        total_groups = _bounded_count(qs)
        orphan_groups = _bounded_count(qs.filter(scmd_user_count=0, scmd_department_count=0, scmd_position_count=0))
        high_risk_groups = _bounded_count(qs.filter(scmd_permission_count__gte=80))
        active_groups = _bounded_count(qs.filter(scmd_user_count__gt=0))
        extra_context = extra_context or {}
        extra_context.update(
            {
                "scmd_group_stats": {
                    "total_groups": total_groups,
                    "active_groups": active_groups,
                    "orphan_groups": orphan_groups,
                    "high_risk_groups": high_risk_groups,
                },
                "scmd_group_links": {
                    "add_group": reverse("admin:auth_group_add"),
                    "user_list": reverse("admin:auth_user_changelist"),
                    "department_list": reverse("admin:users_phongban_changelist"),
                    "position_list": reverse("admin:users_chucdanh_changelist"),
                },
            }
        )
        return super().changelist_view(request, extra_context=extra_context)

    def get_fieldsets(self, request, obj=None):
        return [
            (
                _("Thông tin nhóm quyền"),
                {
                    "fields": ("name",),
                    "description": _("Tên nhóm nên phản ánh đúng vai trò nghiệp vụ, ví dụ: Điều phối vận hành, Nhân sự khu vực, Kế toán trưởng."),
                },
            )
        ]

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        form = context.get("adminform").form
        permission_sections = []
        for section in getattr(form, "section_metadata", []):
            permission_sections.append(
                {
                    "title": section["title"],
                    "description": section["description"],
                    "field": form[section["field_name"]],
                }
            )

        context["permission_sections"] = permission_sections
        context["group_permissions_hidden_field"] = form["permissions"]
        return super().render_change_form(request, context, add, change, form_url, obj)
=======
    list_display = ('name', 'count_users')
    
    def count_users(self, obj): 
        return obj.user_set.count()
    count_users.short_description = _("Số lượng User")
    
    def get_form(self, request, obj=None, **kwargs):
        """Lọc danh sách quyền chỉ hiển thị các module của SCMD để tránh nhầm lẫn."""
        form = super().get_form(request, obj, **kwargs)
        apps_to_keep = [
            'operations', 'inspection', 'users', 'clients', 
            'inventory', 'accounting', 'reports', 'workflow', 'notifications'
        ]
        form.base_fields['permissions'].queryset = Permission.objects.filter(
            content_type__app_label__in=apps_to_keep
        ).select_related('content_type')
        return form
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
