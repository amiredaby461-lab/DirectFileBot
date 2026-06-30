from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from keyboards.inline import build_admin_keyboard, build_start_keyboard
from models.enums import JobStatus
from services.container import ServiceContainer
from utils.constants import TELEGRAM_MAX_FILE_SIZE_MB
from utils.formatting import escape, human_bytes, human_duration

commands_router = Router(name="commands")


@commands_router.message(Command("start"))
async def start_handler(message: Message, container: ServiceContainer) -> None:
    settings, jobs, users, stats = await container.queue_service.load_all()
    await container.queue_service.ensure_user(users, message.from_user.id, message.from_user.username or "", message.from_user.full_name or "")
    await container.state_repo.save_users(users)

    text = (
        f"👋 <b>خوش آمدید</b>\n\n"
        f"این ربات لینک دانلود مستقیم را می‌گیرد، آن را روی GitHub Actions بررسی و دانلود می‌کند، و فایل را به تلگرام می‌فرستد.\n\n"
        f"روش استفاده:\n"
        f"1) یک لینک مستقیم HTTP/HTTPS بفرستید\n"
        f"2) اعتبارسنجی انجام می‌شود\n"
        f"3) فایل دانلود و ارسال می‌شود"
    )
    await message.answer(text, reply_markup=build_start_keyboard())


@commands_router.message(Command("help"))
async def help_handler(message: Message, container: ServiceContainer) -> None:
    text = (
        "<b>راهنما</b>\n\n"
        "/start — شروع\n"
        "/help — راهنما\n"
        "/status — وضعیت ربات\n"
        "/queue — صف دانلودهای شما\n"
        "/cancel — لغو آخرین job در صف\n"
        "/settings — تنظیمات شما\n"
        "/admin — پنل مدیریت"
    )
    await message.answer(text, reply_markup=build_start_keyboard())


@commands_router.message(Command("status"))
async def status_handler(message: Message, container: ServiceContainer) -> None:
    settings, jobs, users, stats = await container.queue_service.load_all()
    profile = await container.queue_service.ensure_user(users, message.from_user.id, message.from_user.username or "", message.from_user.full_name or "")
    await container.state_repo.save_users(users)
    active = [job for job in jobs if job.status in {JobStatus.PENDING, JobStatus.APPROVED, JobStatus.DOWNLOADING, JobStatus.UPLOADING} and job.user_id == profile.user_id]
    text = (
        f"<b>وضعیت ربات</b>\n\n"
        f"فعال: <code>{'بله' if settings.bot_enabled else 'خیر'}</code>\n"
        f"حالت نگهداری: <code>{'بله' if settings.maintenance_mode else 'خیر'}</code>\n"
        f"تعداد jobهای شما: <code>{len(active)}</code>\n"
        f"تکمیل‌شده: <code>{profile.completed_jobs}</code>\n"
        f"ناموفق: <code>{profile.failed_jobs}</code>\n"
        f"لغوشده: <code>{profile.cancelled_jobs}</code>\n\n"
        f"آمار کلی:\n"
        f"اجراهای workflow: <code>{stats.workflow_runs}</code>\n"
        f"دانلودهای موفق: <code>{stats.completed_jobs}</code>\n"
        f"حجم دانلود شده: <code>{human_bytes(stats.downloaded_bytes)}</code>\n"
        f"حجم آپلود شده: <code>{human_bytes(stats.uploaded_bytes)}</code>\n"
        f"زمان کل اجرا: <code>{human_duration(stats.runtime_seconds_total)}</code>"
    )
    await message.answer(text, reply_markup=build_start_keyboard())


@commands_router.message(Command("queue"))
async def queue_handler(message: Message, container: ServiceContainer) -> None:
    settings, jobs, users, stats = await container.queue_service.load_all()
    profile = await container.queue_service.ensure_user(users, message.from_user.id, message.from_user.username or "", message.from_user.full_name or "")
    await container.state_repo.save_users(users)
    user_jobs = [job for job in jobs if job.user_id == profile.user_id]
    if not user_jobs:
        await message.answer("صف شما خالی است.")
        return
    lines = ["<b>صف شما</b>\n"]
    for job in sorted(user_jobs, key=lambda item: item.created_at):
        lines.append(f"• <code>{escape(job.file_name or job.url)}</code> — <code>{job.status}</code> — <code>{escape(job.id[:8])}</code>")
    await message.answer("\n".join(lines))


@commands_router.message(Command("cancel"))
async def cancel_handler(message: Message, container: ServiceContainer) -> None:
    settings, jobs, users, stats = await container.queue_service.load_all()
    profile = await container.queue_service.ensure_user(users, message.from_user.id, message.from_user.username or "", message.from_user.full_name or "")
    await container.state_repo.save_users(users)
    success, text = await container.queue_service.cancel_job(jobs, users, profile.user_id)
    if success:
        await container.queue_service.save_all(settings, jobs, users, stats)
    await message.answer(text)


@commands_router.message(Command("settings"))
async def settings_handler(message: Message, container: ServiceContainer) -> None:
    settings, jobs, users, stats = await container.queue_service.load_all()
    profile = await container.queue_service.ensure_user(users, message.from_user.id, message.from_user.username or "", message.from_user.full_name or "")
    await container.state_repo.save_users(users)
    text = (
        f"<b>تنظیمات شما</b>\n\n"
        f"Admin: <code>{'بله' if profile.is_admin else 'خیر'}</code>\n"
        f"Allowed: <code>{'بله' if profile.is_allowed else 'خیر'}</code>\n"
        f"Blacklisted: <code>{'بله' if profile.is_blacklisted else 'خیر'}</code>\n"
        f"سقف صف کاربر: <code>{settings.per_user_queue_limit}</code>\n"
        f"حد حجم: <code>{min(max(settings.max_file_size_mb, 1), TELEGRAM_MAX_FILE_SIZE_MB)}</code> MB"
    )
    await message.answer(text)


@commands_router.message(Command("admin"))
async def admin_handler(message: Message, container: ServiceContainer) -> None:
    settings, jobs, users, stats = await container.queue_service.load_all()
    profile = await container.queue_service.ensure_user(users, message.from_user.id, message.from_user.username or "", message.from_user.full_name or "")
    await container.state_repo.save_users(users)
    if not profile.is_admin:
        await message.answer("دسترسی ادمین ندارید.")
        return
    text = (
        "<b>پنل مدیریت</b>\n\n"
        f"کاربران: <code>{len(users)}</code>\n"
        f"Jobs: <code>{len(jobs)}</code>\n"
        f"فعال: <code>{'بله' if settings.bot_enabled else 'خیر'}</code>"
    )
    await message.answer(text, reply_markup=build_admin_keyboard())
