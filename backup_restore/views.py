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
import os


def is_superuser(user):
    return user.is_superuser


@user_passes_test(is_superuser)
def backup_restore_view(request):
    if request.method == "POST":
        if "backup" in request.POST:
            # Tạo file sao lưu trong bộ nhớ
            output = StringIO()
            call_command("dumpdata", stdout=output)
            output.seek(0)

            # Chuẩn bị để tải file về
            filename = (
                f"backup_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
            )
            response = HttpResponse(output, content_type="application/json")
            response["Content-Disposition"] = f"attachment; filename={filename}"
            return response

        elif "restore" in request.POST and request.FILES.get("restore_file"):
            restore_file = request.FILES["restore_file"]

            # Lưu file tải lên vào một vị trí tạm thời
            fs = FileSystemStorage(location=settings.MEDIA_ROOT)
            temp_file_name = fs.save(restore_file.name, restore_file)
            temp_file_path = os.path.join(settings.MEDIA_ROOT, temp_file_name)

            try:
                # Xóa sạch database hiện tại
                call_command("flush", "--noinput")

                # Nạp dữ liệu từ file tạm
                call_command("loaddata", temp_file_path)

                messages.success(
                    request,
                    "Phục hồi dữ liệu thành công! Vui lòng tạo lại tài khoản superuser để đăng nhập.",
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

    return render(request, "backup_restore/main.html")
