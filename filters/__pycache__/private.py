from __future__ import annotations

from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import Message


class PrivateChatFilter(BaseFilter):
    async def __call__(self, message: Message, **data: Any) -> bool:
        return message.chat.type == "private"
