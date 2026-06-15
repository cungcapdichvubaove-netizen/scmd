# -*- coding: utf-8 -*-
<<<<<<< HEAD
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from .forms import TaskForm, ProposalForm, ApprovalActionForm
from .models import Task, Proposal, PheDuyetLog


class WorkflowDashboardView(LoginRequiredMixin, View):
    """Workspace chung cho khối quản lý/phòng ban.

    Trang này không phải kênh kiến nghị trực tiếp của nhân viên bảo vệ hiện trường.
    Kiến nghị từ hiện trường cần được phòng nghiệp vụ tiếp nhận, chuẩn hóa hồ sơ và
    trình lên đây dưới dạng đề xuất/công việc nội bộ để các phòng ban thẩm định,
    phê duyệt và thực hiện theo phân quyền.
    """

    def get(self, request):
        try:
            nhan_vien = request.user.nhan_vien
        except Exception:
            messages.error(request, "Tài khoản chưa liên kết nhân viên!")
            return redirect('dashboard:main')

        now = timezone.now()
        due_soon_at = now + timedelta(hours=24)

        my_tasks = (
            Task.objects
            .filter(Q(nguoi_nhan=nhan_vien) | Q(nguoi_phoi_hop=nhan_vien))
            .exclude(trang_thai__in=[Task.Status.HOAN_THANH, Task.Status.DA_HUY])
            .select_related('nguoi_giao', 'nguoi_nhan', 'muc_tieu')
            .prefetch_related('nguoi_phoi_hop')
            .distinct()
            .order_by('han_chot', '-uu_tien', '-ngay_tao')
        )

        assigned_tasks = (
            Task.objects
            .filter(nguoi_giao=nhan_vien)
            .exclude(trang_thai__in=[Task.Status.HOAN_THANH, Task.Status.DA_HUY])
            .select_related('nguoi_giao', 'nguoi_nhan', 'muc_tieu')
            .order_by('han_chot', '-ngay_tao')[:6]
        )

        pending_approvals = (
            Proposal.objects
            .filter(nguoi_duyet_hien_tai=nhan_vien, trang_thai=Proposal.Status.CHO_DUYET)
            .select_related('nguoi_de_xuat', 'nguoi_duyet_hien_tai')
            .order_by('ngay_tao')
        )

        my_proposals_qs = (
            Proposal.objects
            .filter(nguoi_de_xuat=nhan_vien)
            .select_related('nguoi_de_xuat', 'nguoi_duyet_hien_tai')
            .order_by('-ngay_tao')
        )

        involved_proposals_qs = (
            Proposal.objects
            .filter(Q(nguoi_de_xuat=nhan_vien) | Q(nguoi_duyet_hien_tai=nhan_vien) | Q(logs__nguoi_xu_ly=nhan_vien))
            .distinct()
        )

        overdue_tasks = my_tasks.filter(han_chot__lt=now)
        due_soon_tasks = my_tasks.filter(han_chot__gte=now, han_chot__lte=due_soon_at)
        returned_proposals = my_proposals_qs.filter(trang_thai=Proposal.Status.YEU_CAU_SUA)
        approved_proposals_count = my_proposals_qs.filter(trang_thai=Proposal.Status.DA_DUYET).count()

        proposal_type_stats = list(
            involved_proposals_qs
            .values('loai_de_xuat')
            .annotate(total=Count('id'))
            .order_by('-total')[:5]
        )
        proposal_type_label_map = dict(Proposal.Type.choices)
        max_type_count = max([item['total'] for item in proposal_type_stats] or [1])
        for item in proposal_type_stats:
            item['label'] = proposal_type_label_map.get(item['loai_de_xuat'], item['loai_de_xuat'])
            item['percent'] = round((item['total'] / max_type_count) * 100) if max_type_count else 0

        proposal_status_stats = {
            row['trang_thai']: row['total']
            for row in involved_proposals_qs.values('trang_thai').annotate(total=Count('id'))
        }

        action_items = []
        for item in pending_approvals[:5]:
            action_items.append({
                'tone': 'danger',
                'type': 'Cần duyệt',
                'title': item.tieu_de,
                'meta': f"{item.get_loai_de_xuat_display()} · từ {item.nguoi_de_xuat.ho_ten}",
                'time': item.ngay_tao,
                'url': reverse('workflow:proposal_detail', kwargs={'pk': item.pk}),
                'cta': 'Xử lý',
            })
        for item in overdue_tasks[:4]:
            action_items.append({
                'tone': 'warning',
                'type': 'Trễ hạn',
                'title': item.tieu_de,
                'meta': f"Hạn {item.han_chot.strftime('%d/%m %H:%M')} · giao bởi {item.nguoi_giao.ho_ten}",
                'time': item.han_chot or item.ngay_tao,
                'url': reverse('workflow:task_detail', kwargs={'pk': item.pk}),
                'cta': 'Cập nhật',
            })
        for item in returned_proposals[:4]:
            action_items.append({
                'tone': 'info',
                'type': 'Cần sửa',
                'title': item.tieu_de,
                'meta': item.get_loai_de_xuat_display(),
                'time': item.ngay_cap_nhat,
                'url': reverse('workflow:proposal_detail', kwargs={'pk': item.pk}),
                'cta': 'Xem góp ý',
            })
        action_items = sorted(action_items, key=lambda x: x['time'], reverse=False)[:8]

        context = {
            'nhan_vien': nhan_vien,
            'department_name': nhan_vien.phong_ban.ten_phong_ban if nhan_vien.phong_ban else 'Chưa gắn phòng ban',
            'is_management_staff': bool(nhan_vien.phong_ban),

            # Backward-compatible context names.
            'my_tasks': my_tasks[:8],
            'my_tasks_count': my_tasks.count(),
            'assigned_tasks': assigned_tasks,
            'my_proposals': my_proposals_qs[:6],
            'pending_approvals': pending_approvals[:8],
            'pending_approvals_count': pending_approvals.count(),

            # Operational metrics for the cross-department workflow dashboard.
            'overdue_tasks_count': overdue_tasks.count(),
            'due_soon_tasks_count': due_soon_tasks.count(),
            'assigned_open_count': Task.objects.filter(nguoi_giao=nhan_vien).exclude(trang_thai__in=[Task.Status.HOAN_THANH, Task.Status.DA_HUY]).count(),
            'my_proposals_count': my_proposals_qs.count(),
            'my_pending_proposals_count': my_proposals_qs.filter(trang_thai=Proposal.Status.CHO_DUYET).count(),
            'returned_proposals_count': returned_proposals.count(),
            'approved_proposals_count': approved_proposals_count,
            'proposal_status_stats': proposal_status_stats,
            'proposal_type_stats': proposal_type_stats,
            'max_type_count': max_type_count,
            'action_items': action_items,
            'urls': {
                'task_create': reverse('workflow:task_create'),
                'task_list': reverse('workflow:task_list'),
                'proposal_create': reverse('workflow:proposal_create'),
                'proposal_list': reverse('workflow:proposal_list'),
            },
        }
        return self.render_dashboard(request, context)

    def render_dashboard(self, request, context):
        from django.shortcuts import render
        return render(request, "workflow/dashboard.html", context)


