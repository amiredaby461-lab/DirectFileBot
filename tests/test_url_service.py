from __future__ import annotations

from utils.network import is_safe_http_url


def test_http_url():
    assert is_safe_http_url("https://example.com/file.zip")


def test_reject_ftp():
    assert not is_safe_http_url("ftp://example.com/file.zip")
