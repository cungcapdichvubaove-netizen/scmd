# file: notifications/models.py
from django.db import models
from django.conf import settings


class ThongBao(models.Model):
    nguoi_nhan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tieu_de = models.CharField("Tiêu đề", max_length=255)
    noi_dung = models.TextField("Nội dung")
    link_hanh_dong = models.URLField("Link hành động", blank=True)
    ngay_tao = models.DateTimeField(auto_now_add=True)
    da_doc = models.BooleanField("Đã đọc", default=False)

    class Meta:
        ordering = ["-ngay_tao"]
