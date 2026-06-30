from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(slots=True)
class Stats:
    workflow_runs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    cancelled_jobs: int = 0
    downloaded_bytes: int = 0
    uploaded_bytes: int = 0
    runtime_seconds_total: float = 0.0
    rejected_jobs: int = 0
    validation_failures: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Stats":
        return cls(**data)
