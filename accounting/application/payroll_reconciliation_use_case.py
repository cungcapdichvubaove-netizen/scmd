# -*- coding: utf-8 -*-
"""Phase C payroll source reconciliation.

This use case brings Phase A+B business records into payroll snapshots without
removing legacy sources yet. It refuses to write into LOCKED/PAID periods.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from accounting.models import BangLuongThang, ChiTietLuong, KhoanKhauTruNhanVien, TamUngLuong
from accounting.models_soquy import SoQuy
from accounting.services.payroll_calculation import PayrollCalculationService
from main.models import AuditLog
from users.models import DonNghiPhep, HoSoBaoHiem, NhanVien


class PayrollSourceReconciliationUseCase:
    """Reconcile approved source records into ``ChiTietLuong`` snapshots."""

    @staticmethod
    def _decimal(value):
        return ChiTietLuong.to_decimal_safe(value or Decimal("0"))

    @classmethod
    def _sum_by_employee(cls, queryset, field="so_tien"):
        return {
            item["nhan_vien_id"]: cls._decimal(item["total"])
            for item in queryset.values("nhan_vien_id").annotate(total=Sum(field))
        }

    @staticmethod
    def _leave_days_by_employee(queryset, period_start, period_end):
        result = defaultdict(lambda: Decimal("0"))
        for leave in queryset:
            result[leave.nhan_vien_id] += PayrollCalculationService.calculate_leave_days_in_period(leave, period_start, period_end)
        return dict(result)

    @staticmethod
    def _leave_total_days_by_employee(queryset):
        result = defaultdict(lambda: Decimal("0"))
        for leave in queryset:
            result[leave.nhan_vien_id] += Decimal(str(leave.so_ngay or 0))
        return dict(result)

    @staticmethod
    def _serialize_source_ids(queryset):
        return list(queryset.values_list("id", flat=True))

    @classmethod
    def execute(cls, *, bang_luong, tenant_id, employee_ids=None, actor=None, include_legacy=True):
        with transaction.atomic():
            payroll_id = bang_luong.pk if hasattr(bang_luong, "pk") else bang_luong
            payroll = BangLuongThang.objects.for_tenant(tenant_id).select_for_update().get(pk=payroll_id)
            if payroll.is_locked:
                raise ValueError(
                    f"Không được đối soát nguồn vào kỳ lương {payroll.thang}/{payroll.nam} khi đã {payroll.trang_thai}."
                )

            period_start, period_end = PayrollCalculationService.get_period_bounds(payroll.thang, payroll.nam)
            staff_qs = NhanVien.objects.for_tenant(tenant_id)
            if employee_ids:
                staff_qs = staff_qs.filter(id__in=employee_ids)
            staff_ids = list(staff_qs.values_list("id", flat=True))

            advances_qs = TamUngLuong.objects.for_tenant(tenant_id).filter(
                nhan_vien_id__in=staff_ids,
                trang_thai__in=[TamUngLuong.TrangThai.APPROVED, TamUngLuong.TrangThai.PAID],
            ).filter(
                bang_luong_du_kien=payroll
            )
            deductions_qs = KhoanKhauTruNhanVien.objects.for_tenant(tenant_id).filter(
                nhan_vien_id__in=staff_ids,
                trang_thai=KhoanKhauTruNhanVien.TrangThai.APPROVED,
            ).filter(
                bang_luong_du_kien=payroll
            )
            insurance_qs = HoSoBaoHiem.objects.for_tenant(tenant_id).filter(
                nhan_vien_id__in=staff_ids,
                loai_bao_hiem=HoSoBaoHiem.LoaiBaoHiem.BHXH,
                trang_thai=HoSoBaoHiem.TrangThai.ACTIVE,
                ngay_tham_gia__lt=period_end,
            ).filter(
                models_q_ngay_ket_thuc()
            )
            leave_qs = DonNghiPhep.objects.for_tenant(tenant_id).filter(
                nhan_vien_id__in=staff_ids,
                trang_thai=DonNghiPhep.TrangThai.APPROVED,
                tu_ngay__lt=period_end,
                den_ngay__gte=period_start,
            )

            linked_advance_ids = set(
                deductions_qs.exclude(tam_ung_id__isnull=True).values_list("tam_ung_id", flat=True)
            )
            direct_advances_qs = advances_qs.exclude(id__in=linked_advance_ids) if linked_advance_ids else advances_qs
            advances_by_employee = cls._sum_by_employee(direct_advances_qs)
            unpaid_leave_qs = leave_qs.filter(loai_nghi=DonNghiPhep.LoaiNghi.KHONG_LUONG)
            unpaid_leave_days = cls._leave_days_by_employee(unpaid_leave_qs, period_start, period_end)
            paid_leave_days = cls._leave_days_by_employee(leave_qs.exclude(loai_nghi=DonNghiPhep.LoaiNghi.KHONG_LUONG), period_start, period_end)
            leave_total_days = cls._leave_total_days_by_employee(leave_qs)
            leave_days_in_period = cls._leave_days_by_employee(leave_qs, period_start, period_end)

            deduction_totals = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
            deduction_ids = defaultdict(list)
            for deduction in deductions_qs:
                employee_id = deduction.nhan_vien_id
                amount = cls._decimal(deduction.so_tien)
                deduction_ids[employee_id].append(deduction.pk)
                if deduction.loai_khau_tru == KhoanKhauTruNhanVien.LoaiKhauTru.TAM_UNG:
                    deduction_totals[employee_id]["ung_luong"] += amount
                elif deduction.loai_khau_tru == KhoanKhauTruNhanVien.LoaiKhauTru.DONG_PHUC:
                    deduction_totals[employee_id]["tien_dong_phuc"] += amount
                elif deduction.loai_khau_tru == KhoanKhauTruNhanVien.LoaiKhauTru.DEN_BU:
                    deduction_totals[employee_id]["tien_den_bu"] += amount
                elif deduction.loai_khau_tru == KhoanKhauTruNhanVien.LoaiKhauTru.VI_PHAM:
                    deduction_totals[employee_id]["phat_vi_pham"] += amount
                elif deduction.loai_khau_tru == KhoanKhauTruNhanVien.LoaiKhauTru.BAO_HIEM:
                    deduction_totals[employee_id]["bao_hiem"] += amount
                else:
                    deduction_totals[employee_id]["tien_den_bu"] += amount

            legacy_advances_by_employee = {}
            legacy_ids = defaultdict(list)
            if include_legacy:
                legacy_qs = SoQuy.objects.for_tenant(tenant_id).filter(
                    nhan_vien_id__in=staff_ids,
                    loai_phieu="CHI",
                    hang_muc="TAM_UNG",
                    trang_thai="DA_DUYET",
                    ngay_lap__gte=period_start,
                    ngay_lap__lt=period_end,
                )
                legacy_advances_by_employee = cls._sum_by_employee(legacy_qs)
                for obj in legacy_qs.only("id", "nhan_vien_id"):
                    legacy_ids[obj.nhan_vien_id].append(obj.pk)

            insurance_ids = defaultdict(list)
            for profile in insurance_qs.only("id", "nhan_vien_id"):
                insurance_ids[profile.nhan_vien_id].append(profile.pk)
            leave_ids = defaultdict(list)
            for leave in leave_qs.only("id", "nhan_vien_id"):
                leave_ids[leave.nhan_vien_id].append(leave.pk)

            changed = []
            for staff_id in staff_ids:
                new_advance = advances_by_employee.get(staff_id, Decimal("0"))
                legacy_advance = legacy_advances_by_employee.get(staff_id, Decimal("0"))
                totals = deduction_totals.get(staff_id, {})
                source_present = any([
                    new_advance,
                    legacy_advance,
                    totals,
                    unpaid_leave_days.get(staff_id),
                    paid_leave_days.get(staff_id),
                    insurance_ids.get(staff_id),
                ])
                existing = ChiTietLuong.objects.for_tenant(tenant_id).filter(bang_luong=payroll, nhan_vien_id=staff_id).first()
                if not source_present and existing is None:
                    continue

                detail = existing or ChiTietLuong(
                    tenant_id=tenant_id,
                    bang_luong=payroll,
                    nhan_vien_id=staff_id,
                )
                detail.ung_luong = new_advance + totals.get("ung_luong", Decimal("0")) + legacy_advance
                detail.tien_dong_phuc = totals.get("tien_dong_phuc", detail.tien_dong_phuc or Decimal("0"))
                detail.tien_den_bu = totals.get("tien_den_bu", detail.tien_den_bu or Decimal("0"))
                detail.phat_vi_pham = totals.get("phat_vi_pham", detail.phat_vi_pham or Decimal("0"))
                detail.bao_hiem = totals.get("bao_hiem", detail.bao_hiem or Decimal("0"))
                detail.so_ngay_nghi = int(unpaid_leave_days.get(staff_id, Decimal("0")))
                detail.thuc_lanh = max(detail.tong_thu_nhap - detail.tong_khau_tru, Decimal("0"))
                snapshot = dict(detail.nguon_du_lieu_snapshot or {})
                snapshot["phase_c_reconciliation"] = {
                    "schema_version": "payroll-source-reconciliation.v2",
                    "tam_ung_luong_direct_ids": list(direct_advances_qs.filter(nhan_vien_id=staff_id).values_list("id", flat=True)),
                    "tam_ung_luong_ids": list(advances_qs.filter(nhan_vien_id=staff_id).values_list("id", flat=True)),
                    "tam_ung_luong_excluded_due_to_deduction_ids": [
                        obj_id for obj_id in advances_qs.filter(nhan_vien_id=staff_id, id__in=linked_advance_ids).values_list("id", flat=True)
                    ],
                    "khoan_khau_tru_ids": deduction_ids.get(staff_id, []),
                    "ho_so_bhxh_active_ids": insurance_ids.get(staff_id, []),
                    "don_nghi_phep_ids": leave_ids.get(staff_id, []),
                    "leave_total_days": str(leave_total_days.get(staff_id, Decimal("0"))),
                    "leave_days_in_this_period": str(leave_days_in_period.get(staff_id, Decimal("0"))),
                    "paid_leave_days_not_absent": str(paid_leave_days.get(staff_id, Decimal("0"))),
                    "unpaid_leave_days": str(unpaid_leave_days.get(staff_id, Decimal("0"))),
                    "legacy_sources": {
                        "enabled": bool(include_legacy),
                        "so_quy_tam_ung_ids": legacy_ids.get(staff_id, []),
                        "so_quy_tam_ung_amount": str(legacy_advance),
                    },
                }
                detail.nguon_du_lieu_snapshot = snapshot
                detail.reconciliation_note = "Phase C source reconciliation: HĐLĐ/leave/advance/deduction/insurance sources linked."
                detail._audit_user = actor if getattr(actor, "is_authenticated", False) else None
                detail._audit_note = "Phase C payroll source reconciliation"
                detail.save()
                changed.append(detail.pk)

            AuditLog.objects.create(
                user=actor if getattr(actor, "is_authenticated", False) else None,
                action=AuditLog.Action.EXECUTE,
                module="accounting",
                model_name="BangLuongThang",
                object_id=str(payroll.pk),
                tenant_id=tenant_id,
                note="Phase C payroll source reconciliation executed",
                changes={"reconciled_detail_ids": changed, "source_model_count": 4, "legacy_sources_preserved": bool(include_legacy)},
            )
            return {"status": "ok", "reconciled_count": len(changed), "detail_ids": changed}


def models_q_ngay_ket_thuc():
    """Avoid importing Q at module import-sites that monkeypatch Django settings."""
    from django.db.models import Q

    return Q(ngay_ket_thuc__isnull=True) | Q(ngay_ket_thuc__gte=timezone_safe_date())


def timezone_safe_date():
    from django.utils import timezone

    return timezone.localdate()
