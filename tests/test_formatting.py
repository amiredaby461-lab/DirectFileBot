from __future__ import annotations

from utils.formatting import human_bytes, progress_bar


def test_human_bytes():
    assert human_bytes(1024) == "1.00 KB"


def test_progress_bar():
    assert len(progress_bar(50, 100)) == 12
