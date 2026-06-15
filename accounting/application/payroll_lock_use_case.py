from django.conf import settings
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.translation import gettext_lazy as _
from rolepermissions.checkers import has_role
from accounting.models import BangLuongThang
from accounting.services.payroll import PayrollService
from main.models import AuditLog

class LockPayrollUseCase:
    """
    Application Use Case xử lý việc khóa bảng lương.
    Tập trung logic chuyển đổi trạng thái, quản lý giao dịch và ghi audit log.
    
    Refactor này giải quyết nợ kỹ thuật P1 khi logic nghiệp vụ bị rò rỉ vào View.
    Tuân thủ WHITEPAPER.md Mục 6.2 (Payroll reconciliation) và 7.3 (State Machine).
    """

    @staticmethod
    def execute(payroll_id: int, actor_user, tenant_id: str, reason: str = "") -> tuple[BangLuongThang, bool]:
        """
        Thực hiện khóa bảng lương và ghi nhận vào hệ thống kiểm toán.
        """
        # Rule 8: Permission & Audit Governance
        if not (actor_user.is_superuser or has_role(actor_user, ['ban_giam_doc', 'ke_toan'])):
            raise PermissionDenied(_("Bạn không có quyền thực hiện hành động khóa bảng lương."))

        if str(tenant_id) != str(settings.SCMD_ORGANIZATION_ID):
            raise PermissionDenied(_("Không được khóa bảng lương ngoài phạm vi tổ chức hiện tại."))

        staff_profile = getattr(actor_user, "nhan_vien", None)
        if staff_profile is not None and str(staff_profile.tenant_id) != str(settings.SCMD_ORGANIZATION_ID):
            raise PermissionDenied(_("Tài khoản không thuộc tổ chức hiện tại."))

        with transaction.atomic():
            try:
                # select_for_update để ngăn chặn race condition khi nhiều người cùng thao tác
                payroll = BangLuongThang.objects.for_tenant(tenant_id).select_for_update().get(id=payroll_id)
            except BangLuongThang.DoesNotExist:
                raise ValidationError(_("Bảng lương không tồn tại."))

            # Kiểm tra máy trạng thái (State Machine Guard)
            # Nếu đã khóa hoặc đã thanh toán, không làm gì thêm (idempotency)
            if payroll.trang_thai in [BangLuongThang.TrangThai.LOCKED, BangLuongThang.TrangThai.PAID]:
                return payroll, False

            # Rule 6.2: Operational Truth - Chặn khóa nếu thiếu dữ liệu đối soát
            details = payroll.chi_tiet.select_related('nhan_vien').all()
            if not details.exists():
                raise ValidationError(_("Bảng lương chưa có dữ liệu chi tiết, không thể khóa."))
            
            for detail in details:
                # Đảm bảo đã có snapshot tính toán (chứa rate baseline, đơn giá, ...)
                if not detail.nguon_du_lieu_snapshot:
                    raise ValidationError(_(
                        f"Phiếu lương nhân viên {detail.nhan_vien.ho_ten} thiếu dữ liệu snapshot đối soát. "
                        "Vui lòng tính toán lại bảng lương trước khi khóa kỳ."
                    ))

            old_status = payroll.trang_thai
            payroll.trang_thai = BangLuongThang.TrangThai.LOCKED
            payroll.save(update_fields=['trang_thai'])

            # SSOT: Thực hiện khóa các hồ sơ vận hành liên quan (Rule 6.2)
            success, msg = PayrollService.lock_related_records(payroll)
            if not success:
                raise ValidationError(_(f"Lỗi khi khóa các bản ghi liên quan: {msg}"))

            # Ghi Audit log bắt buộc theo WHITEPAPER.md Mục 8.2
            AuditLog.objects.create(
                user=actor_user,
                action=AuditLog.Action.EXECUTE,
                module="Accounting",
                model_name="BangLuongThang",
                object_id=str(payroll.id),
                tenant_id=tenant_id,
                note=f"Khóa bảng lương tháng {payroll.thang}/{payroll.nam}. Lý do: {reason}",
                changes={
                    "before": old_status, 
                    "after": payroll.trang_thai,
                    "reason": reason,
                }
            )
            
            return payroll, True