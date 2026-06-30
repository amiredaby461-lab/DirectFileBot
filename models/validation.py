from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    reason: str
    url: str
    domain: str = ""
    file_name: str = ""
    content_type: str = ""
    content_length: int = 0
    accept_ranges: bool = False
    resume_supported: bool = False
    status_code: int = 0
    headers: dict[str, str] = field(default_factory=dict)
