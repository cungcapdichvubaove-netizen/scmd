# -*- coding: utf-8 -*-
"""Admin-only HTTP views for SCMD Pro.

Views live in the interface layer.  Application/search logic stays in
``main.services`` so the Django Admin shell remains layered and testable.
"""

from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from main.services.admin_global_search import run_admin_global_search


@staff_member_required
def admin_global_search_view(request: HttpRequest) -> HttpResponse:
    """One-result-page global search for Django Admin."""

    context = run_admin_global_search(request, request.GET.get("q", ""))
    return render(request, "admin/global_search.html", context)
