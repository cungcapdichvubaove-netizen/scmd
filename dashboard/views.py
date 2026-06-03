# -*- coding: utf-8 -*-
"""
SCMD ERP executive dashboard.
"""

import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings
from dashboard.application.executive_dashboard import GetExecutiveDashboardUseCase


@login_required
def dashboard_main(request):
    # SSOT: Logic nghiệp vụ được tách biệt hoàn toàn khỏi View theo Rule 3.2
    tenant_id = settings.SCMD_ORGANIZATION_ID
    
    # Orchestrate data through Use Case
    context = GetExecutiveDashboardUseCase.execute(request.user, tenant_id)
    
    # Convert chart data to JSON for Template
    context["chart_labels"] = json.dumps(context.get("chart_labels", []))
    context["data_su_co"] = json.dumps(context.get("data_su_co", []))
    context["data_doanh_thu"] = json.dumps(context.get("data_doanh_thu", []))

    return render(request, "dashboard/main.html", context)
