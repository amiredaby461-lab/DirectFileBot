from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from aiogram import Bot, Dispatcher

from models.enums import JobStatus
from models.job import Job
from models.settings import AppSettings
from models.stats import Stats
from models.user import UserProfile
from services.container import ServiceContainer
from utils.constants import TELEGRAM_MAX_FILE_SIZE_MB
from utils.filesystem import ensure_directory, remove_tree
from utils.formatting import escape, human_bytes, human_duration
from keyboards.inline import build_file_preview_keyboard

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProcessResult:
    processed_jobs: int = 0
    processed_updates: int = 0


class WorkflowService:
    def __init__(self, container: ServiceContainer, dispatcher: Dispatcher, bot: Bot, poll_seconds: int = 25) -> None:
        self.container = container
        self.dispatcher = dispatcher
        self.bot = bot
        self.poll_seconds = poll_seconds

    async def run_cycle(self) -> ProcessResult:
        started = perf_counter()
        queue_service = self.container.queue_service
        state_repo = self.container.state_repo

        settings, jobs, users, stats = await queue_service.load_all()
        cursor = await state_repo.load_cursor()
        stats.workflow_runs += 1

        await self._recover_stuck_jobs(jobs, users, stats)

        updates = await self.bot.get_updates(
            offset=cursor.last_update_id + 1 if cursor.last_update_id else None,
            timeout=max(0, min(self.poll_seconds, 30)),
            allowed_updates=["message", "callback_query"],
        )

        processed_updates = 0
        for update in updates:
            try:
                await self.dispatcher.feed_update(self.bot, update)
            except Exception as exc:
                logger.exception("Failed to process update %s: %s", update.update_id, exc)
            finally:
                cursor.last_update_id = update.update_id
                processed_updates += 1

        await state_repo.save_cursor(cursor)

        processed_jobs = await self._process_jobs(settings, jobs, users, stats)

        stats.runtime_seconds_total += perf_counter() - started
        await queue_service.save_all(settings, jobs, users, stats)
        await state_repo.log(
            f"cycle processed_updates={processed_updates} processed_jobs={processed_jobs} runtime={stats.runtime_seconds_total:.2f}"
        )
        return ProcessResult(processed_jobs=processed_jobs, processed_updates=processed_updates)

    async def _recover_stuck_jobs(self, jobs: list[Job], users: dict[str, UserProfile], stats: Stats) -> None:
        for job in jobs:
            if job.status in {JobStatus.DOWNLOADING, JobStatus.UPLOADING, JobStatus.VALIDATING}:
                job.status = JobStatus.FAILED
                job.error = "Workflow restarted before completion."
                job.finished_at = datetime.now(timezone.utc).isoformat()
                job.updated_at = job.finished_at
                stats.failed_jobs += 1
                await self.container.queue_service.clear_active(jobs, users, job)

    async def _process_jobs(self, settings: AppSettings, jobs: list[Job], users: dict[str, UserProfile], stats: Stats) -> int:
        processed = 0
        queue_service = self.container.queue_service

        while True:
            job = await queue_service.get_next_job(jobs, users)
            if job is None:
                break

            if job.cancelled or job.status == JobStatus.CANCELLED:
                await queue_service.finalize_job(jobs, users, job, JobStatus.CANCELLED)
                stats.cancelled_jobs += 1
                continue

            processed += 1
            await queue_service.mark_active(jobs, users, job)

            try:
                await self._execute_job(job, jobs, users, settings, stats)
                await queue_service.finalize_job(jobs, users, job, JobStatus.COMPLETED)
                stats.completed_jobs += 1
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Job failed: %s", exc)
                await queue_service.finalize_job(jobs, users, job, JobStatus.FAILED, error=str(exc))
                stats.failed_jobs += 1
            finally:
                temp_path = Path(self.container.settings.temp_dir) / job.id
                remove_tree(temp_path)

        return processed

    async def _execute_job(
        self,
        job: Job,
        jobs: list[Job],
        users: dict[str, UserProfile],
        settings: AppSettings,
        stats: Stats,
    ) -> None:
        telegram = self.container.telegram_service
        download_service = self.container.download_service
        temp_path = Path(self.container.settings.temp_dir) / job.id
        ensure_directory(temp_path)

        preview_text = (
            f"<b>اطلاعات فایل</b>\n\n"
            f"نام فایل: <code>{escape(job.file_name)}</code>\n"
            f"حجم: <code>{human_bytes(job.file_size)}</code>\n"
            f"نوع: <code>{escape(job.content_type)}</code>\n"
            f"دامنه: <code>{escape(job.domain)}</code>\n"
            f"Resume: <code>{'بله' if job.accept_ranges else 'خیر'}</code>\n"
        )

        if job.preview_message_id:
            await telegram.edit_message(job.chat_id, job.preview_message_id, f"⬇️ شروع دانلود...\n\n{preview_text}")
        else:
            preview = await telegram.send_preview(
                job.chat_id,
                f"⬇️ شروع دانلود...\n\n{preview_text}",
                reply_markup=build_file_preview_keyboard(job.id),
            )
            job.preview_message_id = preview.message_id

        job.status = JobStatus.DOWNLOADING
        job.started_at = job.started_at or datetime.now(timezone.utc).isoformat()

        download_path = temp_path / job.file_name
        last_download_ui = 0
        download_started = perf_counter()

        async def download_progress(transferred: int, total: int, elapsed: float) -> None:
            nonlocal last_download_ui
            if job.preview_message_id and (total == 0 or transferred == total or transferred - last_download_ui >= 512 * 1024):
                last_download_ui = transferred
                speed = transferred / elapsed if elapsed > 0 else 0.0
                remaining = max(total - transferred, 0)
                eta = remaining / speed if speed > 0 else 0.0
                await telegram.progress_message(
                    job.chat_id,
                    job.preview_message_id,
                    f"دانلود {job.file_name}",
                    transferred,
                    total,
                    f"{human_bytes(speed)}/s",
                    human_duration(eta),
                    human_duration(elapsed),
                )

        await download_service.download(job, download_path, download_progress)
        download_seconds = perf_counter() - download_started
        downloaded_size = download_path.stat().st_size if download_path.exists() else 0
        stats.downloaded_bytes += downloaded_size

        if job.preview_message_id:
            await telegram.edit_message(job.chat_id, job.preview_message_id, f"⬆️ شروع آپلود...\n\n{preview_text}")

        job.status = JobStatus.UPLOADING
        last_upload_ui = 0
        upload_started = perf_counter()

        async def upload_progress(transferred: int, total: int, elapsed: float) -> None:
            nonlocal last_upload_ui
            if job.preview_message_id and (total == 0 or transferred == total or transferred - last_upload_ui >= 512 * 1024):
                last_upload_ui = transferred
                speed = transferred / elapsed if elapsed > 0 else 0.0
                remaining = max(total - transferred, 0)
                eta = remaining / speed if speed > 0 else 0.0
                await telegram.progress_message(
                    job.chat_id,
                    job.preview_message_id,
                    f"آپلود {job.file_name}",
                    transferred,
                    total,
                    f"{human_bytes(speed)}/s",
                    human_duration(eta),
                    human_duration(elapsed),
                )

        max_bytes = min(max(settings.max_file_size_mb or TELEGRAM_MAX_FILE_SIZE_MB, 1), TELEGRAM_MAX_FILE_SIZE_MB) * 1024 * 1024
        if downloaded_size > max_bytes:
            raise RuntimeError(f"File exceeds Telegram upload cap ({max_bytes // (1024 * 1024)} MB)")

        await telegram.upload_document(
            chat_id=job.chat_id,
            file_path=download_path,
            file_name=job.file_name,
            caption=(
                f"✅ <b>فایل با موفقیت ارسال شد.</b>\n\n"
                f"نام فایل: <code>{escape(job.file_name)}</code>\n"
                f"حجم فایل: <code>{human_bytes(downloaded_size)}</code>\n"
                f"مدت دانلود: <code>{human_duration(download_seconds)}</code>\n"
                f"مدت آپلود: <code>{human_duration(perf_counter() - upload_started)}</code>\n"
                f"زمان کل عملیات: <code>{human_duration(perf_counter() - download_started)}</code>\n"
            ),
            progress_callback=upload_progress,
        )
        stats.uploaded_bytes += downloaded_size
        job.finished_at = datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _elapsed_seconds(start_iso: str) -> float:
        try:
            start = datetime.fromisoformat(start_iso)
            return max(0.0, (datetime.now(timezone.utc) - start).total_seconds())
        except Exception:
            return 0.0
