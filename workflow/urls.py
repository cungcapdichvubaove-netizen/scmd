from django.urls import path
from . import views

app_name = 'workflow'

urlpatterns = [
    path('dashboard/', views.WorkflowDashboardView.as_view(), name='dashboard'),
    path('tasks/', views.TaskListView.as_view(), name='task_list'),
    path('tasks/create/', views.TaskCreateView.as_view(), name='task_create'),
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('tasks/<int:pk>/update/', views.TaskUpdateView.as_view(), name='task_update'),
    path('proposals/', views.ProposalListView.as_view(), name='proposal_list'),
    path('proposals/create/', views.ProposalCreateView.as_view(), name='proposal_create'),
    path('proposals/<int:pk>/', views.ProposalDetailView.as_view(), name='proposal_detail'),
    path('proposals/<int:pk>/action/', views.ProposalActionView.as_view(), name='proposal_action'),
    path('proposals/<int:pk>/print/', views.ProposalPrintView.as_view(), name='proposal_print'),
]