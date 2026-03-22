# -*- coding: utf-8 -*-
from django import forms
from users.models import NhanVien
from operations.models import MucTieu
from .models import Task, Proposal

# --- FORM CÔNG VIỆC ---
class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['tieu_de', 'noi_dung', 'nguoi_nhan', 'nguoi_phoi_hop', 'muc_tieu', 'han_chot', 'uu_tien', 'file_dinh_kem']
        widgets = {
            'tieu_de': forms.TextInput(attrs={'class': 'w-full rounded-lg border-slate-300 p-2.5 text-sm font-bold', 'placeholder': 'Tiêu đề công việc...'}),
            'noi_dung': forms.Textarea(attrs={'class': 'w-full rounded-lg border-slate-300 p-2.5 text-sm', 'rows': 4}),
            'nguoi_nhan': forms.Select(attrs={'class': 'select2 w-full'}),
            'nguoi_phoi_hop': forms.SelectMultiple(attrs={'class': 'select2 w-full', 'multiple': 'multiple'}),
            'muc_tieu': forms.Select(attrs={'class': 'select2 w-full'}),
            'han_chot': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full rounded-lg border-slate-300 p-2.5'}),
            'uu_tien': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-300 p-2.5'}),
            'file_dinh_kem': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:py-2 file:px-4 file:rounded-full file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_staffs = NhanVien.objects.filter(trang_thai_lam_viec__in=['CHINHTHUC', 'THUVIEC']).order_by('phong_ban', 'ho_ten')
        self.fields['nguoi_nhan'].queryset = active_staffs
        self.fields['nguoi_phoi_hop'].queryset = active_staffs
        self.fields['muc_tieu'].queryset = MucTieu.objects.all().order_by('ten_muc_tieu')

# --- FORM TỜ TRÌNH ---
class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = ['loai_de_xuat', 'tieu_de', 'noi_dung', 'nguoi_duyet_hien_tai', 'file_dinh_kem']
        widgets = {
            'loai_de_xuat': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-300 p-2.5 text-sm font-bold bg-slate-50'}),
            'tieu_de': forms.TextInput(attrs={'class': 'w-full rounded-lg border-slate-300 p-3 text-sm font-bold placeholder-slate-400 focus:ring-blue-500 focus:border-blue-500', 'placeholder': 'V/v: ...'}),
            'noi_dung': forms.Textarea(attrs={'class': 'w-full rounded-lg border-slate-300 p-4 text-sm focus:ring-blue-500 focus:border-blue-500', 'rows': 10}),
            'nguoi_duyet_hien_tai': forms.Select(attrs={'class': 'select2 w-full', 'data-placeholder': 'Chọn lãnh đạo duyệt...'}),
            'file_dinh_kem': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nguoi_duyet_hien_tai'].queryset = NhanVien.objects.filter(trang_thai_lam_viec='CHINHTHUC').order_by('phong_ban', 'chuc_danh')
        self.fields['nguoi_duyet_hien_tai'].label = "Kính trình (Người duyệt đầu tiên)"

# --- FORM DUYỆT ---
class ApprovalActionForm(forms.Form):
    HANH_DONG = [
        ('DUYET_KET_THUC', '✅ Phê duyệt & Ban hành'),
        ('CHUYEN_TIEP', '🔄 Kính chuyển cấp trên'),
        ('YEU_CAU_SUA', '✏️ Yêu cầu sửa'),
        ('TU_CHOI', '❌ Từ chối'),
    ]
    
    hanh_dong = forms.ChoiceField(choices=HANH_DONG, widget=forms.RadioSelect(attrs={'class': 'form-radio text-blue-600 space-y-2'}), label="Quyết định")
    y_kien = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'w-full rounded-lg border-slate-300 p-3 text-sm mt-2'}), label="Ý kiến", required=True)
    nguoi_tiep_theo = forms.ModelChoiceField(queryset=NhanVien.objects.filter(trang_thai_lam_viec='CHINHTHUC').order_by('phong_ban'), required=False, label="Chuyển đến", widget=forms.Select(attrs={'class': 'select2 w-full'}))