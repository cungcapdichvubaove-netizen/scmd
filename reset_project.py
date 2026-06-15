# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
File: reset_project.py
Author: Mr. Anh (CTO)
Description: Script dọn dẹp hệ thống và tái tạo cấu trúc Database (Schema).
             NOTE: Phiên bản này KHÔNG tạo dữ liệu mẫu. Database sẽ trắng trơn.
"""

import os
import shutil
import glob
from pathlib import Path
import sys

# Danh sách các App nội bộ cần xóa migrations
LOCAL_APPS = [
    'main', 
    'users', 
    'clients', 
    'operations', 
    'inventory',
    'inspection', 
    'accounting', 
    'workflow', 
    'notifications',
    'backup_restore', 
    'reports', 
    'dashboard', 
    'mobile'
]

def main():
    print("="*60)
    print("🔥 SCMD SYSTEM RESET - CHẾ ĐỘ SẠCH (NO DATA) 🔥")
    print("="*60)
    
    # 1. Kiểm tra vị trí
    base_dir = Path(__file__).resolve().parent
    if not (base_dir / "manage.py").exists():
        print("❌ LỖI: File này phải nằm cùng thư mục với manage.py")
        return

    # 2. Xác nhận
    print("⚠ CẢNH BÁO: Hành động này sẽ:")
    print("   1. Xóa vĩnh viễn Database hiện tại.")
    print("   2. Xóa tất cả file migrations cũ.")
    print("   3. Tạo lại cấu trúc bảng mới (Trống rỗng).")
    
    confirm = input("\n👉 Tiếp tục? (y/n): ")
    if confirm.lower() != 'y':
        print("Đã hủy.")
        return

    # 3. Xóa Database
    db_path = base_dir / "db.sqlite3"
    if db_path.exists():
        print(f"\n[1/3] Đang xóa Database cũ...", end=" ")
        try:
            os.remove(db_path)
            print("✅ OK")
        except PermissionError:
            print("\n❌ LỖI: Database đang mở. TẮT TẤT CẢ SERVER (Ctrl+C) trước!")
            return
    else:
        print("\n[1/3] Database chưa tồn tại. Bỏ qua.")

    # 4. Xóa Migrations cũ
    print("[2/3] Đang dọn dẹp Migrations cũ...")
    deleted_count = 0
    for app in LOCAL_APPS:
        migration_path = base_dir / app / "migrations"
        if migration_path.exists():
            files = glob.glob(str(migration_path / "*.py"))
            for f in files:
                if "__init__.py" not in f:
                    try:
                        os.remove(f)
                        deleted_count += 1
                    except: pass
            
            pycache = migration_path / "__pycache__"
            if pycache.exists():
                shutil.rmtree(pycache, ignore_errors=True)
    
    print(f"   -> Đã xóa {deleted_count} file migrations.")

    # 5. Chạy lệnh hệ thống
    print("\n[3/3] Đang tái cấu trúc hệ thống...")
    
    print("   -> 1. Tạo Migrations (makemigrations)...")
    if os.system(f'"{sys.executable}" manage.py makemigrations') != 0:
        print("❌ Lỗi makemigrations!")
        return

    print("   -> 2. Áp dụng Migrations (migrate)...")
    if os.system(f'"{sys.executable}" manage.py migrate') != 0:
        print("❌ Lỗi migrate!")
        return

    print("\n" + "="*60)
    print("✅ HOÀN TẤT! HỆ THỐNG ĐÃ SẴN SÀNG (DATABASE TRỐNG).")
    print("👉 Lưu ý: Hiện chưa có tài khoản Admin.")
    print("👉 Để tạo Admin thủ công, chạy lệnh: python manage.py createsuperuser")
    print("👉 Để nạp dữ liệu mẫu sau này, chạy lệnh: python manage.py seed_data")
    print("="*60)

if __name__ == "__main__":
    main()