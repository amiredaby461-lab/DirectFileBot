from __future__ import annotations

import html
from datetime import timedelta
from math import ceil


def escape(text: str | None) -> str:
    return html.escape(text or "", quote=False)


def human_bytes(value: int | float | None) -> str:
    if value is None or value <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    amount = float(value)
    while amount >= 1024 and index < len(units) - 1:
        amount /= 1024
        index += 1
    if amount >= 100:
        return f"{amount:.0f} {units[index]}"
    if amount >= 10:
        return f"{amount:.1f} {units[index]}"
    return f"{amount:.2f} {units[index]}"


def human_duration(seconds: float | int | None) -> str:
    if seconds is None or seconds < 0:
        return "0s"
    td = timedelta(seconds=int(seconds))
    total = int(td.total_seconds())
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def progress_bar(current: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return "░" * width
    ratio = max(0.0, min(1.0, current / total))
    filled = min(width, int(round(ratio * width)))
    return "█" * filled + "░" * (width - filled)


def pct(current: int, total: int) -> str:
    if total <= 0:
        return "0%"
    return f"{min(100, max(0, ceil((current / total) * 100)))}%"


def format_rate(bytes_per_second: float | int | None) -> str:
    if not bytes_per_second or bytes_per_second <= 0:
        return "0 B/s"
    return f"{human_bytes(bytes_per_second)}/s"
