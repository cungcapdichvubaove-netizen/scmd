# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: users/admin.py
Author: Mr. Anh (CTO) & AI Assistant
Created Date: 2025-12-05
Updated Date: 2026-03-21
Description: Giao diện Admin Users (V6.0 - Enterprise HRM Optimized).
             FIXED: Khôi phục đầy đủ tính năng In Lý Lịch & Sửa lỗi IntegrityError.
             ENHANCEMENT: Tối ưu hóa hiệu suất truy vấn và chuyên nghiệp hóa UI.
"""

import logging
import tablib
from django.contrib import admin, messages
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django import forms
from django.db import models
from django.forms import TextInput, Select
from django.utils.html import format_html 
from django.http import HttpResponse
from django.urls import path
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

# --- IMPORT/EXPORT LIBRARIES ---
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

# IMPORT MODELS
from .models import (
    NhanVien, PhongBan, ChucDanh, LichSuCongTac, HocVan, BangCapChungChi, 
    CauHinhMaNhanVien
)

# Logger cho hệ thống SCMD
logger = logging.getLogger(__name__)

# Import config quyền
try: 
    from .permissions_config import PERMISSION_GROUPS
except ImportError: 
    PERMISSION_GROUPS = {}


# --- HELPER: KIỂM TRA QUYỀN TRUY CẬP ---
def is_hr_or_director(user):
    """Kiểm tra người dùng có thuộc nhóm nhân sự hoặc ban giám đốc không."""
    if user.is_superuser: 
        return True
    try:
        if not hasattr(user, 'nhan_vien') or not user.nhan_vien.chuc_danh or not user.nhan_vien.chuc_danh.nhom_quyen:
            return False
        group_name = user.nhan_vien.chuc_danh.nhom_quyen.name
        return group_name in ['BAN_GIAM_DOC', 'NHAN_SU', 'HANH_CHINH', 'ADMIN_HE_THONG']
    except Exception as e:
        logger.error(f"Lỗi kiểm tra quyền: {str(e)}")
        return False


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
    ngay_vao_lam = fields.Field(attribute='ngay_vao_lam', column_name=_('Ngày vào làm (YYYY-MM-DD)'))

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


# ==============================================================================
# 3. CẤU HÌNH DANH MỤC & INLINES
# ==============================================================================
@admin.register(CauHinhMaNhanVien)
class CauHinhMaNhanVienAdmin(admin.ModelAdmin):
    list_display = ('tien_to', 'do_dai_so', 'so_hien_tai')


@admin.register(ChucDanh)
class ChucDanhAdmin(admin.ModelAdmin):
    list_display = ('ten_chuc_danh', 'nhom_quyen')
    search_fields = ('ten_chuc_danh',)


@admin.register(PhongBan)
class PhongBanAdmin(admin.ModelAdmin):
    list_display = ('ten_phong_ban', 'nhom_quyen')
    search_fields = ('ten_phong_ban',)


class HocVanInline(admin.TabularInline):
    model = HocVan
    extra = 0
    verbose_name_plural = _("🎓 Quá trình Học vấn")
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'style': 'width: 250px;'})}
    }


class BangCapChungChiInline(admin.TabularInline):
    model = BangCapChungChi
    extra = 0
    verbose_name_plural = _("📜 Bằng cấp & Chứng chỉ")


class LichSuCongTacInline(admin.TabularInline):
    model = LichSuCongTac
    extra = 0
    fk_name = "nhan_vien"
    verbose_name_plural = _("🏢 Lịch sử Công tác")
    autocomplete_fields = ['muc_tieu']
    
    def get_readonly_fields(self, request, obj=None):
        return ['ngay_bat_dau'] if obj else []


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
    list_display = ('avatar_thumb', 'ma_nhan_vien_bold', 'ho_ten', 'chuc_danh', 'phong_ban', 'sdt_action', 'status_badge', 'print_btn')
    list_display_links = ('avatar_thumb', 'ma_nhan_vien_bold', 'ho_ten')
    list_filter = ('trang_thai_lam_viec', 'phong_ban', 'chuc_danh', BirthdayMonthFilter, ('ngay_vao_lam', admin.DateFieldListFilter))
    search_fields = ('ho_ten', 'ma_nhan_vien', 'sdt_chinh', 'so_cccd')
    list_select_related = ('phong_ban', 'chuc_danh', 'user')
    inlines = [LichSuCongTacInline, HocVanInline, BangCapChungChiInline]
    autocomplete_fields = ['phong_ban', 'chuc_danh']
    readonly_fields = ('ma_nhan_vien', 'image_preview_large')
    actions = ['make_official', 'make_resigned', 'download_template_action', 'print_selected_profiles']

    class Media: 
        css = { 'all': ('css/custom_admin.css',) }

    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'class': 'vTextField', 'style': 'width: 100%; max-width: 400px;'})},
        models.EmailField: {'widget': TextInput(attrs={'class': 'vTextField', 'style': 'width: 100%; max-width: 400px;'})},
        models.ForeignKey: {'widget': Select(attrs={'style': 'width: 100%; max-width: 405px;'})},
    }

    # --- CORE BUSINESS: IN LÝ LỊCH ---
    @admin.display(description=_('In hồ sơ'))
    def print_btn(self, obj):
        """Nút in lý lịch cá nhân nhanh trên list view."""
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background-color: #4f46e5; color: white; '
            'padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 600;">'
            '<i class="fas fa-print"></i> IN LÝ LỊCH</a>',
            f'./{obj.pk}/print-profile/'
        )

    def print_profile_view(self, request, object_id):
        """View xử lý in lý lịch chi tiết nhân viên."""
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, "admin/users/nhanvien/print_profile.html", {"nhan_vien": obj})

    @admin.action(description=_('🖨️ In lý lịch trích ngang đã chọn'))
    def print_selected_profiles(self, request, queryset):
        """Action in hàng loạt lý lịch nhân viên đã chọn."""
        return TemplateResponse(request, "admin/users/nhanvien/print_profile_bulk.html", {"queryset": queryset})

    def print_profiles_bulk_view(self, request):
        """Xử lý dữ liệu đầu vào cho in hàng loạt qua URL."""
        ids = request.GET.get('ids', '').split(',')
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
        if formset.model == LichSuCongTac:
            instances = formset.save(commit=False)
            for instance in instances:
                if not instance.pk and not instance.ngay_bat_dau:
                    instance.ngay_bat_dau = timezone.now().date()
                instance.save()
            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)

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


# ==============================================================================
# 5. CUSTOM GROUP ADMIN (SECURITY PROTOCOL)
# ==============================================================================
admin.site.unregister(Group)

class CustomGroupForm(forms.ModelForm):
    class Meta: 
        model = Group
        fields = '__all__'
    
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(), 
        widget=admin.widgets.FilteredSelectMultiple(_("Quyền hạn"), is_stacked=False), 
        required=False
    )

@admin.register(Group)
class CustomGroupAdmin(BaseGroupAdmin):
    form = CustomGroupForm
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