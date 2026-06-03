# -*- coding: utf-8 -*-
"""
Application Layer: Dashboard Use Cases.

Standardized layered monolith edition:
- Interface calls use cases from this module.
- Use cases orchestrate ORM queries and permission-aware filtering.
"""

import logging

from django.utils import timezone
from rolepermissions.checkers import has_role

from clients.models import MucTieu
from operations.models import BaoCaoSuCo, ChamCong, PhanCongCaTruc

logger = logging.getLogger(__name__)


class GetWarRoomDashboardUseCase:
    @staticmethod
    def execute(user, tenant_id, target_date, muc_tieu_id=None):
        if not hasattr(user, "nhan_vien"):
            return {}

        nv = user.nhan_vien
        allowed_target_ids = []

        if has_role(user, ["ban_giam_doc", "ke_toan"]):
            allowed_target_ids = list(MucTieu.objects.values_list("id", flat=True))
        elif has_role(user, "quan_ly_vung"):
            allowed_target_ids = list(
                MucTieu.objects.filter(quan_ly_vung=nv).values_list("id", flat=True)
            )
        elif has_role(user, "doi_truong"):
            allowed_target_ids = list(
                MucTieu.objects.filter(quan_ly_muc_tieu=nv).values_list(
                    "id", flat=True
                )
            )

        final_target_ids = allowed_target_ids
        if muc_tieu_id:
            try:
                requested_id = int(muc_tieu_id)
            except (ValueError, TypeError):
                requested_id = None

            if requested_id is not None:
                if requested_id in allowed_target_ids:
                    final_target_ids = [requested_id]
                else:
                    logger.warning(
                        "SECURITY: user %s attempted to access unauthorized site %s",
                        user.id,
                        requested_id,
                    )
                    return {"error": "Unauthorized site access"}

        active_ccs_qs = ChamCong.objects.for_tenant(tenant_id).filter(
            thoi_gian_check_in__date=target_date,
            thoi_gian_check_out__isnull=True,
            ca_truc__vi_tri_chot__muc_tieu_id__in=final_target_ids,
        ).select_related("ca_truc__nhan_vien", "ca_truc__vi_tri_chot__muc_tieu")

        total_shifts_qs = PhanCongCaTruc.objects.for_tenant(tenant_id).filter(
            ngay_truc=target_date,
            vi_tri_chot__muc_tieu_id__in=final_target_ids,
        )

        incidents_qs = BaoCaoSuCo.objects.for_tenant(tenant_id).filter(
            trang_thai__in=["CHO_XU_LY", "DANG_XU_LY", "CHO_DEN_BU"],
            muc_tieu_id__in=final_target_ids,
        ).select_related("muc_tieu", "nhan_vien_bao_cao").order_by("-created_at")

        active_ccs_list = list(active_ccs_qs)
        total_shifts = total_shifts_qs.count()
        active_count = len(active_ccs_list)

        markers_data = []
        for cc in active_ccs_list:
            point = cc.location_check_in
            if point:
                nhan_vien = cc.ca_truc.nhan_vien
                markers_data.append(
                    {
                        "id": nhan_vien.id,
                        "name": nhan_vien.ho_ten,
                        "lat": float(point.y),
                        "lng": float(point.x),
                        "target": cc.ca_truc.vi_tri_chot.muc_tieu.ten_muc_tieu,
                        "status": "active",
                    }
                )

        incidents_data = []
        for incident in incidents_qs:
            if incident.muc_tieu and incident.muc_tieu.vi_do is not None:
                incidents_data.append(
                    {
                        "id": incident.id,
                        "title": incident.tieu_de,
                        "level": incident.muc_do,
                        "lat": float(incident.muc_tieu.vi_do),
                        "lng": float(incident.muc_tieu.kinh_do),
                    }
                )

        last_cc = (
            ChamCong.objects.for_tenant(tenant_id)
            .filter(thoi_gian_check_in__date=target_date)
            .select_related("ca_truc__nhan_vien", "ca_truc__vi_tri_chot__muc_tieu")
            .order_by("-thoi_gian_check_in")
            .first()
        )

        last_activity = None
        if last_cc:
            last_activity = {
                "user": last_cc.ca_truc.nhan_vien.ho_ten,
                "action": "Check-in",
                "time": timezone.localtime(last_cc.thoi_gian_check_in).strftime(
                    "%H:%M"
                ),
            }

        return {
            "stats": {
                "tong_ca": total_shifts,
                "da_checkin": active_count,
                "vang_mat": total_shifts - active_count,
            },
            "markers": markers_data,
            "incidents": incidents_data,
            "last_activity": last_activity,
        }
