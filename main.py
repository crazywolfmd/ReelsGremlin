from __future__ import annotations

import logging
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from platforms import facebook, instagram, tiktok, youtube


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.getenv("APP_LOG_FILE", "app.log"), encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Reels Gremlin", page_icon="RG", layout="centered")

TEMP_DIR = Path(os.getenv("TEMP_DOWNLOAD_DIR", ".tmp_downloads"))
TEMP_TTL_SECONDS = int(os.getenv("TEMP_TTL_SECONDS", "600"))


def ensure_temp_dir() -> None:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def sweep_temp_files() -> None:
    ensure_temp_dir()
    cutoff = time.time() - TEMP_TTL_SECONDS
    for file_path in TEMP_DIR.glob("*"):
        if not file_path.is_file():
            continue
        try:
            if file_path.stat().st_mtime < cutoff:
                file_path.unlink(missing_ok=True)
        except OSError:
            continue


def delete_file(path_str: str | None) -> None:
    if not path_str:
        return
    try:
        path = Path(path_str)
        if path.exists() and path.is_file():
            path.unlink(missing_ok=True)
    except OSError:
        return


def platform_registry() -> dict[str, Any]:
    return {
        "YouTube": youtube,
        "Facebook": facebook,
        "Instagram": instagram,
        "TikTok": tiktok,
    }


def init_state() -> None:
    if "analysis" not in st.session_state:
        st.session_state.analysis = None
    if "analysis_url" not in st.session_state:
        st.session_state.analysis_url = ""
    if "prepared" not in st.session_state:
        st.session_state.prepared = None


def clear_prepared() -> None:
    prepared = st.session_state.get("prepared")
    if prepared:
        delete_file(prepared.get("file_path"))
    st.session_state.prepared = None


def render_metadata(result: dict[str, Any]) -> None:
    if result.get("thumbnail"):
        st.image(result["thumbnail"], width="stretch")

    st.subheader(result.get("title") or "Untitled")
    st.write("**Description**")
    st.write(result.get("description") or "No description")


def media_options(module: Any) -> list[str]:
    if getattr(module, "SUPPORTS_AUDIO", True):
        return ["video", "audio"]
    return ["video"]


def _progress_label(media_type: str, data: dict[str, Any]) -> str:
    percent = data.get("percent")
    downloaded = _format_bytes(data.get("downloaded_bytes"))
    total = _format_bytes(data.get("total_bytes"))
    if isinstance(percent, (int, float)):
        if downloaded and total:
            return f"{media_type.capitalize()} download: {percent:.1f}% ({downloaded} / {total})"
        return f"{media_type.capitalize()} download: {percent:.1f}%"

    percent_str = data.get("percent_str")
    if isinstance(percent_str, str):
        match = re.search(r"[0-9]+(?:\\.[0-9]+)?", percent_str)
        if match:
            return f"{media_type.capitalize()} download: {match.group(0)}%"
    return f"Downloading {media_type}..."


def _format_bytes(value: Any) -> str | None:
    if not isinstance(value, (int, float)) or value < 0:
        return None
    size = float(value)
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)}{unit}"
            return f"{size:.2f}{unit}"
        size /= 1024.0
    return None


def prepare_download(module: Any, url: str, media_type: str) -> None:
    clear_prepared()
    sweep_temp_files()
    progress_text = st.empty()
    progress_bar = st.progress(0.0, text=f"Starting {media_type} download...")

    with st.spinner(f"Preparing {media_type} file..."):
        try:
            def on_progress(data: dict[str, Any]) -> None:
                status = data.get("status")
                if status == "downloading":
                    progress_label = _progress_label(media_type, data)
                    percent = data.get("percent")
                    if isinstance(percent, (int, float)):
                        value = min(max(float(percent) / 100.0, 0.0), 1.0)
                        progress_bar.progress(value, text=progress_label)
                    else:
                        progress_text.info(progress_label)
                elif status == "finished":
                    progress_bar.progress(1.0, text="Download complete. Finalizing file...")

            prepared = module.download(
                url,
                media_type,
                TEMP_DIR,
                progress_callback=on_progress,
            )
            st.session_state.prepared = prepared
            progress_text.empty()
            st.success(f"{media_type.capitalize()} is ready.")
        except Exception:
            logger.exception("Download preparation failed for %s", media_type)
            progress_text.empty()
            st.error(f"Failed to prepare {media_type} file.")


def render_download_section(module: Any, url: str) -> None:
    st.write("**Downloads**")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Download Video 🎬", width="stretch"):
            prepare_download(module, url, "video")

    with col2:
        if "audio" in media_options(module):
            if st.button("Download Audio 🎵", width="stretch"):
                prepare_download(module, url, "audio")

    prepared = st.session_state.get("prepared")
    if prepared:
        file_path = Path(prepared["file_path"])
        if not file_path.exists():
            st.warning("Prepared file is no longer available. Prepare it again.")
            st.session_state.prepared = None
            return

        with file_path.open("rb") as handle:
            st.download_button(
                label=f"Save {file_path.suffix.lstrip('.').upper() or 'file'}",
                data=handle,
                file_name=prepared["file_name"],
                mime=prepared["mime_type"],
                width="stretch",
            )

        st.caption(
            f"Temporary file auto-cleanup: {TEMP_TTL_SECONDS // 60} minutes."
        )


def main() -> None:
    init_state()
    sweep_temp_files()

    st.markdown("### Reels Gremlin")
    st.caption("Analyze and download content from major platforms")
    if shutil.which("ffmpeg") is None:
        st.warning("ffmpeg is not installed. Video/audio merge downloads may fail.")
    st.divider()

    platforms = platform_registry()
    selected_platform = st.selectbox("Select platform", list(platforms.keys()))

    st.divider()
    url = st.text_input("Paste content URL", placeholder="https://...")

    analyze_button = st.button("Analyze Content", width="stretch")
    if analyze_button:
        if not url.strip():
            st.warning("Please provide a URL.")
        else:
            clear_prepared()
            with st.spinner("Analyzing content..."):
                try:
                    module = platforms[selected_platform]
                    result = module.analyze(url.strip())
                    st.session_state.analysis = result
                    st.session_state.analysis_url = url.strip()
                    st.success("Content analyzed successfully.")
                except Exception as exc:
                    logger.exception("Analysis failed")
                    st.session_state.analysis = None
                    st.error("Failed to analyze URL. Check the link and try again.")

    result = st.session_state.get("analysis")
    analysis_url = st.session_state.get("analysis_url")
    if result and analysis_url:
        render_metadata(result)
        st.divider()
        render_download_section(platforms[selected_platform], analysis_url)


if __name__ == "__main__":
    main()
