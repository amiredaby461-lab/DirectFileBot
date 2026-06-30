from __future__ import annotations

from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from services.container import ServiceContainer


class IsAdminFilter(BaseFilter):
    def __init__(self, admin_ids: list[int]) -> None:
        self.admin_ids = set(admin_ids)

    async def __call__(self, event: Message | CallbackQuery, **data: Any) -> bool:
        user = event.from_user
        return bool(user and user.id in self.admin_ids)
