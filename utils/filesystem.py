from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any


async def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default

    def _read() -> Any:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)

    return await asyncio.to_thread(_read)


async def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def _write() -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
            fp.write("\n")
        os.replace(tmp_path, path)

    await asyncio.to_thread(_write)


async def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def _append() -> None:
        with path.open("a", encoding="utf-8") as fp:
            fp.write(text)

    await asyncio.to_thread(_append)


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def remove_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
