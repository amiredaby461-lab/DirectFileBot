from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from keyboards.inline import build_file_preview_keyboard
from models.job import Job
from services.container import ServiceContainer
from utils.constants import TELEGRAM_MAX_FILE_SIZE_MB
from utils.formatting import escape, human_bytes

files_router = Router(name="files")


def _looks_like_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")


@files_router.message(F.text)
async def file_link_handler(message: Message, container: ServiceContainer) -> None:
    text = (message.text or "").strip()
    if text.startswith("/"):
        return
    if not _looks_like_url(text):
        return

    settings, jobs, users, stats = await container.queue_service.load_all()
    profile = await container.queue_service.ensure_user(users, message.from_user.id, message.from_user.username or "", message.from_user.full_name or "")
    await container.state_repo.save_users(users)

    validation = await container.url_service.validate(text)
    if not validation.ok:
        await message.answer(f"❌ {validation.reason}")
        stats.validation_failures += 1
        await container.queue_service.save_all(settings, jobs, users, stats)
        return

    job = Job(
        user_id=profile.user_id,
        chat_id=message.chat.id,
        message_id=message.message_id,
        url=validation.url,
        domain=validation.domain,
        file_name=validation.file_name,
        content_type=validation.content_type,
        file_size=validation.content_length,
        accept_ranges=validation.accept_ranges,
        approved=True,
    )
    success, queue_message = await container.queue_service.enqueue_job(jobs, users, profile, job)
    if not success:
        await message.answer(f"⚠️ {queue_message}")
        stats.rejected_jobs += 1
        await container.queue_service.save_all(settings, jobs, users, stats)
        return

    preview_text = (
        f"<b>اطلاعات فایل</b>\n\n"
        f"نام فایل: <code>{escape(job.file_name)}</code>\n"
        f"حجم: <code>{human_bytes(job.file_size)}</code>\n"
        f"نوع فایل: <code>{escape(job.content_type)}</code>\n"
        f"دامنه: <code>{escape(job.domain)}</code>\n"
        f"Resume: <code>{'بله' if job.accept_ranges else 'خیر'}</code>\n"
        f"وضعیت لینک: <code>معتبر</code>\n"
    )
    preview = await message.answer(preview_text, reply_markup=build_file_preview_keyboard(job.id))
    job.preview_message_id = preview.message_id
    await container.queue_service.save_all(settings, jobs, users, stats)
