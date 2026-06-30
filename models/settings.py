from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any


@dataclass(slots=True)
class AppSettings:
    bot_enabled: bool = True
    maintenance_mode: bool = False
    max_file_size_mb: int = 1950
    per_user_queue_limit: int = 5
    download_retry: int = 3
    upload_retry: int = 3
    poll_timeout_seconds: int = 25
    workflow_sleep_seconds: int = 5
    allowed_user_ids: list[int] = field(default_factory=list)
    blacklisted_user_ids: list[int] = field(default_factory=list)
    admin_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        return cls(**data)
