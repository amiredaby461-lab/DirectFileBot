from __future__ import annotations

import asyncio
import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

import aiohttp

from config import Settings
from models.validation import ValidationResult
from utils.constants import TELEGRAM_MAX_FILE_SIZE_MB
from utils.network import is_private_address, is_safe_http_url

_FILENAME_RE = re.compile(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', re.IGNORECASE)


class UrlValidationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _guess_filename(self, url: str, headers: aiohttp.typedefs.LooseHeaders) -> str:
        header_map = {str(key).lower(): str(value) for key, value in headers.items()}
        disposition = header_map.get("content-disposition", "")
        if disposition:
            match = _FILENAME_RE.search(disposition)
            if match:
                candidate = unquote(match.group(1)).strip().strip('"')
                if candidate:
                    return self._sanitize_filename(candidate)
        parsed = urlparse(url)
        candidate = PurePosixPath(parsed.path).name
        if candidate:
            return self._sanitize_filename(unquote(candidate))
        return "downloaded-file"

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        cleaned = name.replace("\\", "_").replace("/", "_").strip()
        return cleaned or "downloaded-file"

    async def validate(self, url: str) -> ValidationResult:
        url = url.strip()
        if not is_safe_http_url(url):
            return ValidationResult(ok=False, reason="فقط لینک‌های HTTP/HTTPS مستقیم پشتیبانی می‌شوند.", url=url)

        parsed = urlparse(url)
        if not parsed.hostname or is_private_address(parsed.hostname):
            return ValidationResult(ok=False, reason="دسترسی به آدرس‌های خصوصی یا محلی مجاز نیست.", url=url)

        timeout = aiohttp.ClientTimeout(total=self.settings.request_timeout_seconds)
        headers = {"User-Agent": self.settings.user_agent, "Accept": "*/*"}

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            try:
                async with session.head(url, allow_redirects=False) as resp:
                    response_headers = {k.lower(): v for k, v in resp.headers.items()}
                    content_type = response_headers.get("content-type", "")
                    content_length = int(response_headers.get("content-length", "0") or 0)
                    accept_ranges = response_headers.get("accept-ranges", "").lower() == "bytes"

                    if resp.status != 200:
                        return ValidationResult(
                            ok=False,
                            reason=f"لینک قابل دسترسی نیست. کد پاسخ: {resp.status}",
                            url=url,
                            domain=parsed.hostname or "",
                            status_code=resp.status,
                            headers=response_headers,
                        )

                    if not content_type:
                        return ValidationResult(ok=False, reason="Content-Type نامعتبر است.", url=url, domain=parsed.hostname or "")

                    lowered = content_type.lower()
                    if "text/html" in lowered or "application/xhtml+xml" in lowered:
                        return ValidationResult(
                            ok=False,
                            reason="این لینک یک صفحه HTML است، نه فایل مستقیم.",
                            url=url,
                            domain=parsed.hostname or "",
                            content_type=content_type,
                            content_length=content_length,
                            accept_ranges=accept_ranges,
                            resume_supported=accept_ranges,
                            status_code=resp.status,
                            headers=response_headers,
                        )

                    if content_length <= 0:
                        return ValidationResult(
                            ok=False,
                            reason="Content-Length معتبر دریافت نشد.",
                            url=url,
                            domain=parsed.hostname or "",
                            content_type=content_type,
                            content_length=content_length,
                            accept_ranges=accept_ranges,
                            resume_supported=accept_ranges,
                            status_code=resp.status,
                            headers=response_headers,
                        )

                    effective_limit_mb = min(max(self.settings.max_file_size_mb, 1), TELEGRAM_MAX_FILE_SIZE_MB)
                    if content_length > effective_limit_mb * 1024 * 1024:
                        return ValidationResult(
                            ok=False,
                            reason="حجم فایل از محدودیت مجاز بیشتر است.",
                            url=url,
                            domain=parsed.hostname or "",
                            content_type=content_type,
                            content_length=content_length,
                            accept_ranges=accept_ranges,
                            resume_supported=accept_ranges,
                            status_code=resp.status,
                            headers=response_headers,
                        )

                    file_name = self._guess_filename(url, resp.headers)
                    return ValidationResult(
                        ok=True,
                        reason="لینک معتبر است.",
                        url=url,
                        domain=parsed.hostname or "",
                        file_name=file_name,
                        content_type=content_type,
                        content_length=content_length,
                        accept_ranges=accept_ranges,
                        resume_supported=accept_ranges,
                        status_code=resp.status,
                        headers=response_headers,
                    )
            except asyncio.TimeoutError:
                return ValidationResult(ok=False, reason="تایم‌اوت هنگام بررسی لینک.", url=url, domain=parsed.hostname or "")
            except aiohttp.ClientError:
                return ValidationResult(ok=False, reason="خطای شبکه هنگام بررسی لینک.", url=url, domain=parsed.hostname or "")
            except Exception:
                return ValidationResult(ok=False, reason="خطای غیرمنتظره در اعتبارسنجی.", url=url, domain=parsed.hostname or "")
