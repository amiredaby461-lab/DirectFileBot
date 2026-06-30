from __future__ import annotations

from dataclasses import dataclass, field

from aiogram import Bot

from config import Settings
from repositories.state_repository import StateRepository
from services.download_service import DownloadService
from services.queue_service import QueueService
from services.telegram_service import TelegramService
from services.url_service import UrlValidationService


@dataclass(slots=True)
class ServiceContainer:
    settings: Settings
    bot: Bot
    state_repo: StateRepository
    url_service: UrlValidationService
    download_service: DownloadService
    telegram_service: TelegramService
    queue_service: QueueService
    _bound: bool = field(default=False, init=False)

    def bind_self(self) -> None:
        self._bound = True
