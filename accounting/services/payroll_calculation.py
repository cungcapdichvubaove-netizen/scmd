# -*- coding: utf-8 -*-
"""
Service layer for payroll calculation rules and batch aggregation.
"""

from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Prefetch, Q, Sum

from accounting.domain.attendance_incentive import calculate_attendance_incentive
from accounting.models import CauHinhLuong, ChiTietLuong, KhoanKhauTruNhanVien
from accounting.models_soquy import SoQuy
from inspection.models import BienBanViPham
from inventory.models import PhieuXuat
from clients.models import MucTieuDonGiaHistory
from operations.models import ChamCong, PhanCongCaTruc


class PayrollCalculationService:
    @staticmethod
    def get_period_bounds(thang, nam):
        if thang == 12:
            return date(nam, thang, 1), date(nam + 1, 1, 1)
        return date(nam, thang, 1), date(nam, thang + 1, 1)

    @staticmethod
    def calculate_leave_days_in_period(leave, period_start, period_end):
        """Return prorated leave days overlapping [period_start, period_end).

        DonNghiPhep stores inclusive date ranges. Payroll periods use an
        exclusive end date. If the leave crosses month boundaries, only the
        overlapping calendar portion is counted in this payroll period while
        preserving decimal half-day style ``so_ngay`` values proportionally.
        """
        leave_start = leave.tu_ngay
        leave_end = leave.den_ngay
        if not leave_start or not leave_end or leave_end < period_start or leave_start >= period_end:
            return Decimal("0")
        inclusive_period_end = period_end - timedelta(days=1)
        overlap_start = max(leave_start, period_start)
        overlap_end = min(leave_end, inclusive_period_end)
        if overlap_end < overlap_start:
            return Decimal("0")
        total_calendar_days = max((leave_end - leave_start).days + 1, 1)
        overlap_calendar_days = (overlap_end - overlap_start).days + 1
        declared_days = Decimal(str(leave.so_ngay or total_calendar_days))
        prorated = declared_days * Decimal(overlap_calendar_days) / Decimal(total_calendar_days)
        return prorated.quantize(Decimal("0.01"))

    @staticmethod
    def decimal_aggregate_map(queryset, group_field, aggregate_field, alias):
        return {
            item[group_field]: ChiTietLuong.to_decimal_safe(item[alias])
            for item in queryset.values(group_field).annotate(**{alias: Sum(aggregate_field)})
        }

    @classmethod
    def build_batch_context(cls, bang_luong, tenant_id, nhan_vien_ids):
        if not nhan_vien_ids:
            return {
                "attendance_snapshot_by_employee": defaultdict(list),
                "attendance_count_by_employee": defaultdict(int),
                "actual_work_days_by_employee": defaultdict(int),
                "expected_work_days_by_employee": defaultdict(int),
                "total_hours_by_employee": defaultdict(lambda: Decimal("0")),
                "base_salary_by_employee": defaultdict(lambda: Decimal("0")),
                "target_counter_by_employee": defaultdict(Counter),
                "target_by_id": {},
                "salary_configs": {},
                "fines_by_employee": {},
                "inventory_by_employee": {},
                "advances_by_employee": {},
                "incident_deductions_by_employee": {},
                "approved_paid_leave_days_by_employee": {},
                "approved_unpaid_leave_days_by_employee": {},
                "approved_leave_total_days_by_employee": {},
                "approved_leave_days_in_period_by_employee": {},
                "leave_snapshot_by_employee": defaultdict(list),
            }

        thang = bang_luong.thang
        nam = bang_luong.nam
        period_start, period_end = cls.get_period_bounds(thang, nam)

        attendance_rows = (
            ChamCong.objects.for_tenant(tenant_id)
            .filter(
                ca_truc__nhan_vien_id__in=nhan_vien_ids,
                ca_truc__ngay_truc__gte=period_start,
                ca_truc__ngay_truc__lt=period_end,
                thoi_gian_check_in__gte=period_start,
                thoi_gian_check_in__lt=period_end,
                thoi_gian_check_in__isnull=False,
            )
            .select_related("ca_truc__nhan_vien", "ca_truc__vi_tri_chot__muc_tieu")
            .prefetch_related(
                Prefetch(
                    "ca_truc__vi_tri_chot__muc_tieu__lich_su_don_gia",
                    queryset=MucTieuDonGiaHistory.objects.for_tenant(tenant_id).order_by(
                        "ngay_hieu_luc", "id"
                    ),
                )
            )
            .order_by("ca_truc__nhan_vien_id", "ca_truc__ngay_truc", "id")
        )

        attendance_snapshot_by_employee = defaultdict(list)
        attendance_count_by_employee = defaultdict(int)
        actual_work_dates_by_employee = defaultdict(set)
        total_hours_by_employee = defaultdict(lambda: Decimal("0"))
        base_salary_by_employee = defaultdict(lambda: Decimal("0"))
        target_counter_by_employee = defaultdict(Counter)
        target_by_id = {}

        for cham_cong in attendance_rows:
            employee_id = cham_cong.ca_truc.nhan_vien_id
            gio_lam = Decimal(str(cham_cong.thuc_lam_gio or 0))
            muc_tieu = cham_cong.ca_truc.vi_tri_chot.muc_tieu
            rate_context = muc_tieu.get_payroll_rate_context(cham_cong.ca_truc.ngay_truc)
            don_gia_gio = rate_context["hourly_rate"]

            total_hours_by_employee[employee_id] += gio_lam
            base_salary_by_employee[employee_id] += gio_lam * don_gia_gio
            attendance_count_by_employee[employee_id] += 1
            actual_work_dates_by_employee[employee_id].add(cham_cong.ca_truc.ngay_truc)
            target_counter_by_employee[employee_id][muc_tieu.id] += 1
            target_by_id[muc_tieu.id] = muc_tieu
            attendance_snapshot_by_employee[employee_id].append(
                {
                    "schema_version": "payroll-attendance-rate-snapshot.v1",
                    "cham_cong_id": cham_cong.id,
                    "ca_truc_id": cham_cong.ca_truc_id,
                    "nhan_vien_id": employee_id,
                    "ngay_truc": cham_cong.ca_truc.ngay_truc.isoformat(),
                    "check_in": cham_cong.thoi_gian_check_in.isoformat() if cham_cong.thoi_gian_check_in else None,
                    "check_out": cham_cong.thoi_gian_check_out.isoformat() if cham_cong.thoi_gian_check_out else None,
                    "gio_lam": str(gio_lam),
                    "thuc_lam_gio": str(gio_lam),
                    "di_muon_phut": int(cham_cong.di_muon_phut or 0),
                    "ve_som_phut": int(cham_cong.ve_som_phut or 0),
                    "phat_vi_pham_ca": str(cham_cong.phat_vi_pham or 0),
                    "vi_tri_hop_le": bool(cham_cong.vi_tri_hop_le),
                    "don_gia_gio": str(don_gia_gio),
                    "don_gia_hieu_luc_tu": rate_context["effective_date"].isoformat(),
                    "luong_khoan_bao_ve_thang": str(rate_context["monthly_salary"]),
                    "so_gio_mot_ngay": str(rate_context["standard_hours_per_day"]),
                    "nguon_don_gia": rate_context["source"],
                    "rate_record_id": rate_context["rate_record_id"],
                    "muc_tieu_id": muc_tieu.id,
                    "muc_tieu": muc_tieu.ten_muc_tieu,
                }
            )

        expected_work_dates_by_employee = defaultdict(set)
        assignment_rows = (
            PhanCongCaTruc.objects.for_tenant(tenant_id)
            .filter(
                nhan_vien_id__in=nhan_vien_ids,
                ngay_truc__gte=period_start,
                ngay_truc__lt=period_end,
            )
            .values_list("nhan_vien_id", "ngay_truc")
            .distinct()
        )
        for employee_id, ngay_truc in assignment_rows:
            expected_work_dates_by_employee[employee_id].add(ngay_truc)

        actual_work_days_by_employee = {
            employee_id: len(work_dates)
            for employee_id, work_dates in actual_work_dates_by_employee.items()
        }
        expected_work_days_by_employee = {
            employee_id: len(work_dates)
            for employee_id, work_dates in expected_work_dates_by_employee.items()
        }

        from users.models import DonNghiPhep

        approved_paid_leave_days_by_employee = defaultdict(lambda: Decimal("0"))
        approved_unpaid_leave_days_by_employee = defaultdict(lambda: Decimal("0"))
        approved_leave_total_days_by_employee = defaultdict(lambda: Decimal("0"))
        approved_leave_days_in_period_by_employee = defaultdict(lambda: Decimal("0"))
        leave_snapshot_by_employee = defaultdict(list)
        approved_leaves = DonNghiPhep.objects.for_tenant(tenant_id).filter(
            nhan_vien_id__in=nhan_vien_ids,
            trang_thai=DonNghiPhep.TrangThai.APPROVED,
            tu_ngay__lt=period_end,
            den_ngay__gte=period_start,
        ).select_related("nhan_vien")
        for leave in approved_leaves:
            total_leave_days = Decimal(str(leave.so_ngay or 0))
            leave_days_in_period = cls.calculate_leave_days_in_period(leave, period_start, period_end)
            approved_leave_total_days_by_employee[leave.nhan_vien_id] += total_leave_days
            approved_leave_days_in_period_by_employee[leave.nhan_vien_id] += leave_days_in_period
            if leave.loai_nghi == DonNghiPhep.LoaiNghi.KHONG_LUONG:
                approved_unpaid_leave_days_by_employee[leave.nhan_vien_id] += leave_days_in_period
            else:
                approved_paid_leave_days_by_employee[leave.nhan_vien_id] += leave_days_in_period
            leave_snapshot_by_employee[leave.nhan_vien_id].append({
                "don_nghi_phep_id": leave.pk,
                "ma_don": leave.ma_don,
                "loai_nghi": leave.loai_nghi,
                "tu_ngay": leave.tu_ngay.isoformat(),
                "den_ngay": leave.den_ngay.isoformat(),
                "leave_total_days": str(total_leave_days),
                "leave_days_in_this_period": str(leave_days_in_period),
                "so_ngay": str(leave_days_in_period),
                "payroll_treatment": "UNPAID_LEAVE" if leave.loai_nghi == DonNghiPhep.LoaiNghi.KHONG_LUONG else "APPROVED_PAID_LEAVE_NOT_ABSENT",
            })

        salary_configs = {
            item.nhan_vien_id: item
            for item in CauHinhLuong.objects.for_tenant(tenant_id).filter(
                nhan_vien_id__in=nhan_vien_ids,
            ).select_related("nhan_vien")
        }

        return {
            "attendance_snapshot_by_employee": attendance_snapshot_by_employee,
            "attendance_count_by_employee": attendance_count_by_employee,
            "actual_work_days_by_employee": actual_work_days_by_employee,
            "expected_work_days_by_employee": expected_work_days_by_employee,
            "total_hours_by_employee": total_hours_by_employee,
            "base_salary_by_employee": base_salary_by_employee,
            "target_counter_by_employee": target_counter_by_employee,
            "target_by_id": target_by_id,
            "salary_configs": salary_configs,
            "fines_by_employee": cls.decimal_aggregate_map(
                BienBanViPham.objects.filter(
                    doi_tuong_vi_pham_id__in=nhan_vien_ids,
                    ngay_vi_pham__gte=period_start,
                    ngay_vi_pham__lt=period_end,
                    trang_thai="DA_DUYET",
                ),
                "doi_tuong_vi_pham_id",
                "so_tien_phat",
                "total_fines",
            ),
            "inventory_by_employee": cls.decimal_aggregate_map(
                PhieuXuat.objects.filter(
                    nhan_vien_nhan_id__in=nhan_vien_ids,
                    loai_xuat="BAN_TRU_LUONG",
                    ngay_xuat__gte=period_start,
                    ngay_xuat__lt=period_end,
                    trang_thai_thanh_toan="CHUA_TRU",
                ),
                "nhan_vien_nhan_id",
                "tong_tien_phai_thu",
                "total_inventory",
            ),
            "advances_by_employee": cls.decimal_aggregate_map(
                SoQuy.objects.filter(
                    nhan_vien_id__in=nhan_vien_ids,
                    loai_phieu="CHI",
                    hang_muc="TAM_UNG",
                    trang_thai="DA_DUYET",
                    ngay_lap__gte=period_start,
                    ngay_lap__lt=period_end,
                ),
                "nhan_vien_id",
                "so_tien",
                "total_advance",
            ),
            # Payroll must only deduct incident compensation through approved
            # deduction source records, never directly from BaoCaoSuCo.
            "incident_deductions_by_employee": cls.decimal_aggregate_map(
                KhoanKhauTruNhanVien.objects.for_tenant(tenant_id).filter(
                    nhan_vien_id__in=nhan_vien_ids,
                    loai_khau_tru=KhoanKhauTruNhanVien.LoaiKhauTru.DEN_BU,
                    trang_thai__in=[
                        KhoanKhauTruNhanVien.TrangThai.APPROVED,
                        KhoanKhauTruNhanVien.TrangThai.APPLIED,
                    ],
                ).filter(
                    Q(bang_luong_du_kien=bang_luong)
                    | Q(
                        bang_luong_du_kien__isnull=True,
                        ngay_ap_dung__gte=period_start,
                        ngay_ap_dung__lt=period_end,
                    )
                ),
                "nhan_vien_id",
                "so_tien",
                "total_compensation",
            ),
            "approved_paid_leave_days_by_employee": approved_paid_leave_days_by_employee,
            "approved_unpaid_leave_days_by_employee": approved_unpaid_leave_days_by_employee,
            "approved_leave_total_days_by_employee": approved_leave_total_days_by_employee,
            "approved_leave_days_in_period_by_employee": approved_leave_days_in_period_by_employee,
            "leave_snapshot_by_employee": leave_snapshot_by_employee,
        }

    @classmethod
    def calculate_detail(cls, nhan_vien, batch_context):
        employee_id = nhan_vien.id
        tong_gio_lam = batch_context["total_hours_by_employee"].get(
            employee_id, Decimal("0")
        )
        luong_chinh = batch_context["base_salary_by_employee"].get(
            employee_id, Decimal("0")
        )
        attendance_snapshot = list(
            batch_context["attendance_snapshot_by_employee"].get(employee_id, [])
        )

        salary_config = batch_context["salary_configs"].get(employee_id)
        phu_cap_khac = Decimal("0")
        if salary_config:
            phu_cap_khac = (
                ChiTietLuong.to_decimal_safe(salary_config.phu_cap_trach_nhiem)
                + ChiTietLuong.to_decimal_safe(salary_config.phu_cap_xang_xe)
                + ChiTietLuong.to_decimal_safe(salary_config.phu_cap_an_uong)
            )

        attendance_count = batch_context["attendance_count_by_employee"].get(
            employee_id, len(attendance_snapshot)
        )
        actual_work_days = int(
            batch_context.get("actual_work_days_by_employee", {}).get(
                employee_id,
                attendance_count,
            )
            or 0
        )
        expected_work_days = int(
            batch_context.get("expected_work_days_by_employee", {}).get(
                employee_id,
                actual_work_days,
            )
            or 0
        )
        approved_paid_leave_days = Decimal(str(
            batch_context.get("approved_paid_leave_days_by_employee", {}).get(employee_id, Decimal("0"))
            or 0
        ))
        approved_unpaid_leave_days = Decimal(str(
            batch_context.get("approved_unpaid_leave_days_by_employee", {}).get(employee_id, Decimal("0"))
            or 0
        ))
        leave_total_days = Decimal(str(
            batch_context.get("approved_leave_total_days_by_employee", {}).get(employee_id, approved_paid_leave_days + approved_unpaid_leave_days)
            or 0
        ))
        leave_days_in_this_period = Decimal(str(
            batch_context.get("approved_leave_days_in_period_by_employee", {}).get(employee_id, approved_paid_leave_days + approved_unpaid_leave_days)
            or 0
        ))
        absent_days = max(expected_work_days - actual_work_days - int(approved_paid_leave_days), 0)

        thuong_chuyen_can = Decimal("0")
        incentive_snapshot = {
            "enabled": False,
            "reason": "NO_ATTENDANCE_TARGET",
        }

        target_counter = batch_context.get("target_counter_by_employee", {}).get(employee_id)
        if target_counter:
            if not hasattr(target_counter, "most_common"):
                target_counter = Counter(target_counter)
            primary_target_id = target_counter.most_common(1)[0][0]
            primary_target = batch_context.get("target_by_id", {}).get(primary_target_id)
            if primary_target:
                incentive_result = calculate_attendance_incentive(
                    muc_tieu=primary_target,
                    absent_days=absent_days,
                )
                thuong_chuyen_can = incentive_result["thuong_chuyen_can_thuc_te"]
                incentive_snapshot = {
                    "enabled": True,
                    "muc_tieu_id": primary_target.id,
                    "muc_tieu": primary_target.ten_muc_tieu,
                    "expected_work_days": expected_work_days,
                    "actual_work_days": actual_work_days,
                    "attendance_record_count": int(attendance_count or 0),
                    "absent_days": absent_days,
                    "tien_chuyen_can_goc": str(incentive_result["tien_chuyen_can_goc"]),
                    "khau_tru_chuyen_can": str(incentive_result["khau_tru_chuyen_can"]),
                    "thuong_chuyen_can_thuc_te": str(
                        incentive_result["thuong_chuyen_can_thuc_te"]
                    ),
                    "rule": incentive_result["rule"],
                }

        phat_vi_pham = batch_context["fines_by_employee"].get(employee_id, Decimal("0"))
        tien_dong_phuc = batch_context["inventory_by_employee"].get(
            employee_id, Decimal("0")
        )
        ung_luong = batch_context["advances_by_employee"].get(employee_id, Decimal("0"))
        tien_den_bu = batch_context["incident_deductions_by_employee"].get(employee_id, Decimal("0"))
        bao_hiem = Decimal("0")
        phi_cong_doan = Decimal("0")

        thuc_lanh = (
            luong_chinh
            + thuong_chuyen_can
            + phu_cap_khac
            - ung_luong
            - phat_vi_pham
            - tien_dong_phuc
            - tien_den_bu
            - bao_hiem
            - phi_cong_doan
        )

        snapshot = {
            "schema_version": "payroll-detail-snapshot.v1",
            "attendance": attendance_snapshot,
            "attendance_count": attendance_count,
            "chuyen_can": incentive_snapshot,
            "leave_requests": list(batch_context.get("leave_snapshot_by_employee", {}).get(employee_id, [])),
            "leave_total_days": str(leave_total_days),
            "leave_days_in_this_period": str(leave_days_in_this_period),
            "approved_paid_leave_days_not_absent": str(approved_paid_leave_days),
            "approved_unpaid_leave_days": str(approved_unpaid_leave_days),
            "tong_gio_lam": str(tong_gio_lam),
            "tong_gio_lam_float": float(tong_gio_lam),
            "rate_snapshot_count": len(attendance_snapshot),
            "rate_sources": sorted({row.get("nguon_don_gia") for row in attendance_snapshot if row.get("nguon_don_gia")}),
            "luong_chinh": str(ChiTietLuong.to_decimal_safe(luong_chinh)),
            "thuong_chuyen_can": str(ChiTietLuong.to_decimal_safe(thuong_chuyen_can)),
            "phu_cap_khac": str(ChiTietLuong.to_decimal_safe(phu_cap_khac)),
            "ung_luong": str(ChiTietLuong.to_decimal_safe(ung_luong)),
            "phat_vi_pham": str(ChiTietLuong.to_decimal_safe(phat_vi_pham)),
            "tien_dong_phuc": str(ChiTietLuong.to_decimal_safe(tien_dong_phuc)),
            "tien_den_bu": str(ChiTietLuong.to_decimal_safe(tien_den_bu)),
            "bao_hiem": str(ChiTietLuong.to_decimal_safe(bao_hiem)),
            "phi_cong_doan": str(ChiTietLuong.to_decimal_safe(phi_cong_doan)),
        }

        return {
            "tong_gio_lam": float(tong_gio_lam),
            "so_ngay_nghi": int(approved_unpaid_leave_days),
            "luong_chinh": ChiTietLuong.to_decimal_safe(luong_chinh),
            "thuong_chuyen_can": ChiTietLuong.to_decimal_safe(thuong_chuyen_can),
            "phu_cap_khac": ChiTietLuong.to_decimal_safe(phu_cap_khac),
            "ung_luong": ChiTietLuong.to_decimal_safe(ung_luong),
            "phat_vi_pham": ChiTietLuong.to_decimal_safe(phat_vi_pham),
            "tien_dong_phuc": ChiTietLuong.to_decimal_safe(tien_dong_phuc),
            "tien_den_bu": ChiTietLuong.to_decimal_safe(tien_den_bu),
            "bao_hiem": ChiTietLuong.to_decimal_safe(bao_hiem),
            "phi_cong_doan": ChiTietLuong.to_decimal_safe(phi_cong_doan),
            "thuc_lanh": max(ChiTietLuong.to_decimal_safe(thuc_lanh), Decimal("0")),
            "snapshot": snapshot,
        }
