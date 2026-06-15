from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.conf import settings

from operations.application.dashboard_use_cases import GetOperationsDashboardUseCase


class OperationsDashboardUseCaseArchitectureTest(TestCase):
    @patch("operations.application.dashboard_use_cases.MucTieu.objects")
    @patch("operations.application.dashboard_use_cases.has_role")
    def test_allowed_targets_use_tenant_scoped_manager_for_executive_roles(
        self,
        mock_has_role,
        mock_muc_tieu_objects,
    ):
        user = User.objects.create_user(username="bgd-user", password="password")
        user.nhan_vien = object()
        mock_has_role.side_effect = [True]
        tenant_scoped_qs = mock_muc_tieu_objects.for_tenant.return_value

        allowed_targets_qs = GetOperationsDashboardUseCase._get_allowed_targets_queryset(
            user=user,
            tenant_id=settings.SCMD_ORGANIZATION_ID,
        )

        self.assertEqual(allowed_targets_qs, tenant_scoped_qs)
        mock_muc_tieu_objects.for_tenant.assert_called_once_with(settings.SCMD_ORGANIZATION_ID)
