# -*- coding: utf-8 -*-
"""Regression tests for SCMD Pro Operations UX Foundation.

These tests intentionally verify UI provider/query behavior without creating new
schema. The foundation must remain cumulative with StaffVisibilityPolicy and
Django Admin's native changelist mechanics.
"""

from __future__ import annotations

from datetime import date, time, timedelta
import re
from uuid import UUID
from unittest.mock import patch
from pathlib import Path

from django.contrib import admin as django_admin
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import Client
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from clients.models import HopDong, MucTieu
from inspection.models import LoaiTuanTra, LuotTuanTra
from main.models import AuditLog
from main.services.operations_ux import AdminOperationsUXProvider
from main.services.admin_global_search import ADMIN_GLOBAL_SEARCH_TARGETS, run_admin_global_search
from operations.models import CaLamViec, KiemTraQuanSo, PhanCongCaTruc, ViTriChot
from users.access_policies import StaffVisibilityPolicy
from users.admin import NhanVienAdmin, StaffOperationsSmartFilter
from users.models import LichSuCongTac, NhanVien
from config.jazzmin_conf import JAZZMIN_SETTINGS


ORG_ID = UUID("00000000-0000-0000-0000-000000000456")


@override_settings(SCMD_ORGANIZATION_ID=ORG_ID)
class OperationsUXFoundationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        User = get_user_model()
        self.commander_user = User.objects.create_user(username="ux-commander")
        self.guard_a_user = User.objects.create_user(username="ux-guard-a")
        self.guard_b_user = User.objects.create_user(username="ux-guard-b")
        self.hr_user = User.objects.create_user(username="ux-hr")
        self.ops_user = User.objects.create_user(username="ux-ops")
        self.superuser = User.objects.create_superuser(
            username="ux-root",
            email="ux-root@scmdpro.local",
            password="test-pass",
        )
        self.commander_user.is_staff = True
        self.commander_user.save(update_fields=["is_staff"])
        self.commander_user.user_permissions.add(Permission.objects.get(codename="view_muctieu"))

        Group.objects.get_or_create(name="Phòng Hành chính Nhân sự")[0].user_set.add(self.hr_user)
        Group.objects.get_or_create(name="Đội trưởng khu vực")[0].user_set.add(self.ops_user)

        self.commander = self._staff("UX101", "Chỉ huy UX", self.commander_user, sdt_chinh="0900000001")
        self.guard_a = self._staff("UX102", "Nhân viên UX A", self.guard_a_user, sdt_chinh="")
        self.guard_b = self._staff("UX103", "Nhân viên UX B", self.guard_b_user, sdt_chinh="")

        self.contract = HopDong.objects.create(
            so_hop_dong="HD-UX-001",
            ngay_ky=date(2026, 1, 1),
            ngay_hieu_luc=date(2026, 1, 1),
            ngay_het_han=timezone.localdate() + timedelta(days=10),
            gia_tri=0,
            trang_thai="HIEU_LUC",
        )
        self.site_a = self._site("Mục tiêu UX A", quan_ly_muc_tieu=self.commander)
        self.site_b = self._site("Mục tiêu UX B")
        self._assign_current_site(self.guard_a, self.site_a)
        self._assign_current_site(self.guard_b, self.site_b)

        self.post_a = ViTriChot.objects.create(muc_tieu=self.site_a, ten_vi_tri="Cổng chính UX")
        self.shift_type = CaLamViec.objects.create(
            ten_ca="Ca ngày UX",
            gio_bat_dau=time(8, 0),
            gio_ket_thuc=time(18, 0),
        )
        self.shift = PhanCongCaTruc.objects.create(
            vi_tri_chot=self.post_a,
            nhan_vien=self.guard_a,
            ca_lam_viec=self.shift_type,
            ngay_truc=timezone.localdate(),
        )
        KiemTraQuanSo.objects.create(ca_truc=self.shift, trang_thai="PENDING")

        self.patrol_route = LoaiTuanTra.objects.create(
            muc_tieu=self.site_a,
            ten_loai="Tuyến UX",
            thoi_gian_quy_dinh=30,
        )
        LuotTuanTra.objects.create(
            nhan_vien=self.guard_a,
            loai_tuan_tra=self.patrol_route,
            trang_thai="DANG_DI",
        )

    def _staff(self, code, name, user=None, **kwargs):
        if user is not None:
            try:
                staff = user.nhan_vien
            except NhanVien.DoesNotExist:
                staff = None
            if staff is not None:
                staff.tenant_id = ORG_ID
                staff.ma_nhan_vien = code
                staff.ho_ten = name
                for field, value in kwargs.items():
                    setattr(staff, field, value)
                staff.save()
                return staff

        return NhanVien.objects.create(
            tenant_id=ORG_ID,
            ma_nhan_vien=code,
            ho_ten=name,
            user=user,
            **kwargs,
        )

    def _site(self, name, **kwargs):
        return MucTieu.objects.create(
            hop_dong=self.contract,
            ten_muc_tieu=name,
            dia_chi=f"Địa chỉ {name}",
            **kwargs,
        )

    def _assign_current_site(self, staff, site):
        return LichSuCongTac.objects.create(
            nhan_vien=staff,
            muc_tieu=site,
            ngay_bat_dau=date(2026, 1, 1),
            ngay_ket_thuc=None,
        )

    def _request(self, user, path="/admin/users/nhanvien/", data=None):
        request = self.factory.get(path, data or {})
        request.user = user
        return request


    def test_v4_jazzmin_topbar_no_long_module_navigation(self):
        topmenu_links = JAZZMIN_SETTINGS.get("topmenu_links", [])

        self.assertEqual(topmenu_links, [])
        self.assertTrue(JAZZMIN_SETTINGS.get("show_sidebar"))
        self.assertEqual({"main"}, set(JAZZMIN_SETTINGS.get("custom_links", {})))

    def test_v18_jazzmin_custom_links_do_not_duplicate_model_changelists(self):
        """Jazzmin renders registered models natively; custom_links must not add them again."""
        forbidden_model_link_names = {
            "admin:inventory_vattu_changelist": "/admin/inventory/vattu/",
            "admin:inventory_phieuthuhoi_changelist": "/admin/inventory/phieuthuhoi/",
            "admin:inventory_bienbanmathongvattu_changelist": "/admin/inventory/bienbanmathongvattu/",
            "admin:accounting_bangluongthang_changelist": "/admin/accounting/bangluongthang/",
            "admin:accounting_tamungluong_changelist": "/admin/accounting/tamungluong/",
            "admin:accounting_khoankhautrunhanvien_changelist": "/admin/accounting/khoankhautrunhanvien/",
            "admin:reports_baocao_changelist": "/admin/reports/baocao/",
        }
        custom_links = JAZZMIN_SETTINGS.get("custom_links", {})
        flattened_urls = [
            link.get("url")
            for links in custom_links.values()
            for link in links
        ]

        for url_name, href in forbidden_model_link_names.items():
            self.assertNotIn(url_name, flattened_urls, f"Duplicate Jazzmin sidebar custom link for {href}")

        self.assertEqual(flattened_urls.count("admin:index"), 1)

    def test_v4_work_queue_source_errors_are_visible_to_technical_admin(self):
        with patch.object(AdminOperationsUXProvider, "_staff_counts", side_effect=RuntimeError("staff source failed")):
            context = AdminOperationsUXProvider.build(self.superuser)

        source_items = [item for item in context["work_queue_items"] if item["key"] == "source_unavailable:staff"]
        self.assertEqual(len(source_items), 1)
        self.assertEqual(source_items[0]["display_count"], "!")
        self.assertTrue(source_items[0]["source_warning"])

    def test_v4_work_queue_source_errors_are_not_silent_in_logs_but_hidden_from_non_technical_user(self):
        with patch.object(AdminOperationsUXProvider, "_staff_counts", side_effect=RuntimeError("staff source failed")):
            context = AdminOperationsUXProvider.build(self.hr_user)

        keys = {item["key"] for item in context["work_queue_items"]}
        self.assertNotIn("source_unavailable:staff", keys)
        self.assertIn("source_updating:staff", keys)

        soft_items = [item for item in context["work_queue_items"] if item["key"] == "source_updating:staff"]
        self.assertEqual(soft_items[0]["display_count"], "…")
        self.assertIn("đang cập nhật", soft_items[0]["label"])

    def test_v4_device_token_filter_wording_is_operational_not_digital_twin(self):
        self.guard_a.fcm_token = "ux-device-token"
        self.guard_a.save(update_fields=["fcm_token"])
        request = self._request(self.commander_user)
        model_admin = NhanVienAdmin(NhanVien, AdminSite())
        smart_filter = StaffOperationsSmartFilter(request, {}, NhanVien, model_admin)

        labels = [str(label) for _, label in smart_filter.lookups(request, model_admin)]
        self.assertIn("Có thiết bị nhận thông báo", labels)
        self.assertNotIn("Có định danh thiết bị", labels)

    def test_v4_bulk_bar_is_collapsed_until_rows_are_selected(self):
        template = Path("templates/admin/includes/scmd_bulk_action_bar.html").read_text(encoding="utf-8")

        self.assertIn("is-idle", template)
        self.assertIn("data-scmd-bulk-expanded", template)
        self.assertIn("hidden", template)

    def test_role_alias_matching_uses_dashboard_router_group_aliases(self):
        hr_context = AdminOperationsUXProvider.build(self.hr_user)
        ops_context = AdminOperationsUXProvider.build(self.ops_user)

        self.assertIn("scope:hr", hr_context["role_keys"])
        self.assertEqual(hr_context["home_header"]["title"], "Bàn làm việc nhân sự")
        self.assertIn("scope:operations", ops_context["role_keys"])
        self.assertEqual(ops_context["home_header"]["title"], "Bàn làm việc điều hành")

    def test_work_queue_includes_existing_alive_patrol_contract_and_attendance_sources(self):
        context = AdminOperationsUXProvider.build(self.superuser)
        keys = {item["key"] for item in context["work_queue_items"]}

        self.assertIn("alive_pending", keys)
        self.assertIn("shifts_without_checkin", keys)
        self.assertIn("open_patrols", keys)
        self.assertIn("contracts_expiring", keys)

    def test_nhanvien_admin_queryset_uses_staff_visibility_scope(self):
        request = self._request(self.commander_user)
        model_admin = NhanVienAdmin(NhanVien, AdminSite())

        admin_ids = set(model_admin.get_queryset(request).values_list("pk", flat=True))
        policy_ids = set(StaffVisibilityPolicy.visible_staff(self.commander_user).values_list("pk", flat=True))

        self.assertEqual(admin_ids, policy_ids)
        self.assertIn(self.guard_a.pk, admin_ids)
        self.assertNotIn(self.guard_b.pk, admin_ids)

    def test_staff_smart_filter_never_widens_scoped_queryset(self):
        request = self._request(self.commander_user, data={"staff_ops": "missing_phone"})
        model_admin = NhanVienAdmin(NhanVien, AdminSite())
        scoped_qs = model_admin.get_queryset(request)
        smart_filter = StaffOperationsSmartFilter(request, request.GET.copy(), NhanVien, model_admin)

        filtered_ids = set(smart_filter.queryset(request, scoped_qs).values_list("pk", flat=True))
        scoped_ids = set(scoped_qs.values_list("pk", flat=True))

        self.assertLessEqual(filtered_ids, scoped_ids)
        self.assertIn(self.guard_a.pk, filtered_ids)
        self.assertNotIn(self.guard_b.pk, filtered_ids)

    def test_smart_filter_urls_reset_pagination_and_preserve_other_query_params(self):
        request = self._request(self.commander_user, data={"p": "3", "q": "UX", "staff_ops": "missing_phone"})
        model_admin = NhanVienAdmin(NhanVien, AdminSite())
        url = model_admin.smart_filter_url(request, "missing_email")

        self.assertIn("q=UX", url)
        self.assertIn("staff_ops=missing_email", url)
        self.assertNotIn("p=3", url)

    def test_v5_disables_external_google_fonts_cdn(self):
        self.assertFalse(JAZZMIN_SETTINGS.get("use_google_fonts_cdn"))

    def test_v5_global_search_covers_core_operations_entities(self):
        search_models = {target.model_path for target in ADMIN_GLOBAL_SEARCH_TARGETS}

        self.assertIn("users.NhanVien", search_models)
        self.assertIn("clients.MucTieu", search_models)
        self.assertIn("clients.HopDong", search_models)
        self.assertIn("clients.KhachHangTiemNang", search_models)
        self.assertIn("operations.BaoCaoSuCo", search_models)
        self.assertIn("inventory.VatTu", search_models)

    def test_v5_admin_localization_js_is_static_and_does_not_rewrite_date_values(self):
        base_template = Path("templates/admin/base_site.html").read_text(encoding="utf-8")
        localization_js = Path("static/common/js/admin_localization.js").read_text(encoding="utf-8")

        self.assertIn("common/js/admin_localization.js", base_template)
        self.assertLess(base_template.count("<script>"), 2)
        self.assertNotIn("const TEXT_MAP", base_template)
        self.assertIn("const TEXT_MAP", localization_js)
        self.assertNotIn("input.value = `${match", localization_js)
        self.assertIn("không tự động đổi dữ liệu", localization_js)

    def test_v5_auth_change_lists_do_not_define_screen_local_styles(self):
        user_template = Path("templates/admin/auth/user/change_list.html").read_text(encoding="utf-8")
        group_template = Path("templates/admin/auth/group/change_list.html").read_text(encoding="utf-8")
        css = Path("static/common/css/operations_ux.css").read_text(encoding="utf-8")

        self.assertNotIn("<style>", user_template)
        self.assertNotIn("<style>", group_template)
        self.assertIn(".scmd-user-console", css)
        self.assertIn(".scmd-group-console", css)

    def test_v6_work_queue_links_open_pre_filtered_admin_lists(self):
        context = AdminOperationsUXProvider.build(self.superuser)
        urls_by_key = {item["key"]: item["url"] for item in context["work_queue_items"]}

        self.assertIn("alive_status=pending", urls_by_key.get("alive_pending", ""))
        self.assertIn("assignment_quality=missing_checkin_today", urls_by_key.get("shifts_without_checkin", ""))
        self.assertIn("ops=active", urls_by_key.get("open_patrols", ""))
        self.assertIn("contract_quality=expiring_30", urls_by_key.get("contracts_expiring", ""))

    def test_v6_employee_list_is_table_first_and_limits_context_blocks(self):
        template = Path("templates/admin/users/nhanvien/change_list.html").read_text(encoding="utf-8")
        css = Path("static/common/css/operations_ux.css").read_text(encoding="utf-8")

        self.assertIn("scmd-ops-decision-strip", template)
        self.assertIn("scmd-ops-table-tools", template)
        self.assertIn("scmd-ops-workqueue--minimal", css)
        self.assertIn("#result_list thead th", css)

    def test_v6_bulk_bar_has_non_mutating_productivity_helpers(self):
        template = Path("templates/admin/includes/scmd_bulk_action_bar.html").read_text(encoding="utf-8")
        js = Path("static/common/js/operations_ux.js").read_text(encoding="utf-8")

        self.assertIn("copy-filter", template)
        self.assertIn("copyCurrentFilterUrl", js)
        self.assertIn("Sao chép URL bộ lọc", js)

    def test_v6_operations_css_removes_important_overrides(self):
        css = Path("static/common/css/operations_ux.css").read_text(encoding="utf-8")
        self.assertNotIn("!important", css)

    def test_v6_admin_console_metrics_uses_bounded_counts(self):
        admin_console = Path("main/templatetags/admin_console.py").read_text(encoding="utf-8")

        self.assertIn("def _bounded_count", admin_console)
        self.assertIn("task_alert_count = _bounded_count(task_alerts)", admin_console)
        self.assertIn('"audit_log_total": _bounded_count(AuditLog.objects.all())', admin_console)
        self.assertIn('"task_alerts": _bounded_count(TaskResult.objects.exclude(status="SUCCESS"))', admin_console)

    def test_v6_workspace_links_are_role_ordered_and_filter_ready(self):
        from main.templatetags.admin_console import operations_workspace_sections

        hr_sections = operations_workspace_sections(self.hr_user)
        ops_sections = operations_workspace_sections(self.ops_user)

        self.assertEqual(hr_sections[1]["title"], "Nhân sự")
        self.assertEqual(ops_sections[1]["title"], "Khách hàng & mục tiêu")
        first_links = [link["url"] for link in ops_sections[0]["links"]]
        self.assertTrue(any("assignment_quality=today" in url for url in first_links))
        self.assertTrue(any("incident_ops=open" in url for url in first_links))

    def test_v7_custom_admin_css_is_lightweight_and_token_driven(self):
        css = Path("static/common/css/custom_admin.css").read_text(encoding="utf-8")

        self.assertLess(css.count("\n"), 1400)
        self.assertLess(css.count("!important"), 100)
        self.assertNotIn("gradient", css.lower())
        self.assertIn("admin_components.css", css)

    def test_v7_operational_changelists_do_not_embed_local_style_blocks(self):
        offenders = []
        for template_path in Path("templates/admin").rglob("change_list.html"):
            text = template_path.read_text(encoding="utf-8")
            if "<style" in text.lower():
                offenders.append(str(template_path))

        self.assertEqual(offenders, [])

    def test_v7_bulk_bar_supports_real_non_mutating_print_and_export_actions(self):
        template = Path("templates/admin/includes/scmd_bulk_action_bar.html").read_text(encoding="utf-8")
        js = Path("static/common/js/operations_ux.js").read_text(encoding="utf-8")

        self.assertIn("data-scmd-print-selected-url", template)
        self.assertIn("print-selected", template)
        self.assertIn("printSelectedProfiles", js)
        self.assertIn("ids=", js)
        self.assertIn("Xuất danh sách theo filter", Path("users/admin.py").read_text(encoding="utf-8"))

    def test_v9_work_queue_export_actions_only_point_to_real_child_endpoints(self):
        context = AdminOperationsUXProvider.build(self.superuser)
        actions = [
            action.get("url", "")
            for item in context["work_queue_items"]
            for action in item.get("next_actions", [])
        ]

        self.assertTrue(actions)
        self.assertFalse(any("export" + "=1" in url for url in actions))
        self.assertTrue(any("/export/" in url or "/export-csv/" in url for url in actions))

    def test_v8_staff_status_actions_require_confirmation_and_audit_per_object(self):
        admin_source = Path("users/admin.py").read_text(encoding="utf-8")

        self.assertNotIn("queryset.update(trang_thai_lam_viec", admin_source)
        self.assertIn("confirm_staff_status_action", admin_source)
        self.assertIn("record_admin_audit_action", admin_source)
        self.assertIn("select_for_update", admin_source)

    def test_v8_make_official_confirmation_then_execution_records_audit(self):
        model_admin = NhanVienAdmin(NhanVien, AdminSite())
        queryset = NhanVien.objects.filter(pk=self.guard_a.pk)

        preview_request = self.factory.post(
            "/admin/users/nhanvien/",
            {"action": "make_official", ACTION_CHECKBOX_NAME: [str(self.guard_a.pk)]},
        )
        preview_request.user = self.superuser
        preview_response = model_admin.make_official(preview_request, queryset)

        self.assertEqual(preview_response.template_name, "admin/users/nhanvien/confirm_status_action.html")

        execute_request = self.factory.post(
            "/admin/users/nhanvien/",
            {
                "action": "make_official",
                "confirm_staff_status_action": "1",
                ACTION_CHECKBOX_NAME: [str(self.guard_a.pk)],
            },
        )
        execute_request.user = self.superuser
        with patch.object(model_admin, "message_user"):
            result = model_admin.make_official(execute_request, queryset)

        self.assertIsNone(result)
        self.guard_a.refresh_from_db()
        self.assertEqual(self.guard_a.trang_thai_lam_viec, NhanVien.TrangThaiLamViec.CHINH_THUC)
        audit = AuditLog.objects.get(module="users", model_name="NhanVien", object_id=str(self.guard_a.pk))
        self.assertEqual(audit.action, AuditLog.Action.UPDATE)
        self.assertEqual(audit.changes["bulk_action"], "make_official")
        self.assertEqual(audit.changes["trang_thai_lam_viec"]["new"], NhanVien.TrangThaiLamViec.CHINH_THUC)

    def test_v8_inventory_admin_changelists_use_shared_design_system(self):
        offenders = []
        for template_path in Path("inventory/templates/admin/inventory").rglob("change_list.html"):
            text = template_path.read_text(encoding="utf-8").lower()
            if "<style" in text or "style=" in text:
                offenders.append(str(template_path))

        self.assertEqual(offenders, [])
        css = Path("static/common/css/admin_components.css").read_text(encoding="utf-8")
        self.assertIn(".scmd-inventory-hero", css)
        self.assertIn(".scmd-inventory-grid", css)

    def test_v8_operations_css_uses_semantic_tokens_not_screen_specific_hex_palette(self):
        css = Path("static/common/css/operations_ux.css").read_text(encoding="utf-8")

        hex_tokens = re.findall(r"#[0-9a-fA-F]{3,8}\b", css)
        self.assertEqual(hex_tokens, [])
        self.assertIn("var(--scmd-brand)", css)
        self.assertIn("var(--scmd-warning)", css)

    def test_v8_users_admin_stats_use_bounded_count_for_remaining_summary_counts(self):
        admin_source = Path("users/admin.py").read_text(encoding="utf-8")

        self.assertIn("def _bounded_count", admin_source)
        self.assertIn("stats['missing_site'] = _bounded_count", admin_source)
        self.assertIn("total_positions = _bounded_count(qs)", admin_source)
        self.assertIn("total_groups = _bounded_count(qs)", admin_source)



    def test_v9_account_user_bulk_actions_are_confirmed_and_audited(self):
        admin_source = Path("users/admin.py").read_text(encoding="utf-8")

        self.assertIn("confirm_account_action", admin_source)
        self.assertIn("_apply_account_flag_action", admin_source)
        self.assertIn("record_admin_audit_action", admin_source)
        self.assertNotIn("queryset.update(is_active", admin_source)
        self.assertNotIn("queryset.update(is_staff", admin_source)

    def test_v9_sensitive_admin_actions_do_not_use_queryset_update_directly(self):
        checked_files = [
            Path("users/admin.py"),
            Path("operations/admin.py"),
            Path("clients/admin.py"),
            Path("accounting/admin.py"),
        ]
        offenders = []
        for path in checked_files:
            text = path.read_text(encoding="utf-8")
            for line_no, line in enumerate(text.splitlines(), start=1):
                stripped = line.strip()
                if "queryset.update(" in stripped and not stripped.startswith(("#", "\"\"\"", "'")):
                    offenders.append(f"{path}:{line_no}:{stripped}")
        self.assertEqual(offenders, [])

    def test_v9_accounting_changelists_use_shared_css(self):
        offenders = []
        for template_path in Path("accounting/templates/accounting/admin").glob("*change_list.html"):
            text = template_path.read_text(encoding="utf-8").lower()
            if "<style" in text or "style=" in text:
                offenders.append(str(template_path))
        self.assertEqual(offenders, [])

    def test_v9_staff_status_confirmation_does_not_materialize_select_across(self):
        admin_source = Path("users/admin.py").read_text(encoding="utf-8")

        self.assertIn('select_across == "1"', admin_source)
        self.assertNotIn("or [str(pk) for pk in queryset.values_list", admin_source)
        self.assertIn("selected_count_display", admin_source)

    def test_v10_topbar_disables_jazzmin_multi_model_search(self):
        self.assertEqual(JAZZMIN_SETTINGS.get("search_model"), [])
        css = Path("static/common/css/custom_admin.css").read_text(encoding="utf-8")
        js = Path("static/common/js/admin_localization.js").read_text(encoding="utf-8")

        self.assertIn("#jazzy-navbar > form.form-inline", css)
        self.assertIn("normalizeTopbarSearch", js)

    def test_v10_employee_changelist_is_compact_table_first(self):
        template = Path("templates/admin/users/nhanvien/change_list.html").read_text(encoding="utf-8")
        css = Path("static/common/css/operations_ux.css").read_text(encoding="utf-8")

        self.assertIn("scmd-compact-list-page", template)
        self.assertIn("scmd-ops-table-tools--compact", template)
        self.assertLess(template.find("scmd-ops-table-tools--compact"), template.find("block.super"))
        self.assertIn("topbar must stay quiet", Path("static/common/css/custom_admin.css").read_text(encoding="utf-8"))
        self.assertIn("min-height: 34px", css)
        self.assertIn("height: 52px", Path("static/common/css/custom_admin.css").read_text(encoding="utf-8"))

    def test_v10_shift_changelist_removes_hero_and_uses_compact_kpi_strip(self):
        template = Path("templates/admin/operations/calamviec/change_list.html").read_text(encoding="utf-8")

        self.assertIn("scmd-shift-console--compact", template)
        self.assertIn("scmd-shift-grid--compact", template)
        self.assertIn("scmd-shift-subtitle", template)
        self.assertNotIn("Chưa có hôm nay", template)
        self.assertIn('<details class="scmd-shift-note scmd-shift-note--compact">', template)

    def test_v10_smart_filters_have_more_filters_disclosure(self):
        template = Path("templates/admin/includes/scmd_smart_filter_bar.html").read_text(encoding="utf-8")

        self.assertIn("Bộ lọc thêm", template)
        self.assertIn("forloop.counter <= 5", template)

    def test_v11_topbar_has_one_unified_global_search_without_jazzmin_multi_widget(self):
        self.assertEqual(JAZZMIN_SETTINGS.get("search_model"), [])

        base_template = Path("templates/admin/base_site.html").read_text(encoding="utf-8")
        js = Path("static/common/js/admin_localization.js").read_text(encoding="utf-8")
        css = Path("static/common/css/custom_admin.css").read_text(encoding="utf-8")
        urls = Path("config/urls.py").read_text(encoding="utf-8")

        self.assertIn("admin_global_search", base_template)
        self.assertIn("ensureUnifiedGlobalSearch", js)
        self.assertIn("data-scmd-global-search", js)
        self.assertIn(".scmd-global-search", css)
        self.assertIn('path("admin/search/", admin_global_search_view', urls)

    def test_v11_unified_global_search_finds_staff_site_and_contract(self):
        request = self._request(self.superuser, path="/admin/search/", data={"q": "UX"})
        context = run_admin_global_search(request, "UX")
        labels = {group["label"] for group in context["groups"]}

        self.assertIn("Nhân viên", labels)
        self.assertIn("Mục tiêu", labels)
        self.assertIn("Hợp đồng", labels)
        self.assertGreaterEqual(context["total_count"], 3)

    def test_v11_accounting_payroll_approval_template_has_no_inline_style_block(self):
        template = Path("accounting/templates/accounting/admin/bang_luong_trinh_ky.html").read_text(encoding="utf-8").lower()

        self.assertNotIn("<style", template)
        self.assertIn("common/css/payroll_report.css", template)

    def test_v11_admin_result_table_headers_do_not_use_sticky_offset(self):
        css = Path("static/common/css/operations_ux.css").read_text(encoding="utf-8")
        shell_css = Path("static/common/css/custom_admin.css").read_text(encoding="utf-8")

        self.assertIn("body.change-list #result_list thead th", css)
        self.assertIn("body.change-list #result_list thead th", shell_css)
        self.assertIn("position: static", css)
        self.assertIn("position: static", shell_css)
        self.assertNotIn("top: var(--scmd-sticky-table-top, 56px);", css)
        self.assertNotIn("top: 96px", css)
        self.assertNotIn("top: 132px", css)

    def test_v12_global_search_uses_registered_admin_queryset_for_non_staff_targets(self):
        request = self._request(self.commander_user, path="/admin/search/", data={"q": "Mục tiêu UX"})
        context = run_admin_global_search(request, "Mục tiêu UX")
        site_groups = [group for group in context["groups"] if group["label"] == "Mục tiêu"]

        self.assertEqual(len(site_groups), 1)
        result_titles = {item["title"] for item in site_groups[0]["items"]}
        self.assertIn("Mục tiêu UX A", result_titles)
        self.assertNotIn("Mục tiêu UX B", result_titles)

    def test_v12_global_search_service_does_not_use_default_manager_all_for_search_scope(self):
        source = Path("main/services/admin_global_search.py").read_text(encoding="utf-8")

        self.assertIn("model_admin.get_queryset(request)", source)
        self.assertIn("_scoped_admin_queryset", source)
        self.assertNotIn("model._default_manager.all()", source)

    def test_v12_global_search_view_is_in_interface_layer_not_service_layer(self):
        service_source = Path("main/services/admin_global_search.py").read_text(encoding="utf-8")
        view_source = Path("main/admin_views.py").read_text(encoding="utf-8")
        urls_source = Path("config/urls.py").read_text(encoding="utf-8")

        self.assertNotIn("def admin_global_search_view", service_source)
        self.assertNotIn("render(request", service_source)
        self.assertIn("def admin_global_search_view", view_source)
        self.assertIn("run_admin_global_search", view_source)
        self.assertIn("from main.admin_views import admin_global_search_view", urls_source)

    def test_v12_global_search_source_failures_are_reported_to_technical_admin(self):
        model_admin = django_admin.site._registry[MucTieu]
        request = self._request(self.superuser, path="/admin/search/", data={"q": "UX"})

        with patch.object(model_admin, "get_queryset", side_effect=RuntimeError("site source failed")):
            context = run_admin_global_search(request, "UX")

        self.assertTrue(context["has_failed_sources"])
        self.assertTrue(context["show_failed_sources"])
        self.assertIn("Mục tiêu", context["failed_sources"])

    def test_v12_topbar_legacy_search_guard_is_narrow_not_all_form_inline(self):
        js = Path("static/common/js/admin_localization.js").read_text(encoding="utf-8")

        self.assertIn("data-scmd-hidden-legacy-search", js)
        self.assertIn("hasJazzminModelControl", js)
        self.assertNotIn('navbar.querySelectorAll("form.form-inline"));', js)



    def test_v13_dashboard_modules_use_brand_tokens_and_no_inline_styles(self):
        module_css = Path("static/common/css/dashboard_modules.css").read_text(encoding="utf-8")
        for template_path in [
            "inspection/templates/inspection/dashboard.html",
            "accounting/templates/accounting/dashboard.html",
            "clients/templates/clients/dashboard_crm.html",
        ]:
            template = Path(template_path).read_text(encoding="utf-8")
            self.assertNotIn("<style", template)
            self.assertIn("common/css/dashboard_modules.css", template)

        self.assertIn("var(--scmd-", module_css)
        self.assertNotIn("--idt-", module_css)
        self.assertNotIn("--acct-", module_css)
        self.assertNotRegex(module_css, r"#[0-9A-Fa-f]{3,8}")
        self.assertNotIn("linear-gradient", module_css)
        self.assertNotIn("radial-gradient", module_css)

    def test_v13_brand_system_has_dark_mode_tokens_and_eyebrow_classes(self):
        css = Path("static/common/css/brand_system.css").read_text(encoding="utf-8")

        self.assertIn("@media (prefers-color-scheme: dark)", css)
        self.assertIn('[data-theme="dark"]', css)
        self.assertIn(".scmd-eyebrow-l1", css)
        self.assertIn(".scmd-eyebrow-l2", css)

    def test_v13_no_fake_950_font_weight_in_operational_templates(self):
        checked_paths = [
            "inspection/templates/inspection/dashboard.html",
            "accounting/templates/accounting/dashboard.html",
            "clients/templates/clients/dashboard_crm.html",
            "static/common/css/dashboard_modules.css",
        ]
        for path in checked_paths:
            self.assertNotIn("font-weight: " + "950", Path(path).read_text(encoding="utf-8"))

    def test_v13_notification_badge_is_bound_to_context_not_hardcoded_dot(self):
        base_template = Path("templates/base.html").read_text(encoding="utf-8")
        context_processors = Path("config/settings.py").read_text(encoding="utf-8")
        context_source = Path("main/context_processors.py").read_text(encoding="utf-8")

        self.assertIn("notification_count", base_template)
        self.assertIn("{% if notification_count %}", base_template)
        self.assertNotIn("right-1.5 top-1.5 h-2 w-2 rounded-full border border-white bg-red-500", base_template)
        self.assertIn("main.context_processors.notification_context", context_processors)
        self.assertIn("ThongBao.objects.filter", context_source)

    def test_v13_sidebar_and_mobile_accessibility_hardening(self):
        sidebar = Path("templates/partials/sidebar_menu_items.html").read_text(encoding="utf-8")
        mobile = Path("mobile/templates/base.html").read_text(encoding="utf-8")
        mobile_css = Path("static/common/css/mobile_shell.css").read_text(encoding="utf-8")

        self.assertIn("fa-clipboard-check", sidebar)
        self.assertNotIn("fa-user-secret", sidebar)
        self.assertNotIn("request.path", sidebar)
        self.assertNotIn("body { \\n            font-family: 'Inter'", mobile)
        self.assertIn(".scmd-mobile-shell button", mobile_css)
        self.assertIn(".scmd-mobile-tap-target", mobile_css)

    def test_v13_login_captcha_has_visible_answer_label(self):
        login_template = Path("main/templates/main/login.html").read_text(encoding="utf-8")
        login_css = Path("static/common/css/login.css").read_text(encoding="utf-8")

        self.assertIn('class="login-captcha-answer-label"', login_template)
        self.assertIn("Đáp án", login_template)
        self.assertIn(".login-captcha-answer-label", login_css)

    def test_v14_main_dashboard_uses_eyebrow_tokens_not_inline_tracking_utilities(self):
        dashboard_template = Path("dashboard/templates/dashboard/main.html").read_text(encoding="utf-8")
        brand_css = Path("static/common/css/brand_system.css").read_text(encoding="utf-8")

        self.assertIn(".scmd-eyebrow-l1", brand_css)
        self.assertIn(".scmd-eyebrow-l2", brand_css)
        self.assertIn("scmd-eyebrow-l1", dashboard_template)
        self.assertIn("scmd-eyebrow-l2", dashboard_template)
        self.assertNotIn("tracking-[0.18em]", dashboard_template)
        self.assertNotIn("tracking-[0.16em]", dashboard_template)
        self.assertNotIn("tracking-[0.12em]", dashboard_template)

    def test_v14_payroll_print_template_has_no_bootstrap_dependency_classes(self):
        payroll_template = Path("accounting/templates/accounting/admin/bang_luong_trinh_ky.html").read_text(encoding="utf-8")
        payroll_css = Path("static/common/css/payroll_report.css").read_text(encoding="utf-8")

        forbidden_classes = ["btn btn-dark", "btn btn-outline", "d-flex", "justify-content", "col-md-4", "row mb-", "card mb-", "fw-bold"]
        for pattern in forbidden_classes:
            self.assertNotIn(pattern, payroll_template)
        self.assertIn("scmd-payroll-btn--primary", payroll_template)
        self.assertIn("scmd-payroll-grid", payroll_css)
        self.assertNotIn(".btn-dark", payroll_css)
        self.assertNotIn(".d-flex", payroll_css)
        self.assertNotIn(".col-md-4", payroll_css)

    def test_v14_dashboard_module_css_is_tokenized_and_not_broad_recursive(self):
        module_css = Path("static/common/css/dashboard_modules.css").read_text(encoding="utf-8")

        self.assertNotRegex(module_css, r"#[0-9A-Fa-f]{3,8}")
        self.assertNotIn("background: #", module_css)
        self.assertNotIn("color: #", module_css)
        self.assertNotIn(".inspection-dashboard *", module_css)
        self.assertNotIn(".acct-dashboard *", module_css)
        self.assertNotIn(".scmd-module-card *", module_css)
        self.assertNotIn("font-weight:850", module_css)
        self.assertIn("--scmd-", module_css)

    def test_v14_dashboard_kpi_state_microcopy_distinguishes_loading_empty_error(self):
        module_css = Path("static/common/css/dashboard_modules.css").read_text(encoding="utf-8")
        inspection = Path("inspection/templates/inspection/dashboard.html").read_text(encoding="utf-8")
        accounting = Path("accounting/templates/accounting/dashboard.html").read_text(encoding="utf-8")
        crm = Path("clients/templates/clients/dashboard_crm.html").read_text(encoding="utf-8")

        for token in ["--loading", "--empty", "--error"]:
            self.assertIn(token, module_css)
        self.assertIn("card.is_loading", inspection)
        self.assertIn("card.error_message", inspection)
        self.assertIn("card.is_loading", accounting)
        self.assertIn("card.error_message", accounting)
        self.assertIn("expiring_contracts_loading", crm)
        self.assertIn("expiring_contracts_error", crm)

    def test_v14_hr_dashboard_table_is_mobile_safe(self):
        hr_template = Path("users/templates/users/dashboard_hr.html").read_text(encoding="utf-8")

        self.assertIn("overflow-x:auto", hr_template)
        self.assertIn("table-layout:fixed", hr_template)
        self.assertIn("min-width:720px", hr_template)

    def test_v14_admin_global_search_results_are_announced_to_screen_readers(self):
        search_template = Path("templates/admin/global_search.html").read_text(encoding="utf-8")

        self.assertIn('aria-live="polite"', search_template)
        self.assertIn('aria-atomic="false"', search_template)

