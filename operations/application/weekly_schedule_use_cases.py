# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from django.utils import timezone
from rolepermissions.checkers import has_role

from clients.access_policies import SiteVisibilityPolicy
from clients.models import MucTieu
from operations.models import CaLamViec, PhanCongCaTruc, ViTriChot
from users.access_policies import StaffVisibilityPolicy
from users.models import NhanVien


class GetWeeklyScheduleUseCase:
    """
    Application Layer: Use Case lấy dữ liệu bảng xếp lịch tuần.
    Hỗ trợ phân quyền Site Scoping (BGĐ, Quản lý vùng, Đội trưởng, Nghiệp vụ được phân vùng).
    """

    @staticmethod
    def execute(user, tenant_id, date_str=None, muc_tieu_id=None):
        # 1. Xử lý logic thời gian (Tuần)
        start_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
        start_of_week = start_date - timedelta(days=start_date.weekday())
        days_of_week = [start_of_week + timedelta(days=i) for i in range(7)]

        # 2. Site Scoping: trang xem lịch có thể view-only cho BGĐ, còn user scoped
        # phải đi qua SiteVisibilityPolicy. Không trả global staff/site list cho user scoped.
        scoped_targets = MucTieu.objects.for_tenant(tenant_id)
        if user.is_superuser or has_role(user, 'ban_giam_doc'):
            managed_sites = scoped_targets
        else:
            managed_sites = SiteVisibilityPolicy.managed_sites(user, at_time=start_of_week)

        # 3. Lọc Vị trí chốt và Mục tiêu hiện tại
        current_muc_tieu = None
        vi_tris_qs = ViTriChot.objects.for_tenant(tenant_id).filter(muc_tieu__in=managed_sites)
        selected_site = None
        if muc_tieu_id:
            current_muc_tieu = managed_sites.filter(id=muc_tieu_id).first()
            selected_site = current_muc_tieu
            vi_tris_qs = vi_tris_qs.filter(muc_tieu_id=muc_tieu_id)
        else:
            # Giới hạn số lượng hiển thị mặc định để tối ưu hiệu năng UI.
            vi_tris_qs = vi_tris_qs.all()[:10]

        # Materialize once to avoid re-evaluating sliced QuerySets and to map by ID.
        vi_tris = list(vi_tris_qs)
        vi_tri_ids = [vt.id for vt in vi_tris]

        # 4. Truy vấn phân công và mapping vào schedule_map theo ID (O(1), không phụ thuộc object identity).
        phan_congs = (
            PhanCongCaTruc.objects.for_tenant(tenant_id)
            .filter(
                vi_tri_chot_id__in=vi_tri_ids,
                ngay_truc__range=[start_of_week, days_of_week[-1]],
            )
            .select_related('nhan_vien', 'vi_tri_chot', 'ca_lam_viec')
            .order_by('vi_tri_chot_id', 'ngay_truc', 'ca_lam_viec__gio_bat_dau')
        )

        schedule_map = {vt: {day: [] for day in days_of_week} for vt in vi_tris}
        schedule_map_by_id = {vt.id: schedule_map[vt] for vt in vi_tris}
        for pc in phan_congs:
            day_bucket = schedule_map_by_id.get(pc.vi_tri_chot_id)
            if day_bucket is not None:
                day_bucket[pc.ngay_truc].append(pc)

        if selected_site is not None:
            staff_queryset = StaffVisibilityPolicy.visible_staff_for_scheduling(user, selected_site, at_date=start_of_week)
        else:
            staff_queryset = StaffVisibilityPolicy.visible_staff(user, at_time=start_of_week).filter(
                trang_thai_lam_viec__in=[
                    NhanVien.TrangThaiLamViec.CHINH_THUC,
                    NhanVien.TrangThaiLamViec.THU_VIEC,
                ]
            )

        return {
            'days_of_week': days_of_week,
            'vi_tris': vi_tris,
            'schedule_map': schedule_map,
            'muc_tieus': managed_sites,
            'current_muc_tieu': current_muc_tieu,
            'ca_lam_viecs': CaLamViec.objects.for_tenant(tenant_id),
            'nhan_viens': staff_queryset,
            'prev_week': (start_of_week - timedelta(days=7)).strftime('%Y-%m-%d'),
            'next_week': (start_of_week + timedelta(days=7)).strftime('%Y-%m-%d'),
            'today': timezone.now().date(),
        }
