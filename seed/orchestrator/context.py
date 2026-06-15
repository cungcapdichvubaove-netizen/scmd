"""Runtime context shared by Digital Twin factories."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable
import random

from django.conf import settings
from faker import Faker

from .config import DATASET_PREFIX, EXPORT_DIR, SCALES, DatasetScale


@dataclass
class DigitalTwinContext:
    profile: str = "smoke"
    seed: int = 20260609
    incremental: bool = True
    dry_run: bool = False
    batch_size: int = 1000
    suppress_side_effects: bool = True
    export_dir: Path = EXPORT_DIR
    counters: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if self.profile not in SCALES:
            raise ValueError(f"Unknown digital twin profile: {self.profile}")
        self.fake = Faker("vi_VN")
        Faker.seed(self.seed)
        random.seed(self.seed)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    @property
    def scale(self) -> DatasetScale:
        return SCALES[self.profile]

    @property
    def tenant_id(self):
        return settings.SCMD_ORGANIZATION_ID

    def code(self, namespace: str, index: int, width: int = 6) -> str:
        return f"{DATASET_PREFIX}-{namespace}-{index:0{width}d}"

    def count(self, key: str, amount: int = 1):
        self.counters[key] = self.counters.get(key, 0) + amount

    def write_jsonl(self, relative_name: str, rows: Iterable[dict], append: bool = False) -> int:
        import json

        path = self.export_dir / relative_name
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        total = 0
        with path.open(mode, encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                total += 1
        return total
