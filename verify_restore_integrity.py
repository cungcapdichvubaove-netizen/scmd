# -*- coding: utf-8 -*-
"""
SCMD Pro - Restore Integrity Validator
--------------------------------------
Sử dụng sau khi restore dữ liệu để xác nhận các cột mốc 'Operational Truth'.
Kiểm tra: AuditLog, Payroll Snapshot, và Geo Data.
"""

import os
import django
import sys
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from main.models import AuditLog
from accounting.models import ChiTietLuong, BangLuongThang
from operations.models import ChamCong

def verify():
    print("--- SCMD Pro Restore Integrity Check ---")
    results = []

    # 1. Kiểm tra AuditLog Integrity (Rule 4.1)
    failed_audits = []
    for log in AuditLog.objects.all()[:100]:
        if log.checksum != log.generate_checksum():
            failed_audits.append(log.id)
    
    results.append(("AuditLog Checksum", len(failed_audits) == 0, f"Phát hiện {len(failed_audits)} log hỏng"))

    # 2. Kiểm tra Payroll Uniqueness (Rule 6.2)
    # Đảm bảo không có phiếu lương mồ côi hoặc trùng lặp sau restore
    dup_slips = ChiTietLuong.objects.values('bang_luong', 'nhan_vien').annotate(count=django.db.models.Count('id')).filter(count__gt=1)
    results.append(("Payroll Uniqueness", dup_slips.count() == 0, f"Có {dup_slips.count()} phiếu trùng lặp"))

    # 2b. Kiểm tra Payroll Snapshot Integrity (Rule 4.6 & 6.2)
    # Xác nhận snapshot chứa đủ thông tin đối soát đơn giá hồi tố (don_gia_hieu_luc_tu, nguon_don_gia, rate_record_id)
    invalid_snapshots = 0
    for ct in ChiTietLuong.objects.all()[:100]:
        snapshot = ct.nguon_du_lieu_snapshot or {}
        required = ['don_gia_hieu_luc_tu', 'nguon_don_gia', 'rate_record_id']
        if not all(k in snapshot for k in required):
            invalid_snapshots += 1
    
    results.append(("Payroll Snapshot Integrity", invalid_snapshots == 0, f"Phát hiện {invalid_snapshots} snapshot thiếu trường đối soát"))

    # 2c. Kiểm tra Inventory Deduction Trace (Rule 6.4)
    # Đảm bảo các phiếu lương có khấu trừ đồng phục phải có trace nguồn trong snapshot
    missing_inv_trace = ChiTietLuong.objects.filter(
        tien_dong_phuc__gt=0,
        tenant_id=settings.SCMD_ORGANIZATION_ID
    ).exclude(nguon_du_lieu_snapshot__has_key='inventory_deductions').count()
    
    results.append(("Inventory Deduction Trace", missing_inv_trace == 0, f"Phát hiện {missing_inv_trace} phiếu lương thiếu trace kho"))

    # 3. Kiểm tra Geo-spatial (Hardening Phase)
    # Đảm bảo PostGIS restore đúng các tọa độ GPS
    gps_nulls = ChamCong.objects.filter(location_check_in__isnull=True).count()
    # Giả sử trong DB mẫu luôn phải có chấm công có GPS
    results.append(("GPS Data Integrity", gps_nulls < ChamCong.objects.count(), f"Cảnh báo: {gps_nulls} bản ghi thiếu GPS"))

    # 4. Kiểm tra kỳ lương LOCKED
    locked_periods = BangLuongThang.objects.filter(trang_thai='LOCKED')
    has_locked = locked_periods.exists()
    results.append(("Locked Payroll Preservation", has_locked, "Không tìm thấy kỳ lương đã khóa nào"))

    failed = False
    for label, status, note in results:
        mark = "✅ [PASS]" if status else "❌ [FAIL]"
        print(f"{mark} {label}: {note}")
        if not status and "Cảnh báo" not in note:
            failed = True

    if failed:
        print("\n❌ KHÔI PHỤC DỮ LIỆU KHÔNG ĐẠT CHUẨN. Kiểm tra lại bản sao lưu.")
        return 1
    
    # Ghi log diễn tập thành công
    AuditLog.objects.create(
        action=AuditLog.Action.EXECUTE,
        module="system",
        model_name="BackupRestoreDrill",
        note="Bàn giao kết quả Restore Drill thành công.",
        status="SUCCESS"
    )
    
    print("\n✅ Dữ liệu Operational Truth đã được khôi phục nguyên trạng.")
    return 0

if __name__ == "__main__":
    sys.exit(verify())