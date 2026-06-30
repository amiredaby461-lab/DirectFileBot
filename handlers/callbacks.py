from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Router
from aiogram.types import CallbackQuery

from keyboards.inline import JobCallback, MenuCallback, build_admin_keyboard
from models.enums import JobStatus
from services.container import ServiceContainer
from utils.constants import TELEGRAM_MAX_FILE_SIZE_MB
from utils.formatting import escape

callbacks_router = Router(name="callbacks")


@callbacks_router.callback_query(JobCallback.filter())
async def job_callback_handler(query: CallbackQuery, callback_data: JobCallback, container: ServiceContainer) -> None:
    settings, jobs, users, stats = await container.queue_service.load_all()
    profile = await container.queue_service.ensure_user(users, query.from_user.id, query.from_user.username or "", query.from_user.full_name or "")
    await container.state_repo.save_users(users)

    job = next((item for item in jobs if item.id == callback_data.job_id and item.user_id == profile.user_id), None)
    if job is None:
        await query.answer("وظیفه پیدا نشد.", show_alert=True)
        return

    if callback_data.action == "cancel":
        success, text = await container.queue_service.cancel_job(jobs, users, profile.user_id, job.id)
        if success:
            await container.queue_service.save_all(settings, jobs, users, stats)
            if job.preview_message_id:
                await container.telegram_service.edit_message(job.chat_id, job.preview_message_id, f"❌ {text}")
        await query.answer(text, show_alert=not success)
        return

    if callback_data.action == "start":
        job.approved = True
        job.status = JobStatus.APPROVED
        job.updated_at = datetime.now(timezone.utc).isoformat()
        await container.queue_service.save_all(settings, jobs, users, stats)
        await query.answer("دانلود شروع می‌شود.")
        return


@callbacks_router.callback_query(MenuCallback.filter())
async def menu_callback_handler(query: CallbackQuery, callback_data: MenuCallback, container: ServiceContainer) -> None:
    settings, jobs, users, stats = await container.queue_service.load_all()
    profile = await container.queue_service.ensure_user(users, query.from_user.id, query.from_user.username or "", query.from_user.full_name or "")
    await container.state_repo.save_users(users)

    if callback_data.action == "status":
        text = (
            f"<b>وضعیت</b>\n\n"
            f"فعال: <code>{'بله' if settings.bot_enabled else 'خیر'}</code>\n"
            f"کاربر: <code>{escape(profile.full_name)}</code>"
        )
        await query.message.edit_text(text, reply_markup=build_admin_keyboard() if profile.is_admin else None)
        await query.answer()
        return

    if callback_data.action == "help":
        await query.message.edit_text("برای استفاده کافی است لینک مستقیم HTTP/HTTPS را ارسال کنید.")
        await query.answer()
        return

    if callback_data.action == "send_link":
        await query.message.edit_text("لینک مستقیم را همین حالا ارسال کنید.")
        await query.answer()
        return

    if callback_data.action == "my_queue":
        user_jobs = [job for job in jobs if job.user_id == profile.user_id]
        if not user_jobs:
            await query.message.edit_text("صف شما خالی است.")
            await query.answer()
            return
        lines = ["<b>صف شما</b>\n"]
        for job in sorted(user_jobs, key=lambda item: item.created_at):
            lines.append(f"• <code>{escape(job.file_name or job.url)}</code> — <code>{job.status}</code>")
        await query.message.edit_text("\n".join(lines))
        await query.answer()
        return

    if callback_data.action == "settings":
        await query.message.edit_text(
            f"<b>تنظیمات</b>\n\n"
            f"سقف صف: <code>{settings.per_user_queue_limit}</code>\n"
            f"حد حجم: <code>{min(max(settings.max_file_size_mb, 1), TELEGRAM_MAX_FILE_SIZE_MB)}</code> MB"
        )
        await query.answer()
        return

    if callback_data.action == "admin_refresh":
        if not profile.is_admin:
            await query.answer("دسترسی ندارید.", show_alert=True)
            return
        await query.message.edit_text("پنل مدیریت به‌روزرسانی شد.", reply_markup=build_admin_keyboard())
        await query.answer()
        return

    if callback_data.action == "toggle_bot":
        if not profile.is_admin:
            await query.answer("دسترسی ندارید.", show_alert=True)
            return
        settings.bot_enabled = not settings.bot_enabled
        await container.queue_service.save_all(settings, jobs, users, stats)
        await query.message.edit_text(
            f"فعال/غیرفعال: <code>{'بله' if settings.bot_enabled else 'خیر'}</code>",
            reply_markup=build_admin_keyboard(),
        )
        await query.answer()
        return

    if callback_data.action == "admin_stats":
        if not profile.is_admin:
            await query.answer("دسترسی ندارید.", show_alert=True)
            return
        await query.message.edit_text(
            f"<b>آمار</b>\n\n"
            f"Workflow: <code>{stats.workflow_runs}</code>\n"
            f"Completed: <code>{stats.completed_jobs}</code>\n"
            f"Failed: <code>{stats.failed_jobs}</code>\n"
            f"Rejected: <code>{stats.rejected_jobs}</code>",
            reply_markup=build_admin_keyboard(),
        )
        await query.answer()
        return

    await query.answer()
