from __future__ import annotations

import asyncio
from pathlib import Path
from time import monotonic
from typing import Awaitable, Callable

import aiohttp

from config import Settings
from utils.constants import TELEGRAM_MAX_FILE_SIZE_MB
from models.job import Job
from utils.filesystem import ensure_directory, remove_file


ProgressCallback = Callable[[int, int, float], Awaitable[None] | None]


class DownloadError(RuntimeError):
    pass


class DownloadService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def download(self, job: Job, destination: Path, progress_callback: ProgressCallback | None = None) -> Path:
        ensure_directory(destination.parent)
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=self.settings.request_timeout_seconds, sock_read=None)
        base_headers = {"User-Agent": self.settings.user_agent, "Accept": "*/*"}
        existing = destination.stat().st_size if destination.exists() else 0

        async with aiohttp.ClientSession(timeout=timeout, headers=base_headers) as session:
            last_error: Exception | None = None
            for attempt in range(1, max(1, self.settings.download_retry) + 1):
                job.download_attempts = attempt
                headers = dict(base_headers)
                if existing > 0 and job.accept_ranges:
                    headers["Range"] = f"bytes={existing}-"
                try:
                    async with session.get(job.url, allow_redirects=False, headers=headers) as resp:
                        if resp.status not in {200, 206}:
                            raise DownloadError(f"HTTP {resp.status}")
                        if resp.status == 200 and existing > 0:
                            remove_file(destination)
                            existing = 0
                        total = self._total_size(resp, job.file_size, existing)
                        transferred = existing
                        started = monotonic()
                        mode = "ab" if resp.status == 206 and existing > 0 else "wb"
                        with destination.open(mode) as fp:
                            async for chunk in resp.content.iter_chunked(64 * 1024):
                                if job.cancelled:
                                    raise asyncio.CancelledError()
                                fp.write(chunk)
                                transferred += len(chunk)
                                if self.settings.max_file_size_mb > 0:
                                    effective_limit = min(max(self.settings.max_file_size_mb, 1), TELEGRAM_MAX_FILE_SIZE_MB)
                                    if transferred > effective_limit * 1024 * 1024:
                                        raise DownloadError(f"File exceeds Telegram upload cap ({effective_limit} MB)")
                                if progress_callback:
                                    maybe = progress_callback(transferred, total, monotonic() - started)
                                    if asyncio.iscoroutine(maybe):
                                        await maybe
                        if total > 0 and transferred < total:
                            raise DownloadError("Incomplete download")
                        return destination
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    last_error = exc
                    if destination.exists():
                        existing = destination.stat().st_size
                    await asyncio.sleep(1.0 * attempt)
                    continue
        raise DownloadError(str(last_error) if last_error else "Download failed")

    @staticmethod
    def _total_size(resp: aiohttp.ClientResponse, fallback: int, existing: int) -> int:
        content_range = resp.headers.get("Content-Range", "")
        if content_range and "/" in content_range:
            total_part = content_range.split("/")[-1]
            if total_part.isdigit():
                return int(total_part)
        content_length = resp.headers.get("Content-Length", "")
        if content_length.isdigit():
            return existing + int(content_length)
        return fallback
