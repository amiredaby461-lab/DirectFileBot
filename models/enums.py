from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    VALIDATING = "validating"
    DOWNLOADING = "downloading"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FileKind(StrEnum):
    DIRECT = "direct"
    HTML = "html"
    INVALID = "invalid"
