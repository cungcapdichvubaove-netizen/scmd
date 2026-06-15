# file: inventory/forms.py
from django import forms
from .models import CapPhatCaNhan, VatTu
from users.models import NhanVien

class CapPhatCaNhanForm(forms.ModelForm):
    vat_tu = forms.ModelChoiceField(
        queryset=VatTu.objects.order_by('ten_vat_tu'),
        label="Chọn vật tư",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    nguoi_nhan = forms.ModelChoiceField(
        # Tối ưu: Chỉ lấy nhân viên đang hoạt động để giảm tải dropdown (P2)
        # Scoping: Đảm bảo tuân thủ ranh giới nhân sự của tổ chức.
        queryset=NhanVien.objects.filter(user__is_active=True).order_by('ho_ten'),
        label="Nhân viên nhận",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    so_luong = forms.IntegerField(
        label="Số lượng",
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    ghi_chu = forms.CharField(
        label="Ghi chú",
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    class Meta:
        model = CapPhatCaNhan
        fields = ['vat_tu', 'nguoi_nhan', 'so_luong', 'ghi_chu']

    def clean_so_luong(self):
        so_luong = self.cleaned_data.get('so_luong')
        vat_tu = self.cleaned_data.get('vat_tu')
        
        # Kiểm tra tồn kho
        if vat_tu and so_luong:
            if so_luong > vat_tu.so_luong: # Đã sửa thành vat_tu.so_luong
                raise forms.ValidationError(
                    f"Kho không đủ hàng! Hiện chỉ còn {vat_tu.so_luong} {vat_tu.don_vi_tinh}."
                )
        return so_luong