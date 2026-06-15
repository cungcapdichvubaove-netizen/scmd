# -*- coding: utf-8 -*-
from django import forms
from users.models import NhanVien
from operations.models import MucTieu
from .models import Task, Proposal

# --- FORM CÔNG VIỆC ---
<<<<<<< HEAD
class StaffOptionMixin:
    """Gắn metadata phòng ban/chức danh vào option để template lọc người nhận nhanh."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        instance = getattr(value, 'instance', None)
        if instance:
            phong_ban = getattr(getattr(instance, 'phong_ban', None), 'ten_phong_ban', '') or ''
            chuc_danh = getattr(getattr(instance, 'chuc_danh', None), 'ten_chuc_danh', '') or ''
            option['attrs']['data-phong-ban'] = phong_ban
            option['attrs']['data-chuc-danh'] = chuc_danh
            option['attrs']['data-ho-ten'] = getattr(instance, 'ho_ten', '') or ''
            option['attrs']['data-ma-nv'] = getattr(instance, 'ma_nhan_vien', '') or ''
        return option


class StaffSelect(StaffOptionMixin, forms.Select):
    pass


class StaffSelectMultiple(StaffOptionMixin, forms.SelectMultiple):
    pass


class TargetSelect(forms.Select):
    """Gắn metadata mục tiêu để bộ lọc mục tiêu không cần gọi API phụ."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        instance = getattr(value, 'instance', None)
        if instance:
            option['attrs']['data-muc-tieu'] = getattr(instance, 'ten_muc_tieu', '') or ''
            hop_dong = getattr(instance, 'hop_dong', None)
            option['attrs']['data-hop-dong'] = str(hop_dong) if hop_dong else ''
        return option


=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['tieu_de', 'noi_dung', 'nguoi_nhan', 'nguoi_phoi_hop', 'muc_tieu', 'han_chot', 'uu_tien', 'file_dinh_kem']
        widgets = {
<<<<<<< HEAD
            'tieu_de': forms.TextInput(attrs={
                'class': 'wf-input wf-title-input',
                'placeholder': 'Ví dụ: Kiểm tra hồ sơ ca trực mục tiêu A trong tuần này',
            }),
            'noi_dung': forms.Textarea(attrs={
                'class': 'wf-input wf-textarea',
                'rows': 12,
                'placeholder': 'Nêu rõ việc cần làm, căn cứ giao việc, kết quả mong muốn, tài liệu/bằng chứng cần bàn giao và tiêu chí hoàn thành...',
            }),
            'nguoi_nhan': StaffSelect(attrs={
                'class': 'select2 wf-input wf-select',
                'data-placeholder': 'Chọn người chịu trách nhiệm chính...',
                'data-staff-filtered': '1',
            }),
            'nguoi_phoi_hop': StaffSelectMultiple(attrs={
                'class': 'select2 wf-input wf-select',
                'multiple': 'multiple',
                'data-placeholder': 'Chọn nhân sự phối hợp nếu có...',
                'data-staff-filtered': '1',
            }),
            'muc_tieu': TargetSelect(attrs={
                'class': 'select2 wf-input wf-select',
                'data-placeholder': 'Chọn mục tiêu liên quan nếu có...',
                'data-target-filtered': '1',
            }),
            'han_chot': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'wf-input',
            }),
            'uu_tien': forms.Select(attrs={'class': 'wf-input wf-select'}),
            'file_dinh_kem': forms.FileInput(attrs={'class': 'wf-file-input'}),
        }

    @staticmethod
    def _staff_label(nhan_vien):
        phong_ban = getattr(getattr(nhan_vien, 'phong_ban', None), 'ten_phong_ban', None) or 'Chưa rõ phòng ban'
        chuc_danh = getattr(getattr(nhan_vien, 'chuc_danh', None), 'ten_chuc_danh', None) or 'Chưa rõ chức danh'
        ma_nv = getattr(nhan_vien, 'ma_nhan_vien', '') or 'NV'
        return f"{ma_nv} - {nhan_vien.ho_ten} — {phong_ban} — {chuc_danh}"

    @staticmethod
    def _target_label(muc_tieu):
        ten = getattr(muc_tieu, 'ten_muc_tieu', '') or str(muc_tieu)
        hop_dong = getattr(muc_tieu, 'hop_dong', None)
        return f"{ten} — {hop_dong}" if hop_dong else ten

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Workflow giao việc chỉ dành cho khối quản lý/phòng ban. Nhân viên bảo vệ hiện trường
        # gửi kiến nghị qua phòng nghiệp vụ; không là người nhận trực tiếp của workflow chung.
        active_staffs = (
            NhanVien.objects
            .filter(trang_thai_lam_viec__in=['CHINHTHUC', 'THUVIEC'])
            .select_related('phong_ban', 'chuc_danh')
            .exclude(chuc_danh__ten_chuc_danh__icontains='bảo vệ')
            .exclude(phong_ban__ten_phong_ban__icontains='bảo vệ')
            .order_by('phong_ban__ten_phong_ban', 'chuc_danh__ten_chuc_danh', 'ho_ten')
        )
        self.fields['nguoi_nhan'].queryset = active_staffs
        self.fields['nguoi_nhan'].label = 'Người chịu trách nhiệm chính'
        self.fields['nguoi_nhan'].help_text = 'Chọn một nhân sự khối quản lý/phòng ban chịu trách nhiệm hoàn thành việc.'
        self.fields['nguoi_nhan'].label_from_instance = self._staff_label

        self.fields['nguoi_phoi_hop'].queryset = active_staffs
        self.fields['nguoi_phoi_hop'].required = False
        self.fields['nguoi_phoi_hop'].help_text = 'Có thể chọn nhiều người phối hợp; không bắt buộc.'
        self.fields['nguoi_phoi_hop'].label_from_instance = self._staff_label

        targets = MucTieu.objects.select_related('hop_dong').order_by('ten_muc_tieu')
        self.fields['muc_tieu'].queryset = targets
        self.fields['muc_tieu'].required = False
        self.fields['muc_tieu'].empty_label = 'Không gắn mục tiêu cụ thể'
        self.fields['muc_tieu'].label_from_instance = self._target_label
        self.fields['muc_tieu'].help_text = 'Chỉ gắn mục tiêu khi công việc liên quan trực tiếp đến khách hàng/mục tiêu bảo vệ.'
