from __future__ import annotations

from datetime import datetime, timezone

from config import Settings
from models.enums import JobStatus
from models.job import Job
from models.settings import AppSettings
from models.stats import Stats
from models.user import UserProfile
from repositories.state_repository import StateRepository


class QueueService:
    def __init__(self, settings: Settings, state_repo: StateRepository) -> None:
        self.settings = settings
        self.state_repo = state_repo

    async def load_all(self) -> tuple[AppSettings, list[Job], dict[str, UserProfile], Stats]:
        settings = await self.state_repo.load_settings(
            AppSettings(
                bot_enabled=self.settings.enabled,
                max_file_size_mb=self.settings.max_file_size_mb,
                per_user_queue_limit=self.settings.per_user_queue_limit,
                download_retry=self.settings.download_retry,
                upload_retry=self.settings.upload_retry,
                poll_timeout_seconds=self.settings.poll_timeout_seconds,
                workflow_sleep_seconds=self.settings.workflow_sleep_seconds,
                allowed_user_ids=list(self.settings.allowed_user_ids),
                blacklisted_user_ids=list(self.settings.blacklisted_user_ids),
                admin_ids=list(self.settings.admin_ids),
            )
        )
        jobs = await self.state_repo.load_jobs()
        users = await self.state_repo.load_users()
        stats = await self.state_repo.load_stats(Stats())
        return settings, jobs, users, stats

    async def save_all(self, settings: AppSettings, jobs: list[Job], users: dict[str, UserProfile], stats: Stats) -> None:
        await self.state_repo.save_settings(settings)
        await self.state_repo.save_jobs(jobs)
        await self.state_repo.save_users(users)
        await self.state_repo.save_stats(stats)

    async def ensure_user(self, users: dict[str, UserProfile], user_id: int, username: str, full_name: str) -> UserProfile:
        key = str(user_id)
        profile = users.get(key)
        if profile is None:
            profile = UserProfile(user_id=user_id, username=username, full_name=full_name)
            users[key] = profile
        profile.username = username
        profile.full_name = full_name
        profile.is_admin = user_id in self.settings.admin_ids
        profile.is_blacklisted = user_id in self.settings.blacklisted_user_ids
        profile.is_allowed = not self.settings.allowed_user_ids or user_id in self.settings.allowed_user_ids
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        return profile

    async def enqueue_job(
        self,
        jobs: list[Job],
        users: dict[str, UserProfile],
        profile: UserProfile,
        job: Job,
    ) -> tuple[bool, str]:
        if profile.is_blacklisted:
            return False, "کاربر در لیست سیاه است."
        if not profile.is_allowed:
            return False, "این کاربر مجاز به استفاده از ربات نیست."
        active_jobs = [
            item
            for item in jobs
            if item.user_id == profile.user_id
            and item.status in {JobStatus.PENDING, JobStatus.APPROVED, JobStatus.VALIDATING, JobStatus.DOWNLOADING, JobStatus.UPLOADING}
        ]
        if len(active_jobs) >= self.settings.per_user_queue_limit:
            return False, "صف این کاربر به سقف مجاز رسیده است."
        if any(item.url == job.url and item.status not in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED} for item in jobs):
            return False, "این لینک قبلاً در حال پردازش یا در صف است."
        jobs.append(job)
        profile.total_jobs += 1
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        return True, "در صف قرار گرفت."

    async def list_user_jobs(self, jobs: list[Job], user_id: int) -> list[Job]:
        return [job for job in jobs if job.user_id == user_id]

    async def get_next_job(self, jobs: list[Job], users: dict[str, UserProfile]) -> Job | None:
        for job in sorted(jobs, key=lambda item: item.created_at):
            profile = users.get(str(job.user_id))
            if profile is None:
                continue
            if profile.active_job_id and profile.active_job_id != job.id:
                continue
            if job.cancelled or job.status in {JobStatus.CANCELLED, JobStatus.COMPLETED, JobStatus.FAILED}:
                continue
            if job.status in {JobStatus.PENDING, JobStatus.APPROVED}:
                return job
        return None

    async def mark_active(self, jobs: list[Job], users: dict[str, UserProfile], job: Job) -> None:
        profile = users.get(str(job.user_id))
        if profile:
            profile.active_job_id = job.id
            profile.updated_at = datetime.now(timezone.utc).isoformat()
        job.status = JobStatus.APPROVED
        job.updated_at = datetime.now(timezone.utc).isoformat()

    async def clear_active(self, jobs: list[Job], users: dict[str, UserProfile], job: Job) -> None:
        profile = users.get(str(job.user_id))
        if profile and profile.active_job_id == job.id:
            profile.active_job_id = ""
            profile.updated_at = datetime.now(timezone.utc).isoformat()

    async def cancel_job(self, jobs: list[Job], users: dict[str, UserProfile], user_id: int, job_id: str | None = None) -> tuple[bool, str]:
        target: Job | None = None
        if job_id:
            for job in jobs:
                if job.id == job_id and job.user_id == user_id:
                    target = job
                    break
        else:
            for job in reversed(jobs):
                if job.user_id == user_id and job.status in {JobStatus.PENDING, JobStatus.APPROVED, JobStatus.VALIDATING}:
                    target = job
                    break
        if target is None:
            return False, "وظیفه‌ای برای لغو پیدا نشد."
        target.status = JobStatus.CANCELLED
        target.cancelled = True
        await self.clear_active(jobs, users, target)
        target.updated_at = datetime.now(timezone.utc).isoformat()
        return True, "لغو شد."

    async def finalize_job(self, jobs: list[Job], users: dict[str, UserProfile], job: Job, status: JobStatus, error: str = "") -> None:
        job.status = status
        job.error = error
        job.finished_at = datetime.now(timezone.utc).isoformat()
        job.updated_at = job.finished_at
        profile = users.get(str(job.user_id))
        if profile:
            profile.active_job_id = ""
            profile.updated_at = job.finished_at
            if status == JobStatus.COMPLETED:
                profile.completed_jobs += 1
            elif status == JobStatus.CANCELLED:
                profile.cancelled_jobs += 1
            else:
                profile.failed_jobs += 1
