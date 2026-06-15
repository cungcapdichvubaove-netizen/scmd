# -*- coding: utf-8 -*-
"""
Application Layer: scheduling use cases.
"""

from datetime import datetime, timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from main.models import AuditLog
from operations.access_policies import ShiftAssignmentPolicy
from operations.models import CaLamViec, PhanCongCaTruc, ViTriChot
from clients.models import MucTieu
from users.models import NhanVien

class ManageShiftAssignmentUseCase:
    """
    Application Layer: Unified Use Case for creating, updating, and deleting 
    shift assignments with mandatory audit logging.
    """
    @staticmethod
    def execute(
        *,
        action,  # 'SAVE' or 'DELETE'
        actor_user,
        reason=None,
        delete_old_id=None,
        nhan_vien_id=None,
        vi_tri_id=None,
        ca_id=None,
        ngay_truc=None,
        tenant_id=None,
    ):
        tenant_id = tenant_id or settings.SCMD_ORGANIZATION_ID
        
        # Determine day
        day_obj = None
        if ngay_truc:
            day_obj = (
                datetime.strptime(ngay_truc, "%Y-%m-%d").date()
                if isinstance(ngay_truc, str)
                else ngay_truc
            )

        now = timezone.now()

        old_pc = None
        if delete_old_id:
            old_pc = PhanCongCaTruc.objects.for_tenant(tenant_id).select_related(
                "nhan_vien",
                "vi_tri_chot__muc_tieu",
                "ca_lam_viec",
            ).filter(id=delete_old_id).first()

        target_staff = None
        target_site = None
        if action == "SAVE" and nhan_vien_id:
            target_staff = NhanVien.objects.for_tenant(tenant_id).filter(pk=nhan_vien_id).first()
            target_site = MucTieu.objects.for_tenant(tenant_id).filter(
                cac_vi_tri_chot__pk=vi_tri_id
            ).distinct().first()

        if action == "DELETE":
            ShiftAssignmentPolicy.can_delete_shift(actor_user, old_pc).raise_if_denied()
        elif action == "SAVE":
            if old_pc is not None:
                ShiftAssignmentPolicy.can_update_shift(actor_user, old_pc).raise_if_denied()
            if nhan_vien_id:
                ShiftAssignmentPolicy.can_assign_shift(
                    actor_user,
                    target_staff,
                    target_site,
                    day_obj,
                ).raise_if_denied()

        with transaction.atomic():
            # Storage for context if deletion happens
            context_pc = None

            # 1. Handle deletion (Standalone or as part of update)
            if delete_old_id:
                if old_pc:
                    # Rule 8.2 & 8.3: Bắt buộc lý do cho ca trực đã gần hoặc đang diễn ra (Ngưỡng 2h)
                    start_dt = timezone.make_aware(datetime.combine(old_pc.ngay_truc, old_pc.ca_lam_viec.gio_bat_dau))
                    if start_dt <= now + timedelta(hours=2) and not reason:
                        raise ValidationError("Bắt buộc nhập lý do điều chỉnh cho ca trực đang hoặc sắp diễn ra.")

                    context_pc = old_pc
                    audit_changes = {
                        "nhan_vien": old_pc.nhan_vien.ho_ten,
                        "ngay_truc": str(old_pc.ngay_truc),
                        "ca": old_pc.ca_lam_viec.ten_ca,
                        "vi_tri": old_pc.vi_tri_chot.ten_vi_tri
                    }
                    
                    old_pc.delete()
                    
                    # Audit deletion
                    AuditLog.objects.create(
                        user=actor_user,
                        action=AuditLog.Action.DELETE if action == 'DELETE' else AuditLog.Action.UPDATE,
                        module='operations',
                        model_name='PhanCongCaTruc',
                        object_id=str(delete_old_id),
                        tenant_id=tenant_id,
                        note=f"{'Xóa' if action == 'DELETE' else 'Gỡ bỏ'} ca trực: {audit_changes['nhan_vien']}. Lý do: {reason or 'N/A'}",
                        changes={**audit_changes, "reason": reason},
                        status='SUCCESS'
                    )

            # 2. Handle creation (for SAVE action)
            if action == 'SAVE' and nhan_vien_id:
                # Kiểm tra tính nhạy cảm của ca mới gán
                target_ca = CaLamViec.objects.for_tenant(tenant_id).get(id=ca_id)
                target_start_dt = timezone.make_aware(datetime.combine(day_obj, target_ca.gio_bat_dau))
                if target_start_dt <= now + timedelta(hours=2) and not reason:
                    raise ValidationError("Bắt buộc nhập lý do khi gán bổ sung ca trực đang/sắp diễn ra.")

                new_pc = PhanCongCaTruc.objects.create(
                    nhan_vien_id=nhan_vien_id,
                    vi_tri_chot_id=vi_tri_id,
                    ca_lam_viec_id=ca_id,
                    ngay_truc=day_obj,
                    tenant_id=tenant_id
                )
                
                # Audit creation
                AuditLog.objects.create(
                    user=actor_user,
                    action=AuditLog.Action.UPDATE if delete_old_id else AuditLog.Action.CREATE,
                    module='operations',
                    model_name='PhanCongCaTruc',
                    object_id=str(new_pc.id),
                    tenant_id=tenant_id,
                    note=f"{'Cập nhật' if delete_old_id else 'Tạo mới'} ca trực. Lý do: {reason or 'N/A'}",
                    changes={
                        "nhan_vien": new_pc.nhan_vien.ho_ten,
                        "ngay_truc": str(day_obj),
                        "ca": new_pc.ca_lam_viec.ten_ca,
                        "vi_tri": new_pc.vi_tri_chot.ten_vi_tri,
                        "reason": reason
                    },
                    status='SUCCESS'
                )

        # 3. Build return context for cell re-rendering
        f_vt_id = vi_tri_id or (context_pc.vi_tri_chot_id if context_pc else None)
        f_ca_id = ca_id or (context_pc.ca_lam_viec_id if context_pc else None)
        f_day = day_obj or (context_pc.ngay_truc if context_pc else None)

        return {
            "phan_congs": PhanCongCaTruc.objects.for_tenant(tenant_id).filter(
                vi_tri_chot_id=f_vt_id,
                ca_lam_viec_id=f_ca_id,
                ngay_truc=f_day,
            ) if f_vt_id and f_ca_id and f_day else [],
            "vi_tri": ViTriChot.objects.for_tenant(tenant_id).filter(id=f_vt_id).first() if f_vt_id else None,
            "ca": CaLamViec.objects.for_tenant(tenant_id).filter(id=f_ca_id).first() if f_ca_id else None,
            "day": f_day,
        }
