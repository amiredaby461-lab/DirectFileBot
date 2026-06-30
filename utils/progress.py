from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic

from utils.formatting import format_rate, human_bytes, human_duration, pct, progress_bar


@dataclass(slots=True)
class ProgressState:
    started_at: float = field(default_factory=monotonic)
    last_update_at: float = 0.0
    transferred: int = 0
    total: int = 0

    def snapshot(self, transferred: int, total: int) -> dict[str, str]:
        now = monotonic()
        elapsed = max(0.001, now - self.started_at)
        speed = transferred / elapsed
        remaining = max(total - transferred, 0)
        eta = remaining / speed if speed > 0 else 0
        self.transferred = transferred
        self.total = total
        self.last_update_at = now
        return {
            "bar": progress_bar(transferred, total),
            "percent": pct(transferred, total),
            "transferred": human_bytes(transferred),
            "total": human_bytes(total),
            "speed": format_rate(speed),
            "eta": human_duration(eta),
            "elapsed": human_duration(elapsed),
        }
