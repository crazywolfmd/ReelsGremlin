from __future__ import annotations

import os

from platforms.common import analyze_url, download_media

PLATFORM_CODE = "fb"
SUPPORTS_AUDIO = False


def analyze(url: str) -> dict:
    return analyze_url(url, _cookiefile())


def download(url: str, media_type: str, storage_dir, progress_callback=None):
    return download_media(
        url,
        media_type,
        PLATFORM_CODE,
        storage_dir,
        _cookiefile(),
        progress_callback=progress_callback,
    )


def _cookiefile() -> str | None:
    return os.getenv("COOKIES_FACEBOOK") or os.getenv("COOKIES_FILE")
