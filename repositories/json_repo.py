from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, TypeVar

from utils.filesystem import read_json, write_json

T = TypeVar("T")


class JsonRepository:
    def __init__(self, base_path: Path, filename: str, default: Any) -> None:
        self._path = base_path / filename
        self._default = default

    @property
    def path(self) -> Path:
        return self._path

    async def load(self) -> Any:
        return await read_json(self._path, self._default)

    async def save(self, data: Any) -> None:
        await write_json(self._path, data)