=======
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View
from django.contrib import messages
from .models import Task, Proposal, PheDuyetLog
from .forms import TaskForm, ProposalForm, ApprovalActionForm
from users.models import NhanVien

class WorkflowDashboardView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            nhan_vien = request.user.nhan_vien
        except:
            messages.error(request, "Tài khoản chưa liên kết nhân viên!")
            return render(request, "workflow/dashboard.html", {})

        my_tasks = Task.objects.filter(nguoi_nhan=nhan_vien).exclude(trang_thai='HOAN_THANH').order_by('han_chot')
        assigned_tasks = Task.objects.filter(nguoi_giao=nhan_vien).order_by('-ngay_tao')[:5]
        my_proposals = Proposal.objects.filter(nguoi_de_xuat=nhan_vien).order_by('-ngay_tao')[:5]
        pending_approvals = Proposal.objects.filter(nguoi_duyet_hien_tai=nhan_vien, trang_thai='CHO_DUYET').order_by('-ngay_tao')

        context = {
            'nhan_vien': nhan_vien,
            'my_tasks': my_tasks, 'my_tasks_count': my_tasks.count(),
            'assigned_tasks': assigned_tasks,
            'my_proposals': my_proposals,
            'pending_approvals': pending_approvals, 'pending_approvals_count': pending_approvals.count(),
        }
        return render(request, "workflow/dashboard.html", context)

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "workflow/task_list.html"
    context_object_name = "tasks"
    paginate_by = 15
