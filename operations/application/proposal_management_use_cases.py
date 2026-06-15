# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import transaction

from main.models import AuditLog
from operations.models import BaoCaoDeXuat


class CreateFieldProposalUseCase:
    @staticmethod
    def execute(nhan_vien, form_data):
        """Gửi đề xuất nghiệp vụ từ mobile về văn phòng."""
        with transaction.atomic():
            proposal = BaoCaoDeXuat(
                nhan_vien=nhan_vien,
                loai_de_xuat=form_data.get("loai_de_xuat") or BaoCaoDeXuat.LoaiDeXuat.KHAC,
                tieu_de=form_data.get("tieu_de"),
                noi_dung=form_data.get("noi_dung"),
                hinh_anh=form_data.get("hinh_anh"),
                tenant_id=settings.SCMD_ORGANIZATION_ID,
            )
            proposal.save()

            AuditLog.objects.create(
                user=getattr(nhan_vien, "user", None),
                action=AuditLog.Action.CREATE,
                module="operations",
                model_name="BaoCaoDeXuat",
                object_id=str(proposal.pk),
                tenant_id=settings.SCMD_ORGANIZATION_ID,
                note=f"Gửi đề xuất mới từ mobile: {proposal.tieu_de}.",
                changes={
                    "tieu_de": proposal.tieu_de,
                    "loai_de_xuat": proposal.loai_de_xuat,
                    "co_hinh_anh": bool(proposal.hinh_anh),
                },
            )
            return proposal
