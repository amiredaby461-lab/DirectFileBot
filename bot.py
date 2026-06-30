from __future__ import annotations

import argparse
import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from config import Settings
from handlers.admin import admin_router
from handlers.callbacks import callbacks_router
from handlers.commands import commands_router
from handlers.files import files_router
from middlewares.services import ContainerMiddleware
from repositories.state_repository import StateRepository
from services.container import ServiceContainer
from services.download_service import DownloadService
from services.queue_service import QueueService
from services.telegram_service import TelegramService
from services.url_service import UrlValidationService
from services.workflow_service import WorkflowService
from utils.filesystem import ensure_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Direct file transfer bot for GitHub Actions")
    parser.add_argument("--once", action="store_true", help="Run a single workflow cycle and exit")
    parser.add_argument("--poll-seconds", type=int, default=25, help="Short poll timeout for Telegram getUpdates")
    return parser


def build_dispatcher(container: ServiceContainer) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.update.middleware(ContainerMiddleware(container))
    dispatcher.include_router(commands_router)
    dispatcher.include_router(files_router)
    dispatcher.include_router(callbacks_router)
    dispatcher.include_router(admin_router)
    return dispatcher


async def run_once(container: ServiceContainer, poll_seconds: int = 25) -> None:
    bot = container.bot
    dispatcher = build_dispatcher(container)
    workflow = WorkflowService(container=container, dispatcher=dispatcher, bot=bot, poll_seconds=poll_seconds)
    await workflow.run_cycle()


async def run() -> None:
    load_dotenv()
    settings = Settings.from_env()
    ensure_directory(Path(settings.state_dir))
    ensure_directory(Path(settings.temp_dir))

    if not settings.enabled:
        logging.getLogger(__name__).warning("Bot is disabled by configuration.")
        return

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    state_repo = StateRepository(Path(settings.state_dir))
    container = ServiceContainer(
        settings=settings,
        bot=bot,
        state_repo=state_repo,
        url_service=UrlValidationService(settings=settings),
        download_service=DownloadService(settings=settings),
        telegram_service=TelegramService(settings=settings, bot=bot),
        queue_service=QueueService(settings=settings, state_repo=state_repo),
    )
    container.bind_self()

    parser = build_parser()
    args = parser.parse_args()

    try:
        await run_once(container, poll_seconds=args.poll_seconds)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    asyncio.run(run())