<<<<<<< HEAD

    def get_queryset(self):
        try:
            nv = self.request.user.nhan_vien
            return (
                Task.objects
                .filter(Q(nguoi_giao=nv) | Q(nguoi_nhan=nv) | Q(nguoi_phoi_hop=nv))
                .select_related('nguoi_giao', 'nguoi_nhan', 'muc_tieu')
                .prefetch_related('nguoi_phoi_hop')
                .distinct()
                .order_by("-ngay_tao")
            )
        except Exception:
            return Task.objects.none()

=======
    def get_queryset(self):
        try:
            nv = self.request.user.nhan_vien
            return Task.objects.filter(Q(nguoi_giao=nv)|Q(nguoi_nhan=nv)|Q(nguoi_phoi_hop=nv)).distinct().order_by("-ngay_tao")
        except: return Task.objects.none()
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "workflow/task_form.html"
    success_url = reverse_lazy('workflow:task_list')
<<<<<<< HEAD

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    def form_valid(self, form):
        form.instance.nguoi_giao = self.request.user.nhan_vien
        messages.success(self.request, "Đã giao việc.")
        return super().form_valid(form)

<<<<<<< HEAD

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "workflow/task_detail.html"
    context_object_name = "task"

<<<<<<< HEAD

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    template_name = "workflow/task_form.html"
    fields = ["trang_thai", "tien_do", "file_dinh_kem", "noi_dung"]
    success_url = reverse_lazy('workflow:task_list')

<<<<<<< HEAD

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
class ProposalListView(LoginRequiredMixin, ListView):
    model = Proposal
    template_name = "workflow/proposal_list.html"
    context_object_name = "proposals"
    paginate_by = 15
<<<<<<< HEAD

    def get_queryset(self):
        try:
            nv = self.request.user.nhan_vien
            return (
                Proposal.objects
                .filter(Q(nguoi_de_xuat=nv) | Q(nguoi_duyet_hien_tai=nv) | Q(logs__nguoi_xu_ly=nv))
                .select_related('nguoi_de_xuat', 'nguoi_duyet_hien_tai')
                .distinct()
                .order_by("-ngay_tao")
            )
        except Exception:
            return Proposal.objects.none()

=======
    def get_queryset(self):
        try:
            nv = self.request.user.nhan_vien
            return Proposal.objects.filter(Q(nguoi_de_xuat=nv)|Q(nguoi_duyet_hien_tai=nv)|Q(logs__nguoi_xu_ly=nv)).distinct().order_by("-ngay_tao")
        except: return Proposal.objects.none()
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

class ProposalCreateView(LoginRequiredMixin, CreateView):
    model = Proposal
    form_class = ProposalForm
    template_name = "workflow/proposal_form.html"
    success_url = reverse_lazy('workflow:dashboard')
<<<<<<< HEAD

    def form_valid(self, form):
        nv = self.request.user.nhan_vien
        form.instance.nguoi_de_xuat = nv
        if form.instance.nguoi_duyet_hien_tai:
            form.instance.trang_thai = Proposal.Status.CHO_DUYET
        response = super().form_valid(form)
        PheDuyetLog.objects.create(
            proposal=self.object,
            nguoi_xu_ly=nv,
            hanh_dong=PheDuyetLog.Action.GUI,
            y_kien='Khởi tạo và gửi trình',
            nguoi_nhan_tiep_theo=form.instance.nguoi_duyet_hien_tai,
        )
        messages.success(self.request, "Đã gửi đề xuất/tờ trình.")
        return response


=======
    def form_valid(self, form):
        nv = self.request.user.nhan_vien
        form.instance.nguoi_de_xuat = nv
        response = super().form_valid(form)
        PheDuyetLog.objects.create(proposal=self.object, nguoi_xu_ly=nv, hanh_dong='GUI', y_kien='Khởi tạo', nguoi_nhan_tiep_theo=form.instance.nguoi_duyet_hien_tai)
        messages.success(self.request, "Đã gửi tờ trình.")
        return response

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
class ProposalDetailView(LoginRequiredMixin, DetailView):
    model = Proposal
    template_name = "workflow/proposal_detail.html"
    context_object_name = "proposal"
