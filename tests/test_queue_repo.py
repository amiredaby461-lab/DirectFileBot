from __future__ import annotations

import asyncio
from pathlib import Path

from config import Settings
from models.job import Job
from models.user import UserProfile
from repositories.state_repository import StateRepository
from services.queue_service import QueueService


async def _run(tmp_path: Path):
    settings = Settings(bot_token="x", admin_ids=[1])
    repo = StateRepository(tmp_path)
    qs = QueueService(settings, repo)
    settings_state, jobs, users, stats = await qs.load_all()
    profile = await qs.ensure_user(users, 1, "u", "n")
    job = Job(user_id=1, chat_id=1, url="https://example.com/a", file_name="a.bin", content_type="application/octet-stream", file_size=10)
    ok, _ = await qs.enqueue_job(jobs, users, profile, job)
    assert ok
    await qs.save_all(settings_state, jobs, users, stats)
    loaded = await repo.load_jobs()
    assert len(loaded) == 1


def test_queue_repo(tmp_path: Path):
    asyncio.run(_run(tmp_path))
