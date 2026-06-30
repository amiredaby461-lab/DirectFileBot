from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class JobCallback(CallbackData, prefix="job"):
    action: str
    job_id: str


class MenuCallback(CallbackData, prefix="menu"):
    action: str


def build_start_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📥 ارسال لینک", callback_data=MenuCallback(action="send_link").pack())
    kb.button(text="📂 دانلودهای من", callback_data=MenuCallback(action="my_queue").pack())
    kb.button(text="📊 وضعیت", callback_data=MenuCallback(action="status").pack())
    kb.button(text="⚙️ تنظیمات", callback_data=MenuCallback(action="settings").pack())
    kb.button(text="📚 راهنما", callback_data=MenuCallback(action="help").pack())
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def build_file_preview_keyboard(job_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ شروع دانلود", callback_data=JobCallback(action="start", job_id=job_id).pack())
    kb.button(text="❌ لغو", callback_data=JobCallback(action="cancel", job_id=job_id).pack())
    kb.adjust(2)
    return kb.as_markup()


def build_queue_keyboard(job_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ لغو", callback_data=JobCallback(action="cancel", job_id=job_id).pack())
    kb.adjust(1)
    return kb.as_markup()


def build_admin_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="♻️ بازخوانی", callback_data=MenuCallback(action="admin_refresh").pack())
    kb.button(text="⏻ فعال/غیرفعال", callback_data=MenuCallback(action="toggle_bot").pack())
    kb.button(text="📊 آمار", callback_data=MenuCallback(action="admin_stats").pack())
    kb.adjust(2, 1)
    return kb.as_markup()


def build_default_keyboards() -> None:
    return None
