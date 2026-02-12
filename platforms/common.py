from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def analyze_url(url: str, cookiefile: str | None = None) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }
    if cookiefile:
        opts["cookiefile"] = cookiefile

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "description": info.get("description"),
        "thumbnail": _thumbnail(info),
        "duration": info.get("duration"),
        "uploader": info.get("uploader") or info.get("channel"),
        "tags": info.get("tags") or [],
        "webpage_url": info.get("webpage_url") or url,
    }


def download_media(
    url: str,
    media_type: str,
    platform_code: str,
    storage_dir: Path,
    cookiefile: str | None = None,
) -> dict[str, str]:
    storage_dir.mkdir(parents=True, exist_ok=True)

    base = f"{platform_code}_{media_type}_{timestamp()}"
    outtmpl = str(storage_dir / f"{base}.%(ext)s")

    fmt = "bestaudio/best" if media_type == "audio" else "bestvideo+bestaudio/best"

    opts: dict[str, Any] = {
        "format": fmt,
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    if cookiefile:
        opts["cookiefile"] = cookiefile

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    file_path = _resolve_file_path(info, storage_dir)

    ext = file_path.suffix.lower()
    mime = _mime(ext, media_type)

    return {
        "file_path": str(file_path),
        "file_name": file_path.name,
        "mime_type": mime,
    }


def _resolve_file_path(info: dict[str, Any], storage_dir: Path) -> Path:
    requested = info.get("requested_downloads") or []
    if requested:
        path = requested[0].get("filepath")
        if path:
            return Path(path)

    fallback = info.get("_filename")
    if fallback:
        return Path(fallback)

    files = sorted([p for p in storage_dir.glob("*") if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
    if files:
        return files[0]

    raise FileNotFoundError("Downloaded file was not found.")


def _thumbnail(info: dict[str, Any]) -> str | None:
    t = info.get("thumbnail")
    if t:
        return str(t)
    thumbs = info.get("thumbnails") or []
    if thumbs:
        return str(thumbs[-1].get("url"))
    return None


def _mime(ext: str, media_type: str) -> str:
    if media_type == "audio":
        if ext == ".mp3":
            return "audio/mpeg"
        if ext == ".m4a":
            return "audio/mp4"
        return "audio/*"

    if ext in {".mp4", ".m4v"}:
        return "video/mp4"
    if ext == ".webm":
        return "video/webm"
    return "video/*"
