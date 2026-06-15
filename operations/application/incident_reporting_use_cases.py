# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from main.models import AuditLog
from operations.models import BaoCaoSuCo, PhanCongCaTruc


class ReportIncidentUseCase:
    ACTIVE_SHIFT_REQUIRED_MESSAGE = "Chỉ có thể báo cáo sự cố khi đang trong ca trực đã check-in."
    ACTIVE_SHIFT_SITE_REQUIRED_MESSAGE = "Ca trực hiện tại chưa gắn với mục tiêu hợp lệ, không thể tạo báo cáo sự cố."
    REPORTER_REQUIRED_MESSAGE = "Tài khoản chưa liên kết hồ sơ nhân sự nên không thể gửi báo cáo sự cố."

    @staticmethod
    def resolve_active_shift_or_raise(reporter_nv):
        if reporter_nv is None:
            raise ValidationError(ReportIncidentUseCase.REPORTER_REQUIRED_MESSAGE)

        ca_truc = (
            PhanCongCaTruc.objects.for_tenant(settings.SCMD_ORGANIZATION_ID)
            .select_related("vi_tri_chot__muc_tieu")
            .filter(
                nhan_vien=reporter_nv,
                chamcong__thoi_gian_check_in__isnull=False,
                chamcong__thoi_gian_check_out__isnull=True,
            )
            .order_by("-ngay_truc", "-id")
            .first()
        )
        if ca_truc is None:
            raise ValidationError(ReportIncidentUseCase.ACTIVE_SHIFT_REQUIRED_MESSAGE)

        vi_tri_chot = getattr(ca_truc, "vi_tri_chot", None)
        muc_tieu = getattr(vi_tri_chot, "muc_tieu", None)
        if muc_tieu is None:
            raise ValidationError(ReportIncidentUseCase.ACTIVE_SHIFT_SITE_REQUIRED_MESSAGE)
        return ca_truc

    @staticmethod
    def execute(reporter_nv, form_data, files_data):
        """Ghi nhận báo cáo sự cố hiện trường và buộc gắn với ca trực đang active."""
        ca_truc = ReportIncidentUseCase.resolve_active_shift_or_raise(reporter_nv)
        muc_tieu = ca_truc.vi_tri_chot.muc_tieu

        with transaction.atomic():
            incident = BaoCaoSuCo(
                tieu_de=form_data.get("tieu_de") or f"Sự cố báo từ {reporter_nv.ho_ten}",
                nhan_vien_bao_cao=reporter_nv,
                muc_tieu=muc_tieu,
                ca_truc=ca_truc,
                muc_do=form_data.get("muc_do", "TB"),
                mo_ta_chi_tiet=form_data.get("mo_ta_chi_tiet"),
                hinh_anh_1=files_data.get("hinh_anh_1"),
                hinh_anh_2=files_data.get("hinh_anh_2"),
                file_ghi_am=files_data.get("file_ghi_am"),
                tenant_id=settings.SCMD_ORGANIZATION_ID,
            )
            incident.save()

            AuditLog.objects.create(
                user=getattr(reporter_nv, "user", None),
                action=AuditLog.Action.CREATE,
                module="operations",
                model_name="BaoCaoSuCo",
                object_id=str(incident.pk),
                tenant_id=settings.SCMD_ORGANIZATION_ID,
                note=f"Gửi báo cáo sự cố {incident.ma_su_co} từ hiện trường.",
                changes={"tieu_de": incident.tieu_de, "muc_do": incident.muc_do},
            )
            return incident
