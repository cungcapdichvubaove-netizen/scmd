# -*- coding: utf-8 -*-
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from inspection.models import BienBanViPham
from operations.models import PhanCongCaTruc
from main.models import AuditLog

class CreateViolationUseCase:
    @staticmethod
    def execute(reporter_nv, form_data, files_data):
        """Logic lập biên bản vi phạm từ hiện trường kèm theo xác định mục tiêu tự động."""
        doi_tuong = form_data.get('doi_tuong_vi_pham')
        
        # Rule: Tìm ca trực của đối tượng trong ngày để xác định mục tiêu vi phạm
        ca = PhanCongCaTruc.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).filter(
            nhan_vien=doi_tuong, 
            ngay_truc=timezone.now().date()
        ).first()
        
        if not ca:
            return False, "Không tìm thấy ca trực của nhân viên này trong hôm nay!", None

        with transaction.atomic():
            violation = BienBanViPham(
                doi_tuong_vi_pham=doi_tuong,
                nguoi_lap=reporter_nv,
                muc_tieu=ca.vi_tri_chot.muc_tieu,
                ngay_vi_pham=timezone.now(),
                loai_loi=form_data.get('loai_loi'),
                hinh_thuc_xu_ly=form_data.get('hinh_thuc_xu_ly'),
                so_tien_phat=form_data.get('so_tien_phat', 0),
                mo_ta=form_data.get('mo_ta'),
                bang_chung_anh=files_data.get('bang_chung_anh')
            )
            violation.save()

            AuditLog.objects.create(
                user=getattr(reporter_nv, 'user', None),
                action=AuditLog.Action.CREATE,
                module="inspection",
                model_name="BienBanViPham",
                object_id=str(violation.pk),
                tenant_id=settings.SCMD_ORGANIZATION_ID,
                note=f"Lập biên bản {violation.ma_bien_ban} cho {doi_tuong.ho_ten} tại {ca.vi_tri_chot.muc_tieu.ten_muc_tieu}.",
                changes={
                    "loai_loi": violation.loai_loi,
                    "hinh_thuc": violation.hinh_thuc_xu_ly
                }
            )
            return True, "Lập biên bản thành công!", violation