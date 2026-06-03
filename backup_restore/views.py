# file: backup_restore/views.py

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.management import call_command
from django.contrib.auth.decorators import user_passes_test
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.contrib import messages
from io import StringIO
import datetime
import tempfile
import os

from main.models import AuditLog


def is_superuser(user):
    return user.is_superuser


@user_passes_test(is_superuser)
def backup_restore_view(request):
    # Hardening: Check if web-based restore is allowed in settings
    web_restore_enabled = getattr(settings, 'ENABLE_WEB_RESTORE', False)

    if request.method == "POST":
        if "backup" in request.POST:
            # Tạo file sao lưu trong bộ nhớ
            output = StringIO()
            call_command("dumpdata", stdout=output)
            output.seek(0)

            # Rule 8: Mandatory Audit Logging for sensitive administrative actions
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.ACCESS,
                module="BackupRestore",
                model_name="Database",
                note="Full database backup generated via Web UI.",
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                tenant_id=getattr(settings, 'SCMD_ORGANIZATION_ID', None)
            )

            # Chuẩn bị để tải file về
            filename = (
                f"backup_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
            )
            response = HttpResponse(output, content_type="application/json")
            response["Content-Disposition"] = f"attachment; filename={filename}"
            return response

        elif "restore" in request.POST:
            if not web_restore_enabled:
                messages.error(request, "BẢO MẬT: Tính năng phục hồi dữ liệu qua Web UI bị vô hiệu hóa (ENABLE_WEB_RESTORE=False).")
                return redirect("main:central_hub")

            # 2-Step Verification
            if request.POST.get("confirm_action") != "CONFIRM_RESTORE":
                messages.error(request, "Xác thực thất bại: Vui lòng nhập 'CONFIRM_RESTORE' để xác nhận thao tác xóa sạch dữ liệu.")
                return render(request, "backup_restore/main.html", {"web_restore_enabled": web_restore_enabled})

            restore_file = request.FILES.get("restore_file")
            if not restore_file:
                messages.error(request, "Lỗi: Chưa chọn file sao lưu (.json).")
                return render(request, "backup_restore/main.html", {"web_restore_enabled": web_restore_enabled})

            # Hardening: Use a dedicated secure temp directory instead of shared MEDIA_ROOT
            temp_dir = tempfile.mkdtemp(prefix="scmd_restore_")
            fs = FileSystemStorage(location=temp_dir)
            temp_file_name = fs.save(restore_file.name, restore_file)
            temp_file_path = os.path.join(temp_dir, temp_file_name)

            # Rule 8: Log the restoration attempt
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.EXECUTE,
                module="BackupRestore",
                model_name="Database",
                note=f"CRITICAL: Database restore initiated from file: {restore_file.name}",
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                tenant_id=getattr(settings, 'SCMD_ORGANIZATION_ID', None)
            )

            try:
                # Safeguard: Automatic backup before restore
                safety_backup_filename = f"safety_pre_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                safety_backup_path = os.path.join(temp_dir, safety_backup_filename)
                with open(safety_backup_path, 'w', encoding='utf-8') as f:
                    call_command("dumpdata", stdout=f)

                # Execute dangerous commands
                call_command("flush", "--noinput")
                call_command("loaddata", temp_file_path)

                messages.success(
                    request,
                    f"Phục hồi thành công! Bản lưu an toàn được tạo tại: {safety_backup_path}. Vui lòng tạo lại superuser.",
                )

            except Exception as e:
                messages.error(
                    request, f"Đã có lỗi xảy ra trong quá trình phục hồi: {e}"
                )

            finally:
                # Luôn xóa file tạm sau khi hoàn tất
                if fs.exists(temp_file_name):
                    fs.delete(temp_file_name)

            # Đăng xuất và chuyển về trang đăng nhập admin
            return redirect("/admin/logout/")

    return render(request, "backup_restore/main.html", {"web_restore_enabled": web_restore_enabled})
