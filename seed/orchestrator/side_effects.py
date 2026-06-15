"""Signal side-effect controls for deterministic Digital Twin seeding.

Digital Twin seeding creates thousands to hundreds of thousands of operational
records. Production signals on those records intentionally fan out Celery jobs,
WebSocket notifications and cache invalidations. That behavior is correct during
normal runtime, but it is unsafe during bulk seed because it can flood Redis,
block the management command and generate noisy realtime alerts.

This module suppresses only realtime/async side effects for the duration of the
seed command. It does not disconnect profile creation or business validation.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterable, Tuple

from django.db.models.signals import post_delete, post_save

from operations.models import BaoCaoSuCo, ChamCong, PhanCongCaTruc
from operations.models import KiemTraQuanSo
from operations import signals as operation_signals


@dataclass(frozen=True)
class SignalBinding:
    signal: object
    receiver: Callable
    sender: object


OPERATIONAL_SIDE_EFFECT_SIGNALS: Tuple[SignalBinding, ...] = (
    SignalBinding(post_save, operation_signals.handle_su_co_changes, BaoCaoSuCo),
    SignalBinding(post_save, operation_signals.broadcast_attendance, ChamCong),
    SignalBinding(post_save, operation_signals.handle_alive_check_broadcast, KiemTraQuanSo),
    SignalBinding(post_save, operation_signals.invalidate_dashboard_on_shift_assignment_change, PhanCongCaTruc),
    SignalBinding(post_delete, operation_signals.invalidate_dashboard_on_delete, BaoCaoSuCo),
    SignalBinding(post_delete, operation_signals.invalidate_dashboard_on_delete, ChamCong),
    SignalBinding(post_delete, operation_signals.invalidate_dashboard_on_delete, PhanCongCaTruc),
)


@contextmanager
def suppress_operational_side_effects(enabled: bool = True):
    """Temporarily disconnect expensive realtime/async operational signals.

    The context is idempotent and reconnects receivers in a finally block. It is
    intentionally scoped to operations runtime signals only; user profile signal
    handlers remain connected because seed_hr relies on them to create/update
    NhanVien profiles safely.
    """
    if not enabled:
        yield
        return

    disconnected: Iterable[SignalBinding] = []
    disconnected = []
    for binding in OPERATIONAL_SIDE_EFFECT_SIGNALS:
        binding.signal.disconnect(receiver=binding.receiver, sender=binding.sender)
        disconnected.append(binding)

    try:
        yield
    finally:
        for binding in disconnected:
            binding.signal.connect(receiver=binding.receiver, sender=binding.sender, weak=False)
