# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.test import TestCase

from reports.access_policies import ReportAccessPolicy


class ReportAccessPolicyStaffBypassTest(TestCase):
    def test_is_staff_alone_does_not_grant_attendance_or_incident_reports(self):
        user = User.objects.create_user(username="staff-only", password="password", is_staff=True)

        self.assertFalse(ReportAccessPolicy.can_view_attendance_reports(user))
        self.assertFalse(ReportAccessPolicy.can_view_incident_reports(user))
