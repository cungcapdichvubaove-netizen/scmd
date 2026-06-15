"""AI camera and alert snapshot factories.

There is no native Camera/AiAlert model in the current Django schema. To avoid
adding migrations or fake tables, this module emits FK-safe JSONL snapshots that
reference real `MucTieu` ids and real `BaoCaoSuCo` ids when available. These
files are deterministic inputs for AI/load tests and can become migration input
when a native camera app exists.
"""

import random
from datetime import timedelta

from django.utils import timezone

from operations.models import BaoCaoSuCo

CAMERA_TYPES = ["AI", "NORMAL", "PTZ"]
ALERT_TYPES = ["intrusion", "loitering", "fire", "ppe_violation", "crowd_detection"]


def seed_ai_alerts(ctx, site_data):
    sites = site_data["sites"]
    cameras = []
    zones = ["Cổng chính", "Hàng rào", "Kho", "Sảnh", "Bãi xe", "Khu kỹ thuật", "Camera AI"]
    for i in range(1, ctx.scale.cameras + 1):
        site = sites[(i - 1) % len(sites)]
        cameras.append({
            "camera_code": ctx.code("CAM", i),
            "site_id": site.id,
            "site_name": site.ten_muc_tieu,
            "zone": zones[i % len(zones)],
            "type": CAMERA_TYPES[i % len(CAMERA_TYPES)],
            "status": random.choice(["ONLINE", "ONLINE", "ONLINE", "MAINTENANCE", "OFFLINE"]),
            "stream_url_stub": f"rtsp://digital-twin.local/{ctx.code('CAM', i)}",
        })
    ctx.write_jsonl("camera/cameras.jsonl", cameras)

    incident_ids = list(BaoCaoSuCo.objects.filter(ma_su_co__startswith="DT-INC-").values_list("id", flat=True)[: max(1, min(50000, ctx.scale.incidents))])
    alerts = []
    for i in range(1, ctx.scale.ai_alerts + 1):
        cam = cameras[(i - 1) % len(cameras)]
        alert_type = random.choice(ALERT_TYPES)
        linked_incident_id = None
        if incident_ids and random.random() < 0.08:
            linked_incident_id = incident_ids[(i - 1) % len(incident_ids)]
        alerts.append({
            "alert_code": ctx.code("AIALERT", i, width=8),
            "camera_code": cam["camera_code"],
            "site_id": cam["site_id"],
            "alert_type": alert_type,
            "confidence": round(random.uniform(0.55, 0.99), 4),
            "severity": random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
            "occurred_at": timezone.now() - timedelta(days=random.randint(0, 36 * 30), seconds=random.randint(0, 86400)),
            "linked_incident_id": linked_incident_id,
        })
    ctx.write_jsonl("ai-alerts/alerts.jsonl", alerts)
    ctx.count("camera_snapshots", len(cameras))
    ctx.count("ai_alert_snapshots", len(alerts))
    return {"cameras": cameras}