<<<<<<< HEAD

    def get_queryset(self):
        return Proposal.objects.select_related('nguoi_de_xuat', 'nguoi_duyet_hien_tai').prefetch_related('logs')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            if self.object.nguoi_duyet_hien_tai == self.request.user.nhan_vien and self.object.trang_thai == Proposal.Status.CHO_DUYET:
                context['approval_form'] = ApprovalActionForm()
        except Exception:
            pass
        return context


=======
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            if self.object.nguoi_duyet_hien_tai == self.request.user.nhan_vien and self.object.trang_thai == 'CHO_DUYET':
                context['approval_form'] = ApprovalActionForm()
        except: pass
        return context

>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
class ProposalActionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        proposal = get_object_or_404(Proposal, pk=pk)
        current_user = request.user.nhan_vien
        if proposal.nguoi_duyet_hien_tai != current_user:
<<<<<<< HEAD
            messages.error(request, "Bạn không phải người đang thụ lý đề xuất này.")
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
            return redirect('workflow:proposal_detail', pk=pk)
        form = ApprovalActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['hanh_dong']
            note = form.cleaned_data['y_kien']
            next_p = form.cleaned_data['nguoi_tiep_theo']
            log_act = ''
            if action == 'DUYET_KET_THUC':
<<<<<<< HEAD
                proposal.trang_thai = Proposal.Status.DA_DUYET
                proposal.nguoi_duyet_hien_tai = None
                log_act = PheDuyetLog.Action.DUYET
            elif action == 'CHUYEN_TIEP':
                proposal.nguoi_duyet_hien_tai = next_p
                proposal.trang_thai = Proposal.Status.CHO_DUYET
                log_act = PheDuyetLog.Action.CHUYEN
            elif action == 'YEU_CAU_SUA':
                proposal.trang_thai = Proposal.Status.YEU_CAU_SUA
                proposal.nguoi_duyet_hien_tai = proposal.nguoi_de_xuat
                log_act = PheDuyetLog.Action.YEU_CAU_SUA
            elif action == 'TU_CHOI':
                proposal.trang_thai = Proposal.Status.TU_CHOI
                proposal.nguoi_duyet_hien_tai = None
                log_act = PheDuyetLog.Action.TU_CHOI
            proposal.save()
            PheDuyetLog.objects.create(
                proposal=proposal,
                nguoi_xu_ly=current_user,
                hanh_dong=log_act,
                y_kien=note,
                nguoi_nhan_tiep_theo=next_p if action == 'CHUYEN_TIEP' else None,
            )
            messages.success(request, "Đã xử lý đề xuất.")
        return redirect('workflow:proposal_detail', pk=pk)


class ProposalPrintView(LoginRequiredMixin, DetailView):
    model = Proposal
    template_name = "workflow/proposal_print.html"
    context_object_name = "proposal"
=======
                proposal.trang_thai = 'DA_DUYET'
                proposal.nguoi_duyet_hien_tai = None
                log_act = 'DUYET'
            elif action == 'CHUYEN_TIEP':
                proposal.nguoi_duyet_hien_tai = next_p
                log_act = 'CHUYEN'
            elif action == 'YEU_CAU_SUA':
                proposal.trang_thai = 'YEU_CAU_SUA'
                proposal.nguoi_duyet_hien_tai = proposal.nguoi_de_xuat
                log_act = 'YEU_CAU_SUA'
            elif action == 'TU_CHOI':
                proposal.trang_thai = 'TU_CHOI'
                proposal.nguoi_duyet_hien_tai = None
                log_act = 'TU_CHOI'
            proposal.save()
            PheDuyetLog.objects.create(proposal=proposal, nguoi_xu_ly=current_user, hanh_dong=log_act, y_kien=note, nguoi_nhan_tiep_theo=next_p if action == 'CHUYEN_TIEP' else None)
            messages.success(request, "Đã xử lý.")
        return redirect('workflow:proposal_detail', pk=pk)

class ProposalPrintView(LoginRequiredMixin, DetailView):
    model = Proposal
    template_name = "workflow/proposal_print.html"
    context_object_name = "proposal"
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