class CompactOperationsAdminSystemV15StaticTests(TestCase):
    def test_v15_mobile_base_is_scmd_shell_not_django_tailwind_demo(self):
        canonical_mobile_base = Path("mobile/templates/mobile/base.html").read_text(encoding="utf-8")
        compatibility_shim = Path("mobile/templates/base.html").read_text(encoding="utf-8")
        mobile_css = Path("static/common/css/mobile_shell.css").read_text(encoding="utf-8")
        mobile_js = Path("static/common/js/mobile_shell.js").read_text(encoding="utf-8")

        self.assertNotIn("Django Tailwind", canonical_mobile_base)
        self.assertNotIn("Django + Tailwind", canonical_mobile_base)
        self.assertNotIn("Hello from daisyUi", canonical_mobile_base)
        self.assertIn("SCMD Pro", canonical_mobile_base)
        self.assertIn("scmd-mobile-header", canonical_mobile_base)
        self.assertIn("scmd-mobile-bottom-nav", canonical_mobile_base)
        self.assertIn("data-mobile-online-label", canonical_mobile_base)
        self.assertIn("{% block extra_css %}", canonical_mobile_base)
        self.assertIn("{% block extra_js %}", canonical_mobile_base)
        self.assertIn("navigator.onLine", mobile_js)
        self.assertIn(".scmd-mobile-shell", mobile_css)

        self.assertEqual('{% extends "mobile/base.html" %}', compatibility_shim.strip())
        self.assertNotIn('{% extends "../base.html" %}', compatibility_shim)
        self.assertNotIn("scmd-mobile-header", compatibility_shim)

    def test_v16_mobile_templates_extend_canonical_shell(self):
        for template_path in [
            "inspection/templates/inspection/mobile/tuan_tra_list.html",
            "inspection/templates/inspection/mobile/tuan_tra.html",
            "inspection/templates/inspection/mobile/lap_bien_ban.html",
            "inspection/templates/inspection/mobile/chi_tiet_luot_tuan_tra.html",
            "accounting/templates/accounting/phieu_luong_list.html",
            "users/templates/users/mobile/salary_detail.html",
            "users/templates/users/mobile/profile.html",
            "users/templates/users/mobile/password_change.html",
            "operations/templates/operations/mobile/lich_truc.html",
            "operations/templates/operations/mobile/lich_su_cham_cong.html",
            "operations/templates/operations/mobile/de_xuat_list.html",
            "operations/templates/operations/mobile/dashboard.html",
            "operations/templates/operations/mobile/bao_cao_su_co.html",
            "operations/templates/operations/mobile/de_xuat_detail.html",
            "operations/templates/operations/mobile/bao_cao_de_xuat.html",
            "operations/templates/operations/mobile/de_xuat_form.html",
            "operations/templates/operations/mobile/login.html",
        ]:
            body = Path(template_path).read_text(encoding="utf-8")
            self.assertIn('{% extends "mobile/base.html" %}', body)
            self.assertNotIn('operations/mobile/base_mobile_revamped.html', body)

        legacy_shell = Path("operations/templates/operations/mobile/base_mobile_revamped.html").read_text(encoding="utf-8")
        canonical_shell = Path("mobile/templates/mobile/base.html").read_text(encoding="utf-8")
        compatibility_shim = Path("mobile/templates/base.html").read_text(encoding="utf-8")

        self.assertIn('{% extends "mobile/base.html" %}', legacy_shell)
        self.assertEqual('{% extends "mobile/base.html" %}', compatibility_shim.strip())
        self.assertNotIn('{% extends "../base.html" %}', canonical_shell)
        self.assertNotIn('{% extends "../base.html" %}', compatibility_shim)
        legacy_mobile_shell = Path("operations/templates/operations/mobile/base_mobile.html").read_text(encoding="utf-8")
        login_template = Path("operations/templates/operations/mobile/login.html").read_text(encoding="utf-8")

        self.assertIn('{% extends "mobile/base.html" %}', legacy_mobile_shell)
        self.assertIn('{% extends "mobile/base.html" %}', login_template)
        self.assertNotIn("<!DOCTYPE html>", legacy_mobile_shell)
        self.assertNotIn("operations/mobile/base_mobile.html", login_template)
        self.assertIn("scmd-mobile-header", canonical_shell)

    def test_v16_only_one_real_mobile_shell_exists(self):
        real_mobile_shells = []

        for path in Path(".").glob("**/templates/**/*.html"):
            path_text = path.as_posix()
            if "/mobile/" not in path_text and not path_text.startswith("mobile/templates/"):
                continue

            body = path.read_text(encoding="utf-8")
            if "<!DOCTYPE html>" in body:
                real_mobile_shells.append(path_text)

        self.assertEqual(
            ["mobile/templates/mobile/base.html"],
            sorted(real_mobile_shells),
        )

    def test_v16_sidebar_active_state_and_shell_urls_are_reverse_safe(self):
        sidebar = Path("templates/partials/sidebar_menu_items.html").read_text(encoding="utf-8")
        base_template = Path("templates/base.html").read_text(encoding="utf-8")
        mobile_base = Path("mobile/templates/mobile/base.html").read_text(encoding="utf-8")

        self.assertNotIn("request.path", sidebar)
        self.assertIn("request.resolver_match.app_name", sidebar)
        service_worker = Path("templates/sw.js").read_text(encoding="utf-8")
        backup_restore_view = Path("backup_restore/views.py").read_text(encoding="utf-8")
        payroll_listener = Path("static/js/operations_payroll_listener.js").read_text(encoding="utf-8")
        collected_payroll_listener = Path("staticfiles/js/operations_payroll_listener.js").read_text(encoding="utf-8")

        self.assertIn("{% url 'admin:password_change' %}", base_template)
        self.assertIn("{% url 'admin:index' %}", base_template)
        self.assertIn("{% url 'admin_logout_fix' %}", base_template)
        self.assertIn("{% url 'admin:index' %}", service_worker)
        self.assertNotIn('"/admin/"', service_worker)
        self.assertIn("BACKUP_RESTORE_DISABLED_MESSAGE", backup_restore_view)
        self.assertIn("HttpResponseForbidden", backup_restore_view)
        self.assertNotIn('redirect("/admin/logout/")', backup_restore_view)
        self.assertIn("vendor/htmx/htmx.min.js", mobile_base)
        self.assertIn("data-scmd-accounting-dashboard-url", mobile_base)
        self.assertIn("data-scmd-accounting-dashboard-url", payroll_listener)
        self.assertIn("data-scmd-accounting-dashboard-url", collected_payroll_listener)
        self.assertNotIn('/accounting/dashboard/', payroll_listener)
        self.assertNotIn('/accounting/dashboard/', collected_payroll_listener)

    def test_v16_admin_submit_line_is_project_override_and_sticky_ready(self):
        submit_line_template = Path("templates/admin/submit_line.html").read_text(encoding="utf-8")
        shell_css = Path("static/common/css/custom_admin.css").read_text(encoding="utf-8")

        self.assertIn('class="submit-row scmd-submit-row"', submit_line_template)
        self.assertIn("body.change-form #jazzy-actions .scmd-submit-row", shell_css)
        self.assertIn("body.change-form #jazzy-actions .submit-row", shell_css)
        self.assertIn("top: calc(52px + 18vh);", shell_css)

    def test_v15_inventory_dashboard_uses_shared_dashboard_css_not_inline_style(self):
        template = Path("inventory/templates/inventory/dashboard_kho.html").read_text(encoding="utf-8")
        module_css = Path("static/common/css/dashboard_modules.css").read_text(encoding="utf-8")

        self.assertNotIn("<style>", template)
        self.assertIn("common/css/dashboard_modules.css", template)
        self.assertIn("scmd-dashboard--inventory", template)
        self.assertIn(".inv-dashboard", module_css)
        self.assertNotRegex(module_css, r"#[0-9A-Fa-f]{3,8}")
        self.assertNotIn("background: #", module_css)
        self.assertNotIn("color: #", module_css)
        self.assertNotIn("linear-gradient", module_css)
        self.assertNotIn("radial-gradient", module_css)

    def test_v15_dashboard_state_and_skeleton_system_exists(self):
        module_css = Path("static/common/css/dashboard_modules.css").read_text(encoding="utf-8")
        accounting = Path("accounting/templates/accounting/dashboard.html").read_text(encoding="utf-8")
        inventory = Path("inventory/templates/inventory/dashboard_kho.html").read_text(encoding="utf-8")

        for cls in [
            ".scmd-skeleton",
            ".scmd-skeleton-line",
            ".scmd-skeleton-title",
            ".scmd-skeleton-card",
            ".scmd-skeleton-table-row",
            ".scmd-skeleton-avatar",
            ".scmd-state--empty",
            ".scmd-state--error",
            ".scmd-state--loading",
        ]:
            self.assertIn(cls, module_css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", module_css)
        self.assertIn("scmd-state scmd-state--empty", accounting)
        self.assertIn("scmd-state scmd-state--empty", inventory)

    def test_v15_ui_spec_has_breakpoint_contract(self):
        spec = Path("UI_SYSTEM_REFACTOR_SPEC.md").read_text(encoding="utf-8")

        for token in ["xs", "sm", "md", "lg", "xl", "2xl", "0–479px", "640–767px", ">=1280px"]:
            self.assertIn(token, spec)
        self.assertIn("Do not introduce ad-hoc breakpoints", spec)
        self.assertIn(".scmd-skeleton-table-row", spec)

    def test_v19_admin_homepage_stays_within_query_budget_without_advanced_tree(self):
        user = get_user_model().objects.create_superuser(
            username="v19-admin-budget",
            email="v19-admin-budget@scmd.local",
            password="test-pass",
        )
        client = Client()
        client.force_login(user)

        with CaptureQueriesContext(connection) as captured:
            response = client.get(reverse("admin:index"))
            _ = response.content

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(captured),
            65,
            f"/admin/ query budget regressed: {len(captured)} queries",
        )

    def test_v19_global_search_does_not_query_sources_without_search_term(self):
        user = get_user_model().objects.create_superuser(
            username="v19-admin-search",
            email="v19-admin-search@scmd.local",
            password="test-pass",
        )
        request = RequestFactory().get("/admin/search/", {"q": ""})
        request.user = user

        with patch("main.services.admin_global_search._scoped_admin_queryset") as scoped_queryset:
            context = run_admin_global_search(request, "")

        self.assertEqual(context["total_count"], 0)
        self.assertEqual(context["groups"], [])
        scoped_queryset.assert_not_called()

    def test_v19_admin_homepage_lazy_loads_advanced_tree(self):
        template = Path("templates/admin/index.html").read_text(encoding="utf-8")

        self.assertIn("?advanced=1#advanced-admin", template)
        self.assertIn("{% if request.GET.advanced != '1' %}", template)
        self.assertIn("{% group_admin_apps app_list as grouped_app_list %}", template)
