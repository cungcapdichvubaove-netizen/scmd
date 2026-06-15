"""Digital Twin dataset scale contracts for SCMD Pro.

The generator is intentionally profile-driven: smoke/small profiles are used by
CI and local validation, while the full profile encodes the requested enterprise
scale. Counts are deterministic and idempotent.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetScale:
    staff: int
    customers: int
    contracts: int
    sites: int
    warehouses: int
    asset_units: int
    cameras: int
    checkpoints: int
    patrol_routes: int
    patrol_history: int
    incidents: int
    ai_alerts: int
    finance_months: int = 36


SCALES = {
    "smoke": DatasetScale(60, 8, 12, 10, 12, 300, 80, 120, 20, 250, 300, 800, 6),
    "small": DatasetScale(250, 25, 40, 30, 40, 2500, 500, 800, 100, 5000, 5000, 25000, 12),
    "full": DatasetScale(1200, 80, 160, 100, 120, 20000, 4000, 5000, 500, 50000, 150000, 500000, 36),
}

DEFAULT_PROFILE = "smoke"
EXPORT_DIR = Path("var/digital_twin")
DATASET_PREFIX = "DT"
