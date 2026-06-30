from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

import os


def _parse_id_list(value: str | None) -> list[int]:
    if not value:
        return []
    items: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        items.append(int(part))
    return items


@dataclass(slots=True)
class Settings:
    bot_token: str
    bot_username: str = ""
    bot_name: str = "Direct File Transfer Bot"
    enabled: bool = True
    state_dir: str = "state"
    temp_dir: str = "temp"
    admin_ids: list[int] = field(default_factory=list)
    allowed_user_ids: list[int] = field(default_factory=list)
    blacklisted_user_ids: list[int] = field(default_factory=list)
    max_file_size_mb: int = 1950
    per_user_queue_limit: int = 5
    download_retry: int = 3
    upload_retry: int = 3
    poll_timeout_seconds: int = 25
    workflow_sleep_seconds: int = 5
    request_timeout_seconds: int = 25
    user_agent: str = "DirectFileTransferBot/1.0"
    telegram_api_base: str = "https://api.telegram.org"

    @classmethod
    def from_env(cls) -> Self:
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            raise RuntimeError("BOT_TOKEN is not configured")

        enabled = os.getenv("ENABLE_BOT", "1").strip() not in {"0", "false", "False"}
        return cls(
            bot_token=bot_token,
            bot_username=os.getenv("BOT_USERNAME", "").strip(),
            bot_name=os.getenv("BOT_NAME", "Direct File Transfer Bot").strip(),
            enabled=enabled,
            state_dir=os.getenv("STATE_DIR", "state").strip(),
            temp_dir=os.getenv("TEMP_DIR", "temp").strip(),
            admin_ids=_parse_id_list(os.getenv("ADMIN_IDS")),
            allowed_user_ids=_parse_id_list(os.getenv("ALLOWED_USER_IDS")),
            blacklisted_user_ids=_parse_id_list(os.getenv("BLACKLISTED_USER_IDS")),
            max_file_size_mb=min(max(int(os.getenv("DEFAULT_MAX_FILE_SIZE_MB", "1950")), 1), 1950),
            per_user_queue_limit=int(os.getenv("DEFAULT_PER_USER_QUEUE_LIMIT", "5")),
            download_retry=int(os.getenv("DEFAULT_DOWNLOAD_RETRY", "3")),
            upload_retry=int(os.getenv("DEFAULT_UPLOAD_RETRY", "3")),
            poll_timeout_seconds=int(os.getenv("DEFAULT_POLL_TIMEOUT_SECONDS", "25")),
            workflow_sleep_seconds=int(os.getenv("DEFAULT_WORKFLOW_SLEEP_SECONDS", "5")),
            request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "25")),
            user_agent=os.getenv("USER_AGENT", "DirectFileTransferBot/1.0").strip(),
        )

    @property
    def state_path(self) -> Path:
        return Path(self.state_dir)

    @property
    def temp_path(self) -> Path:
        return Path(self.temp_dir)