=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

# --- FORM TỜ TRÌNH ---
class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = ['loai_de_xuat', 'tieu_de', 'noi_dung', 'nguoi_duyet_hien_tai', 'file_dinh_kem']
        widgets = {
<<<<<<< HEAD
            'loai_de_xuat': forms.Select(attrs={'class': 'workflow-input workflow-select'}),
            'tieu_de': forms.TextInput(attrs={'class': 'workflow-input workflow-title-input', 'placeholder': 'Ví dụ: V/v đề nghị phê duyệt mua sắm đồng phục tháng này'}),
            'noi_dung': forms.Textarea(attrs={'class': 'workflow-input workflow-textarea', 'rows': 14, 'placeholder': 'Nêu rõ bối cảnh, căn cứ, đề xuất, chi phí/nguồn lực liên quan, thời hạn cần phê duyệt và đơn vị thực hiện sau khi được duyệt...'}),
            'nguoi_duyet_hien_tai': forms.Select(attrs={'class': 'select2 workflow-input workflow-select', 'data-placeholder': 'Chọn người duyệt đầu tiên...'}),
            'file_dinh_kem': forms.FileInput(attrs={'class': 'workflow-file-input'}),
        }

    @staticmethod
    def _approver_label(nhan_vien):
        phong_ban = getattr(getattr(nhan_vien, 'phong_ban', None), 'ten_phong_ban', None) or 'Chưa rõ phòng ban'
        chuc_danh = getattr(getattr(nhan_vien, 'chuc_danh', None), 'ten_chuc_danh', None) or 'Chưa rõ chức danh'
        ma_nv = getattr(nhan_vien, 'ma_nhan_vien', '') or 'NV'
        return f"{ma_nv} - {nhan_vien.ho_ten} — {phong_ban} — {chuc_danh}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Workflow chung chỉ dành cho khối quản lý/phòng ban. Loại nhân sự bảo vệ hiện trường
        # khỏi danh sách kính trình để tránh trình thẳng sai luồng nghiệp vụ.
        approvers = (
            NhanVien.objects
            .filter(trang_thai_lam_viec='CHINHTHUC')
            .select_related('phong_ban', 'chuc_danh')
            .exclude(chuc_danh__ten_chuc_danh__icontains='bảo vệ')
            .exclude(phong_ban__ten_phong_ban__icontains='bảo vệ')
            .order_by('phong_ban__ten_phong_ban', 'chuc_danh__ten_chuc_danh', 'ho_ten')
        )
        field = self.fields['nguoi_duyet_hien_tai']
        field.queryset = approvers
        field.required = True
        field.empty_label = 'Chọn người duyệt đầu tiên'
        field.label = "Kính trình"
        field.help_text = "Chọn người thụ lý/duyệt bước đầu thuộc khối quản lý hoặc phòng ban chức năng."
        field.label_from_instance = self._approver_label
=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

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