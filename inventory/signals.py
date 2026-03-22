# file: inventory/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ChiTietPhieuNhap, ChiTietPhieuXuat, CongCuTaiMucTieu

# --- XỬ LÝ NHẬP KHO ---
@receiver(post_save, sender=ChiTietPhieuNhap)
def cap_nhat_kho_khi_nhap(sender, instance, created, **kwargs):
    if created:
        instance.vat_tu.so_luong_ton += instance.so_luong
        instance.vat_tu.save()

@receiver(post_delete, sender=ChiTietPhieuNhap)
def tra_lai_kho_khi_xoa_nhap(sender, instance, **kwargs):
    """Xóa phiếu nhập thì trừ lại kho"""
    instance.vat_tu.so_luong_ton -= instance.so_luong
    instance.vat_tu.save()

# --- XỬ LÝ XUẤT KHO ---
@receiver(post_save, sender=ChiTietPhieuXuat)
def cap_nhat_kho_khi_xuat(sender, instance, created, **kwargs):
    if created:
        # 1. Trừ kho tổng
        instance.vat_tu.so_luong_ton -= instance.so_luong
        instance.vat_tu.save()
        
        # 2. Nếu là xuất cho Mục tiêu -> Cộng vào kho mục tiêu
        phieu_xuat = instance.phieu_xuat
        if phieu_xuat.loai_xuat == 'MUC_TIEU' and phieu_xuat.muc_tieu_nhan:
            # Tìm hoặc tạo mới bản ghi công cụ tại mục tiêu
            cong_cu, _ = CongCuTaiMucTieu.objects.get_or_create(
                muc_tieu=phieu_xuat.muc_tieu_nhan,
                vat_tu=instance.vat_tu,
                defaults={'so_luong_dang_giu': 0}
            )
            cong_cu.so_luong_dang_giu += instance.so_luong
            cong_cu.save()

@receiver(post_delete, sender=ChiTietPhieuXuat)
def tra_lai_kho_khi_xoa_xuat(sender, instance, **kwargs):
    """Xóa phiếu xuất (hủy phiếu) -> Cộng lại kho tổng"""
    instance.vat_tu.so_luong_ton += instance.so_luong
    instance.vat_tu.save()
    
    # Nếu xóa phiếu xuất mục tiêu -> Trừ lại kho mục tiêu
    phieu_xuat = instance.phieu_xuat
    if phieu_xuat.loai_xuat == 'MUC_TIEU' and phieu_xuat.muc_tieu_nhan:
        try:
            cong_cu = CongCuTaiMucTieu.objects.get(
                muc_tieu=phieu_xuat.muc_tieu_nhan,
                vat_tu=instance.vat_tu
            )
            cong_cu.so_luong_dang_giu = max(0, cong_cu.so_luong_dang_giu - instance.so_luong)
            cong_cu.save()
        except CongCuTaiMucTieu.DoesNotExist:
            pass