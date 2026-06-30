from __future__ import annotations

import asyncio
import json
from pathlib import Path
from time import monotonic
from typing import Any, Awaitable, Callable

import aiohttp
from aiogram import Bot

from config import Settings
from utils.constants import TELEGRAM_MAX_FILE_SIZE_MB
from utils.formatting import escape, human_bytes, human_duration, pct, progress_bar


ProgressCallback = Callable[[int, int, float], Awaitable[None] | None]


class TelegramUploadError(RuntimeError):
    pass


class _StreamFilePayload(aiohttp.payload.Payload):
    def __init__(self, path: Path, progress_callback: ProgressCallback | None = None) -> None:
        super().__init__(path, content_type="application/octet-stream")
        self._path = path
        self._progress_callback = progress_callback

    async def write(self, writer: aiohttp.abc.AbstractStreamWriter) -> None:
        total = self._path.stat().st_size
        transferred = 0
        started = monotonic()
        with self._path.open("rb") as fp:
            while True:
                chunk = fp.read(64 * 1024)
                if not chunk:
                    break
                await writer.write(chunk)
                transferred += len(chunk)
                if self._progress_callback:
                    maybe = self._progress_callback(transferred, total, monotonic() - started)
                    if asyncio.iscoroutine(maybe):
                        await maybe


class TelegramService:
    def __init__(self, settings: Settings, bot: Bot) -> None:
        self.settings = settings
        self.bot = bot

    async def send_message(self, chat_id: int, text: str, reply_markup=None) -> Any:
        return await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    async def edit_message(self, chat_id: int, message_id: int, text: str, reply_markup=None) -> Any:
        try:
            return await self.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
        except Exception:
            return None

    async def delete_message(self, chat_id: int, message_id: int) -> None:
        try:
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass

    async def send_preview(self, chat_id: int, text: str, reply_markup=None, disable_web_page_preview: bool = True) -> Any:
        return await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_web_page_preview,
        )

    async def progress_message(
        self,
        chat_id: int,
        message_id: int,
        title: str,
        transferred: int,
        total: int,
        speed: str,
        eta: str,
        elapsed: str,
    ) -> Any:
        text = (
            f"<b>{escape(title)}</b>\n\n"
            f"{progress_bar(transferred, total)} {pct(transferred, total)}\n"
            f"حجم ارسال/دانلود: <code>{human_bytes(transferred)}</code> از <code>{human_bytes(total)}</code>\n"
            f"سرعت: <code>{escape(speed)}</code>\n"
            f"زمان باقی‌مانده: <code>{escape(eta)}</code>\n"
            f"زمان سپری‌شده: <code>{escape(elapsed)}</code>"
        )
        return await self.edit_message(chat_id, message_id, text)

    async def upload_document(
        self,
        chat_id: int,
        file_path: Path,
        file_name: str,
        caption: str,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        url = f"{self.settings.telegram_api_base}/bot{self.settings.bot_token}/sendDocument"
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=self.settings.request_timeout_seconds, sock_read=None)

        max_bytes = min(max(self.settings.max_file_size_mb, 1), TELEGRAM_MAX_FILE_SIZE_MB) * 1024 * 1024
        if file_path.stat().st_size > max_bytes:
            raise TelegramUploadError(f"File exceeds Telegram upload cap ({max_bytes // (1024 * 1024)} MB)")

        async with aiohttp.ClientSession(timeout=timeout) as session:
            last_error: Exception | None = None
            for attempt in range(1, max(1, self.settings.upload_retry) + 1):
                try:
                    form = aiohttp.MultipartWriter("form-data")
                    p_chat = form.append(str(chat_id))
                    p_chat.set_content_disposition("form-data", name="chat_id")

                    p_doc = form.append_payload(_StreamFilePayload(file_path, progress_callback))
                    p_doc.set_content_disposition("form-data", name="document", filename=file_name)
                    p_doc.headers[aiohttp.hdrs.CONTENT_TYPE] = "application/octet-stream"

                    p_caption = form.append(caption)
                    p_caption.set_content_disposition("form-data", name="caption")
                    p_parse = form.append("HTML")
                    p_parse.set_content_disposition("form-data", name="parse_mode")

                    async with session.post(url, data=form) as resp:
                        text = await resp.text()
                        if resp.status != 200:
                            raise TelegramUploadError(f"Telegram API HTTP {resp.status}: {text}")
                        payload = json.loads(text)
                        if not payload.get("ok"):
                            raise TelegramUploadError(payload.get("description", "Telegram upload failed"))
                        return payload
                except Exception as exc:
                    last_error = exc
                    await asyncio.sleep(1.0 * attempt)
                    continue
        raise TelegramUploadError(str(last_error) if last_error else "Upload failed")
