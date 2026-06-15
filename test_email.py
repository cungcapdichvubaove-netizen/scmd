# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro - SMTP Connection Tester
=======
SCMD ERP - SMTP Connection Tester
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
---------------------------------
Script này dùng để kiểm tra cấu hình Email trong settings.py và .env.
Cách chạy: python test_email.py
"""

import os
import django
import sys

# 1. Khởi tạo môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
except Exception as e:
    print(f"❌ Không thể khởi tạo Django: {e}")
    sys.exit(1)

from django.core.mail import send_mail
from django.conf import settings

def run_test():
    print("="*50)
<<<<<<< HEAD
    print("🚀 SCMD Pro - SMTP tester")
=======
    print("🚀 SCMD ERP - SMTP TESTER")
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    print("="*50)
    print(f"Backend: {settings.EMAIL_BACKEND}")
    print(f"Host:    {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
    print(f"User:    {settings.EMAIL_HOST_USER}")
    print("-"*50)

    recipient = input("👉 Nhập địa chỉ email người nhận để thử nghiệm: ")
    
    try:
<<<<<<< HEAD
        subject = "SCMD Pro - Kiểm tra kết nối SMTP"
        message = "Nếu bạn nhận được email này, cấu hình SMTP của hệ thống SCMD Pro đã hoạt động chính xác!"
=======
        subject = "SCMD ERP - Kiểm tra kết nối SMTP"
        message = "Nếu bạn nhận được email này, cấu hình SMTP của hệ thống SCMD ERP đã hoạt động chính xác!"
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        print("\n✅ THÀNH CÔNG! Email đã được gửi đi. Vui lòng kiểm tra hộp thư (bao gồm cả thư rác).")
    except Exception as e:
        print(f"\n❌ THẤT BẠI! Lỗi phát sinh: \n{str(e)}")

if __name__ == "__main__":
    run_test()