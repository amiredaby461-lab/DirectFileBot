from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from models.enums import JobStatus


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Job:
    id: str = field(default_factory=lambda: uuid4().hex)
    user_id: int = 0
    chat_id: int = 0
    message_id: int = 0
    url: str = ""
    domain: str = ""
    file_name: str = ""
    content_type: str = ""
    file_size: int = 0
    accept_ranges: bool = False
    status: JobStatus = JobStatus.PENDING
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    started_at: str = ""
    finished_at: str = ""
    preview_message_id: int = 0
    progress_message_id: int = 0
    local_path: str = ""
    error: str = ""
    download_attempts: int = 0
    upload_attempts: int = 0
    approved: bool = True
    cancelled: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        payload = dict(data)
        payload["status"] = JobStatus(payload.get("status", JobStatus.PENDING))
        return cls(**payload)
