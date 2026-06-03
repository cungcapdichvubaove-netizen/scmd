# -*- coding: utf-8 -*-
"""
Access policies for operations module.
"""

from django.core.exceptions import PermissionDenied

from operations.models import PhanCongCaTruc


class ShiftAccessPolicy:
    """
    SSOT for validating whether a user can operate on a shift attendance entrypoint.
    """

    @staticmethod
    def get_accessible_shift_for_attendance(user, shift_id, tenant_id):
        queryset = PhanCongCaTruc.objects.for_tenant(tenant_id).select_related(
            "nhan_vien",
            "vi_tri_chot",
            "vi_tri_chot__muc_tieu",
            "ca_lam_viec",
        )

        if user.is_superuser:
            pass
        elif hasattr(user, "nhan_vien"):
            queryset = queryset.filter(nhan_vien=user.nhan_vien)
        else:
            raise PermissionDenied("Khong co quyen thao tac ca truc nay.")

        shift = queryset.filter(id=shift_id).first()
        if not shift:
            raise PermissionDenied("Khong tim thay ca truc hop le.")

        return shift
