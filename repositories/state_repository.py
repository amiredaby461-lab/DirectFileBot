from __future__ import annotations

from pathlib import Path
from typing import Any

from models.cursor import UpdateCursor
from models.job import Job
from models.settings import AppSettings
from models.stats import Stats
from models.user import UserProfile
from utils.constants import (
    STATE_CURSOR_FILE,
    STATE_LOGS_FILE,
    STATE_QUEUE_FILE,
    STATE_SETTINGS_FILE,
    STATE_STATS_FILE,
    STATE_USERS_FILE,
)
from utils.filesystem import append_text, read_json, write_json


class StateRepository:
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.settings_path = base_path / STATE_SETTINGS_FILE
        self.queue_path = base_path / STATE_QUEUE_FILE
        self.users_path = base_path / STATE_USERS_FILE
        self.stats_path = base_path / STATE_STATS_FILE
        self.cursor_path = base_path / STATE_CURSOR_FILE
        self.logs_path = base_path / STATE_LOGS_FILE

    async def load_settings(self, default: AppSettings) -> AppSettings:
        raw = await read_json(self.settings_path, default.to_dict())
        return AppSettings.from_dict(raw)

    async def save_settings(self, settings: AppSettings) -> None:
        await write_json(self.settings_path, settings.to_dict())

    async def load_jobs(self) -> list[Job]:
        raw = await read_json(self.queue_path, [])
        return [Job.from_dict(item) for item in raw]

    async def save_jobs(self, jobs: list[Job]) -> None:
        await write_json(self.queue_path, [job.to_dict() for job in jobs])

    async def load_users(self) -> dict[str, UserProfile]:
        raw = await read_json(self.users_path, {})
        return {key: UserProfile.from_dict(value) for key, value in raw.items()}

    async def save_users(self, users: dict[str, UserProfile]) -> None:
        await write_json(self.users_path, {key: value.to_dict() for key, value in users.items()})

    async def load_stats(self, default: Stats) -> Stats:
        raw = await read_json(self.stats_path, default.to_dict())
        return Stats.from_dict(raw)

    async def save_stats(self, stats: Stats) -> None:
        await write_json(self.stats_path, stats.to_dict())

    async def load_cursor(self) -> UpdateCursor:
        raw = await read_json(self.cursor_path, {"last_update_id": 0})
        return UpdateCursor.from_dict(raw)

    async def save_cursor(self, cursor: UpdateCursor) -> None:
        await write_json(self.cursor_path, cursor.to_dict())

    async def log(self, line: str) -> None:
        await append_text(self.logs_path, line.rstrip() + "\n")
