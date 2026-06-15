# -*- coding: utf-8 -*-
"""
Service layer for monthly payroll orchestration.
"""

import logging

from django.conf import settings
from django.db import transaction

<<<<<<< HEAD
from accounting.domain.payroll_rate import PayrollRateConfigurationError
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
from accounting.application.payroll_use_cases import (
    AuditPayrollUseCase,
    CalculatePayrollUseCase,
)
from accounting.models import BangLuongThang
from inspection.models import BienBanViPham
from inventory.models import PhieuXuat
from main.models import AuditLog
<<<<<<< HEAD
from users.models import ACTIVE_EMPLOYEE_STATUSES, NhanVien
=======
from users.models import NhanVien
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

logger = logging.getLogger(__name__)


class PayrollService:
    @staticmethod
<<<<<<< HEAD
    def tinh_luong_thang(
        thang: int,
        nam: int,
        user=None,
        nhan_vien_queryset=None,
        batch_size=500,
    ):
=======
    def tinh_luong_thang(thang: int, nam: int, user=None):
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        """
        Tao hoac tinh lai bang luong thang.
        """
        try:
            with transaction.atomic():
<<<<<<< HEAD
                # Scoping BangLuongThang bằng for_tenant()
                bang_luong, _ = BangLuongThang.objects.for_tenant(settings.SCMD_ORGANIZATION_ID).get_or_create(
                    thang=thang,
                    nam=nam,
                    tenant_id=settings.SCMD_ORGANIZATION_ID,
                    defaults={
                        "ten_bang_luong": f"Bang luong he thong - Thang {thang}/{nam}",
                        "trang_thai": BangLuongThang.TrangThai.DRAFT,
                    },
                )

                if not bang_luong.can_recalculate():
                    return False, f"Bang luong thang {thang}/{nam} da khoa so."

                if nhan_vien_queryset is None:
                    # Scoping danh sách nhân viên tính lương bằng for_tenant() (Rule 9)
                    nhan_vien_queryset = NhanVien.objects.for_tenant(
                        settings.SCMD_ORGANIZATION_ID
                    ).filter(trang_thai_lam_viec__in=ACTIVE_EMPLOYEE_STATUSES)

                nhan_vien_ids = list(
                    nhan_vien_queryset.values_list("id", flat=True).order_by("id")
                )
                batch_context = CalculatePayrollUseCase.build_batch_context(
                    bang_luong=bang_luong,
                    tenant_id=settings.SCMD_ORGANIZATION_ID,
                    nhan_vien_ids=nhan_vien_ids,
                )

                created_count = 0
                employee_qs = nhan_vien_queryset.order_by("id")
                for nhan_vien in employee_qs.iterator(chunk_size=batch_size):
=======
                bang_luong, _ = BangLuongThang.objects.get_or_create(
                    thang=thang,
                    nam=nam,
                    defaults={
                        "ten_bang_luong": f"Bang luong he thong - Thang {thang}/{nam}",
                        "trang_thai": "NHAP",
                        "tenant_id": settings.SCMD_ORGANIZATION_ID,
                    },
                )

                if bang_luong.trang_thai == "DA_PHAT_HANH":
                    return False, f"Bang luong thang {thang}/{nam} da khoa so."

                ds_nhan_vien = NhanVien.objects.filter(
                    trang_thai_lam_viec__in=["CHINHTHUC", "THU_VIEC"]
                )

                created_count = 0
                for nhan_vien in ds_nhan_vien:
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                    CalculatePayrollUseCase.execute(
                        nhan_vien=nhan_vien,
                        bang_luong=bang_luong,
                        tenant_id=settings.SCMD_ORGANIZATION_ID,
<<<<<<< HEAD
                        batch_context=batch_context,
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                        user=user,
                    )
                    created_count += 1

                bang_luong.update_totals()
<<<<<<< HEAD
                if bang_luong.trang_thai == BangLuongThang.TrangThai.DRAFT:
                    bang_luong.trang_thai = BangLuongThang.TrangThai.CALCULATED
                    bang_luong.save(update_fields=["trang_thai"])
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

                audit_warning = None
                try:
                    audit_result = AuditPayrollUseCase.execute(
                        bang_luong=bang_luong,
                        tenant_id=settings.SCMD_ORGANIZATION_ID,
                        user=user,
                    )
                    if audit_result.get("status") == "error":
                        audit_warning = (
                            audit_result.get("message") or "audit payroll that bai"
                        )
                except Exception as audit_exc:
                    logger.error(f"Loi hau kiem bang luong: {str(audit_exc)}")
                    audit_warning = str(audit_exc)

                message = f"Hoan tat quyet toan cho {created_count} nhan vien."
                if audit_warning:
                    message += (
                        f" Canh bao: hau kiem payroll chua chay duoc ({audit_warning})."
                    )

                return True, message
<<<<<<< HEAD
        except PayrollRateConfigurationError as exc:
            logger.warning(f"Loi cau hinh payroll: {str(exc)}")
            return False, str(exc)
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        except Exception as exc:
            logger.error(f"Loi PayrollService: {str(exc)}")
            return False, str(exc)

    @staticmethod
    def lock_related_records(bang_luong):
        """
        Khoa cac ban ghi nguon sau khi phat hanh bang luong.
        """
        try:
            with transaction.atomic():
<<<<<<< HEAD
                tenant_id = getattr(bang_luong, "tenant_id", None) or settings.SCMD_ORGANIZATION_ID
                px_qs = PhieuXuat.objects.for_tenant(tenant_id).filter(
=======
                px_qs = PhieuXuat.objects.filter(
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                    loai_xuat="BAN_TRU_LUONG",
                    trang_thai_thanh_toan="CHUA_TRU",
                    ngay_xuat__year=bang_luong.nam,
                    ngay_xuat__month=bang_luong.thang,
                )
                px_count = px_qs.count()
                px_qs.update(trang_thai_thanh_toan="DA_TRU")

<<<<<<< HEAD
                bbp_qs = BienBanViPham.objects.for_tenant(tenant_id).filter(
=======
                bbp_qs = BienBanViPham.objects.filter(
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                    trang_thai="DA_DUYET",
                    ngay_vi_pham__year=bang_luong.nam,
                    ngay_vi_pham__month=bang_luong.thang,
                )
                bbp_count = bbp_qs.count()
                bbp_qs.update(trang_thai="DA_KHAU_TRU")

                AuditLog.objects.create(
                    action=AuditLog.Action.UPDATE,
                    module="accounting",
                    model_name="BangLuongThang",
                    object_id=str(bang_luong.pk),
<<<<<<< HEAD
                    tenant_id=tenant_id,
=======
                    tenant_id=settings.SCMD_ORGANIZATION_ID,
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
                    note=(
                        "Khoa du lieu SSOT sau quyet toan: "
                        f"{px_count} phieu xuat, {bbp_count} bien ban phat."
                    ),
                    changes={
                        "px_locked_count": px_count,
                        "bbp_locked_count": bbp_count,
                        "source_payroll_id": str(bang_luong.pk),
                        "period": f"{bang_luong.thang}/{bang_luong.nam}",
                    },
                    status="SUCCESS",
                )

                logger.info(
                    f"Ky luong {bang_luong}: da khoa {px_count} phieu xuat va {bbp_count} bien ban phat."
                )
                return True, (
                    f"Da dong bo khoa {px_count} phieu xuat va {bbp_count} bien ban phat."
                )
        except Exception as exc:
            logger.error(f"Loi khi khoa ban ghi lien quan: {str(exc)}")
            return False, str(exc)
