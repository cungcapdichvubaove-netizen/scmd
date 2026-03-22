# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2026 SCMD.co.ltd. All Rights Reserved.

File: users/models.py
Author: Mr. Anh
Created Date: 2025-12-05
Updated Date: 2026-03-21
Description: Model quản lý cấu trúc nhân sự, định danh và hồ sơ nghiệp vụ SCMD.
             ENHANCEMENT: Tối ưu Manager, gia cố logic Atomic và chuẩn hóa PEP8.
"""

import logging
from django.db import models, transaction, IntegrityError
from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

# Logger cho hệ thống SCMD
logger = logging.getLogger(__name__)

# --- VALIDATORS ---
phone_validator = RegexValidator(
    regex=r'^0\d{9}$',
    message=_("Số điện thoại không hợp lệ. Vui lòng nhập 10 chữ số bắt đầu bằng số 0 (VD: 0912345678).")
)


# --- MANAGERS TỐI ƯU HÓA TRUY VẤN ---
class NhanVienManager(models.Manager):
    """Tối ưu hóa hiệu suất bằng cách tự động join các bảng liên quan."""
    def get_queryset(self):
        return super().get_queryset().select_related('phong_ban', 'chuc_danh', 'user')


class LichSuCongTacManager(models.Manager):
    """Quản lý các phương thức truy vấn chuyên biệt cho lịch sử công tác."""
    def get_current_position(self, nhan_vien):
        return self.filter(
            nhan_vien=nhan_vien, 
            ngay_ket_thuc__isnull=True
        ).order_by('-ngay_bat_dau').first()


# --- CÁC MODEL CẤU HÌNH HỆ THỐNG ---
class CauHinhMaNhanVien(models.Model):
    tien_to = models.CharField(_("Tiền tố"), max_length=5, default="NV")
    do_dai_so = models.PositiveIntegerField(_("Độ dài phần số"), default=4)
    so_hien_tai = models.PositiveIntegerField(_("Số hiện tại"), default=0)

    class Meta:
        verbose_name = _("Cấu hình Mã nhân viên")
        verbose_name_plural = _("Cấu hình Mã nhân viên")

    def __str__(self):
        return f"{self.tien_to} (Hiện tại: {self.so_hien_tai})"


class ChucDanh(models.Model):
    ten_chuc_danh = models.CharField(_("Tên chức danh"), max_length=100, unique=True)
    mo_ta = models.TextField(_("Mô tả"), blank=True, null=True)
    nhom_quyen = models.ForeignKey(
        Group, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_("Nhóm quyền quản trị")
    )
    
    def __str__(self):
        return self.ten_chuc_danh

    class Meta:
        verbose_name = _("Chức danh")
        verbose_name_plural = _("1. Danh mục Chức danh")


class PhongBan(models.Model):
    ten_phong_ban = models.CharField(_("Tên phòng ban"), max_length=100, unique=True)
    mo_ta = models.TextField(_("Mô tả"), blank=True, null=True)
    nhom_quyen = models.ForeignKey(
        Group, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_("Nhóm quyền mặc định")
    )
    
    def __str__(self):
        return self.ten_phong_ban

    class Meta:
        verbose_name = _("Phòng ban")
        verbose_name_plural = _("2. Danh mục Phòng ban")


# --- MODEL NHÂN VIÊN (CORE ENTITY) ---
class NhanVien(models.Model):
    class GioiTinh(models.TextChoices):
        NAM = "M", _("Nam")
        NU = "F", _("Nữ")
        KHAC = "O", _("Khác")
        
    class TrangThaiLamViec(models.TextChoices):
        THU_VIEC = "THUVIEC", _("Thử việc")
        CHINH_THUC = "CHINHTHUC", _("Chính thức")
        TAM_HOAN = "TAMHOAN", _("Tạm hoãn")
        NGHI_VIEC = "NGHIVIEC", _("Đã nghỉ việc")

    class LoaiHopDong(models.TextChoices):
        XAC_DINH_THOI_HAN = "XDTH", _("Xác định thời hạn")
        KHONG_XAC_DINH_THOI_HAN = "KXDTH", _("Không xác định thời hạn")
        THOI_VU = "THOIVU", _("Thời vụ")

    # Liên kết tài khoản
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name="nhan_vien", 
        verbose_name=_("Tài khoản hệ thống")
    )
    
    # Thông tin tổ chức
    phong_ban = models.ForeignKey(PhongBan, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Phòng ban"))
    chuc_danh = models.ForeignKey(ChucDanh, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Chức danh"))
    ma_nhan_vien = models.CharField(_("Mã số NV"), max_length=20, unique=True, editable=False, db_index=True)
    
    # Thông tin cá nhân
    anh_the = models.ImageField(_("Ảnh thẻ hồ sơ"), upload_to="anh_the/", null=True, blank=True)
    ho_ten = models.CharField(_("Họ và Tên"), max_length=255, db_index=True)
    ngay_sinh = models.DateField(_("Ngày sinh"), null=True, blank=True)
    gioi_tinh = models.CharField(_("Giới tính"), max_length=1, choices=GioiTinh.choices, null=True, blank=True)
    
    # Liên lạc và định danh
    sdt_chinh = models.CharField(
        _("Số điện thoại"), 
        max_length=20,
        validators=[phone_validator],
        db_index=True, 
        null=True, 
        blank=True,
        help_text=_("Định dạng: 0xxxxxxxxx (10 số)")
    )
    so_cccd = models.CharField(_("Số CCCD/CMND"), max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(_("Email cá nhân"), unique=True, null=True, blank=True)
    dia_chi_thuong_tru = models.CharField(_("Địa chỉ thường trú"), max_length=255, blank=True)
    dia_chi_tam_tru = models.CharField(_("Địa chỉ tạm trú"), max_length=255, blank=True)
    nguoi_lien_he_khan_cap = models.CharField(_("Người liên hệ khẩn cấp"), max_length=255, blank=True)
    sdt_khan_cap = models.CharField(_("SĐT khẩn cấp"), max_length=20, blank=True)
    
    # Thông tin công tác
    ngay_vao_lam = models.DateField(_("Ngày vào làm"), null=True, blank=True)
    trang_thai_lam_viec = models.CharField(
        _("Trạng thái nhân sự"), 
        max_length=50, 
        choices=TrangThaiLamViec.choices, 
        default=TrangThaiLamViec.THU_VIEC
    )
    loai_hop_dong = models.CharField(_("Loại hợp đồng"), max_length=50, choices=LoaiHopDong.choices, blank=True)
    
    # Tài chính
    so_tai_khoan = models.CharField(_("Số tài khoản"), max_length=50, blank=True)
    ngan_hang = models.CharField(_("Ngân hàng"), max_length=255, blank=True)
    chi_nhanh_ngan_hang = models.CharField(_("Chi nhánh"), max_length=255, blank=True)

    # Manager tùy chỉnh
    objects = NhanVienManager()

    class Meta:
        verbose_name = _("Nhân viên")
        verbose_name_plural = _("3. Danh sách Nhân viên")
        ordering = ['ma_nhan_vien']

    def __str__(self):
        return f"{self.ma_nhan_vien} - {self.ho_ten}"
        
    @property
    def avatar_url(self):
        """Trả về URL ảnh thẻ hoặc ảnh mặc định cho giao diện Jazzmin."""
        try:
            if self.anh_the and hasattr(self.anh_the, 'url'):
                return self.anh_the.url
        except Exception as e:
            logger.warning(f"Lỗi truy cập URL ảnh thẻ của {self.ma_nhan_vien}: {str(e)}")
        return f"{settings.STATIC_URL}img/default-avatar.png"

    def avatar_tag(self):
        """Thumbnail hiển thị trong trang danh sách Admin."""
        return mark_safe(f'<img src="{self.avatar_url}" width="50" height="50" style="border-radius:50%; object-fit:cover; border: 1px solid #ddd;" />')
    avatar_tag.short_description = _('Ảnh hồ sơ')

    def save(self, *args, **kwargs):
        """Xử lý logic tự động hóa trước khi lưu."""
        is_new = self.pk is None
        
        # 1. Tự động sinh mã nhân viên an toàn với Lock Database
        if not self.ma_nhan_vien:
            try:
                with transaction.atomic():
                    config = CauHinhMaNhanVien.objects.select_for_update().first()
                    if not config:
                        config = CauHinhMaNhanVien.objects.create(tien_to="NV", do_dai_so=4, so_hien_tai=0)
                    config.so_hien_tai += 1
                    config.save()
                    self.ma_nhan_vien = f"{config.tien_to}{str(config.so_hien_tai).zfill(config.do_dai_so)}"
            except Exception as e:
                logger.error(f"Lỗi sinh mã NV: {str(e)}")
                raise ValidationError(_(f"Hệ thống không thể tạo mã nhân viên mới: {str(e)}"))

        # 2. Tạo tài khoản hệ thống cho nhân sự mới
        if is_new and not self.user:
            self._create_system_user()

        super().save(*args, **kwargs)

    def _create_system_user(self):
        """Khởi tạo tài khoản Django User dựa trên mã nhân viên."""
        username = self.ma_nhan_vien
        password = "scmd@123" # Mật khẩu mặc định hệ thống
        full_name = self.ho_ten.strip()
        names = full_name.split(' ')
        first_name = names[-1] if names else ""
        last_name = " ".join(names[:-1]) if len(names) > 1 else ""
        
        try:
            with transaction.atomic():
                final_email = self.email if self.email else None
                # Kiểm tra trùng email để tránh lỗi Integrity
                if final_email and User.objects.filter(email=final_email).exists():
                    final_email = None

                user = User.objects.create_user(
                    username=username, 
                    password=password, 
                    email=final_email, 
                    first_name=first_name, 
                    last_name=last_name
                )
                self.user = user
                # Đảm bảo 1 user chỉ liên kết với 1 nhân viên duy nhất
                NhanVien.objects.filter(user=user).exclude(pk=self.pk).update(user=None)
        except IntegrityError:
            user = User.objects.filter(username=username).first()
            if user:
                self.user = user
        except Exception as e:
            logger.error(f"Lỗi tạo User cho {self.ma_nhan_vien}: {str(e)}")


# --- MODEL HỖ TRỢ HỒ SƠ ---
class HocVan(models.Model):
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="hoc_van")
    truong_dao_tao = models.CharField(_("Trường đào tạo"), max_length=255)
    chuyen_nganh = models.CharField(_("Chuyên ngành"), max_length=255)
    trinh_do = models.CharField(_("Trình độ"), max_length=100)
    tu_ngay = models.DateField(_("Từ ngày"))
    den_ngay = models.DateField(_("Đến ngày"), null=True, blank=True)
    
    class Meta:
        verbose_name = _("Học vấn")
        verbose_name_plural = _("Quá trình Học vấn")


class BangCapChungChi(models.Model):
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="bang_cap")
    ten_bang_cap = models.CharField(_("Tên bằng cấp"), max_length=255)
    noi_cap = models.CharField(_("Nơi cấp"), max_length=255)
    ngay_cap = models.DateField(_("Ngày cấp"))
    ngay_het_han = models.DateField(_("Ngày hết hạn"), null=True, blank=True)
    file_dinh_kem = models.FileField(_("File đính kèm"), upload_to="bang_cap/", null=True, blank=True)

    class Meta:
        verbose_name = _("Bằng cấp")
        verbose_name_plural = _("Bằng cấp & Chứng chỉ")


class LichSuCongTac(models.Model):
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name="lich_su_cong_tac")
    muc_tieu = models.ForeignKey("clients.MucTieu", on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Mục tiêu bảo vệ"))
    chuc_danh_kiem_nhiem = models.ForeignKey(ChucDanh, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Chức danh kiêm nhiệm"))
    quan_ly_truc_tiep = models.ForeignKey(NhanVien, on_delete=models.SET_NULL, null=True, blank=True, related_name="nhan_vien_cap_duoi", verbose_name=_("Quản lý trực tiếp"))
    ngay_bat_dau = models.DateField(_("Ngày bắt đầu"), db_index=True)
    ngay_ket_thuc = models.DateField(_("Ngày kết thúc"), null=True, blank=True)
    
    objects = LichSuCongTacManager()

    class Meta:
        verbose_name = _("Lịch sử công tác")
        verbose_name_plural = _("Lịch sử công tác")
        ordering = ["-ngay_bat_dau"]


# --- SIGNALS (AUTOMATION) ---
@receiver(post_save, sender=NhanVien)
def cap_nhat_quyen_tu_dong(sender, instance, created, **kwargs):
    """Tự động gán User vào các nhóm quyền dựa trên Phòng ban và Chức danh."""
    if instance.user:
        user = instance.user
        try:
            with transaction.atomic():
                # Xóa quyền cũ để cập nhật quyền mới theo chức vụ hiện tại
                user.groups.clear()
                new_groups = []
                
                if instance.chuc_danh and instance.chuc_danh.nhom_quyen:
                    new_groups.append(instance.chuc_danh.nhom_quyen)
                
                if instance.phong_ban and instance.phong_ban.nhom_quyen:
                    new_groups.append(instance.phong_ban.nhom_quyen)
                
                if new_groups:
                    user.groups.add(*new_groups)
                
                # Tự động cấp quyền Staff để truy cập Admin Dashboard
                if instance.chuc_danh and not user.is_staff:
                    user.is_staff = True
                    user.save()
        except Exception as e:
            logger.error(f"Lỗi đồng bộ quyền cho {instance.ma_nhan_vien}: {str(e)}")