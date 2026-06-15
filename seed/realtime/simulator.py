"""Realtime Digital Twin event simulator."""

import random
import time
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from main.models import AuditLog
from operations.models import BaoCaoSuCo, ChamCong, PhanCongCaTruc


@dataclass(frozen=True)
class RealtimeProfile:
    events_per_tick: int
    sleep_seconds: float


REALTIME_PROFILES = {
    "LOW": RealtimeProfile(events_per_tick=5, sleep_seconds=2.0),
    "MEDIUM": RealtimeProfile(events_per_tick=25, sleep_seconds=1.0),
    "HIGH": RealtimeProfile(events_per_tick=150, sleep_seconds=0.5),
    "EXTREME": RealtimeProfile(events_per_tick=750, sleep_seconds=0.1),
}

EVENT_TYPES = ["gps", "patrol_event", "camera_alert", "incident", "attendance"]


def run_realtime_simulation(level="LOW", ticks=10, dry_run=False, stdout=None):
    profile = REALTIME_PROFILES[level]
    assignments = list(PhanCongCaTruc.objects.select_related("nhan_vien", "vi_tri_chot__muc_tieu")[:5000])
    incidents = list(BaoCaoSuCo.objects.only("id", "ma_su_co")[:5000])
    emitted = 0
    for tick in range(ticks):
        for _ in range(profile.events_per_tick):
            event_type = random.choice(EVENT_TYPES)
            assignment = random.choice(assignments) if assignments else None
            payload = {
                "event_type": event_type,
                "tick": tick,
                "assignment_id": getattr(assignment, "id", None),
                "site_id": getattr(getattr(getattr(assignment, "vi_tri_chot", None), "muc_tieu", None), "id", None),
                "incident_id": getattr(random.choice(incidents), "id", None) if incidents else None,
                "ts": timezone.now().isoformat(),
            }
            if not dry_run:
                AuditLog.objects.create(
                    action=AuditLog.Action.EXECUTE,
                    module="digital_twin",
                    model_name="RealtimeSimulationEvent",
                    object_id=str(payload.get("assignment_id") or payload.get("incident_id") or tick),
                    changes=payload,
                    note="Digital Twin realtime synthetic event",
                )
            emitted += 1
        if stdout:
            stdout.write(f"tick={tick + 1}/{ticks}; emitted={emitted}")
        if tick < ticks - 1:
            time.sleep(profile.sleep_seconds)
    return emitted
