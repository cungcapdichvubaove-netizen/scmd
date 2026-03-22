# -*- coding: utf-8 -*-
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

class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "workflow/task_list.html"
    context_object_name = "tasks"
    paginate_by = 15
    def get_queryset(self):
        try:
            nv = self.request.user.nhan_vien
            return Task.objects.filter(Q(nguoi_giao=nv)|Q(nguoi_nhan=nv)|Q(nguoi_phoi_hop=nv)).distinct().order_by("-ngay_tao")
        except: return Task.objects.none()

class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "workflow/task_form.html"
    success_url = reverse_lazy('workflow:task_list')
    def form_valid(self, form):
        form.instance.nguoi_giao = self.request.user.nhan_vien
        messages.success(self.request, "Đã giao việc.")
        return super().form_valid(form)

class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "workflow/task_detail.html"
    context_object_name = "task"

class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    template_name = "workflow/task_form.html"
    fields = ["trang_thai", "tien_do", "file_dinh_kem", "noi_dung"]
    success_url = reverse_lazy('workflow:task_list')

class ProposalListView(LoginRequiredMixin, ListView):
    model = Proposal
    template_name = "workflow/proposal_list.html"
    context_object_name = "proposals"
    paginate_by = 15
    def get_queryset(self):
        try:
            nv = self.request.user.nhan_vien
            return Proposal.objects.filter(Q(nguoi_de_xuat=nv)|Q(nguoi_duyet_hien_tai=nv)|Q(logs__nguoi_xu_ly=nv)).distinct().order_by("-ngay_tao")
        except: return Proposal.objects.none()

class ProposalCreateView(LoginRequiredMixin, CreateView):
    model = Proposal
    form_class = ProposalForm
    template_name = "workflow/proposal_form.html"
    success_url = reverse_lazy('workflow:dashboard')
    def form_valid(self, form):
        nv = self.request.user.nhan_vien
        form.instance.nguoi_de_xuat = nv
        response = super().form_valid(form)
        PheDuyetLog.objects.create(proposal=self.object, nguoi_xu_ly=nv, hanh_dong='GUI', y_kien='Khởi tạo', nguoi_nhan_tiep_theo=form.instance.nguoi_duyet_hien_tai)
        messages.success(self.request, "Đã gửi tờ trình.")
        return response

class ProposalDetailView(LoginRequiredMixin, DetailView):
    model = Proposal
    template_name = "workflow/proposal_detail.html"
    context_object_name = "proposal"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            if self.object.nguoi_duyet_hien_tai == self.request.user.nhan_vien and self.object.trang_thai == 'CHO_DUYET':
                context['approval_form'] = ApprovalActionForm()
        except: pass
        return context

class ProposalActionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        proposal = get_object_or_404(Proposal, pk=pk)
        current_user = request.user.nhan_vien
        if proposal.nguoi_duyet_hien_tai != current_user:
            return redirect('workflow:proposal_detail', pk=pk)
        form = ApprovalActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['hanh_dong']
            note = form.cleaned_data['y_kien']
            next_p = form.cleaned_data['nguoi_tiep_theo']
            log_act = ''
            if action == 'DUYET_KET_THUC':
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