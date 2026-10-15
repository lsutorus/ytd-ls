"""Backend module for YouTube video extraction and downloading using yt-dlp and FFmpeg.

This module provides headless functions and option builders that can be unit-tested
independently of any GUI framework.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Callable

from PIL import Image
import yt_dlp
from yt_dlp.utils import download_range_func

def get_config_path(config_path: Path | None = None) -> Path:
    """Return persistent user config path in APPDATA or provided path."""
    if config_path:
        return config_path
    appdata = os.environ.get("APPDATA")
    if appdata:
        base_dir = Path(appdata) / "YouTubeDownloaderLS"
        # Migrate from legacy directory if needed
        legacy_cfg = Path(appdata) / "YouTubeDownloader" / "config.json"
        if not (base_dir / "config.json").is_file() and legacy_cfg.is_file():
            base_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(legacy_cfg, base_dir / "config.json")
            except Exception:
                pass
    else:
        base_dir = Path.home() / ".youtubedownloaderls"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "config.json"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from persistent config.json."""
    cfg_file = get_config_path(config_path)
    if cfg_file.is_file():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(data: dict[str, Any], config_path: Path | None = None) -> None:
    """Save configuration dictionary to persistent config.json."""
    cfg_file = get_config_path(config_path)
    current = load_config(cfg_file)
    current.update(data)
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)


def get_default_save_dir(config_path: Path | None = None) -> str:
    """Retrieve default save directory from config, falling back to ~/Downloads or cwd."""
    cfg = load_config(config_path)
    saved = cfg.get("default_output_dir")
    if saved and os.path.isdir(saved):
        return os.path.abspath(saved)
    default_dl = str(Path.home() / "Downloads")
    if os.path.isdir(default_dl):
        return default_dl
    return os.getcwd()


def get_saved_cookie_file(config_path: Path | None = None) -> str | None:
    """Retrieve saved cookies.txt path from config if it exists on disk."""
    cfg = load_config(config_path)
    saved = cfg.get("cookie_file_path")
    if saved and os.path.isfile(saved):
        return os.path.abspath(saved)
    return None


def find_ffmpeg() -> str | None:
    """Dynamically detect ffmpeg.exe in MEIPASS, ./bin/, APPDATA, current directory, or PATH."""
    # 1. PyInstaller bundled directory
    if hasattr(sys, "_MEIPASS"):
        for sub in ("bin/ffmpeg.exe", "ffmpeg.exe"):
            p = Path(sys._MEIPASS) / sub
            if p.is_file():
                return str(p)

    # 2. Local ./bin/ relative to this script / project directory
    module_bin = Path(__file__).resolve().parent / "bin" / "ffmpeg.exe"
    if module_bin.is_file():
        return str(module_bin)

    # 3. User APPDATA bin directory
    appdata = os.environ.get("APPDATA")
    if appdata:
        for app_folder in ("YouTubeDownloaderLS", "YouTubeDownloader"):
            appdata_ffmpeg = Path(appdata) / app_folder / "bin" / "ffmpeg.exe"
            if appdata_ffmpeg.is_file():
                return str(appdata_ffmpeg)

    # 4. Current working directory ./bin/ or root
    for sub in ("bin/ffmpeg.exe", "ffmpeg.exe"):
        p = Path.cwd() / sub
        if p.is_file():
            return str(p)

    # 5. System PATH
    path_ffmpeg = shutil.which("ffmpeg")
    if path_ffmpeg:
        return path_ffmpeg

    return None


def find_ffprobe() -> str | None:
    """Dynamically detect ffprobe.exe in MEIPASS, ./bin/, APPDATA, current directory, or PATH."""
    if hasattr(sys, "_MEIPASS"):
        for sub in ("bin/ffprobe.exe", "ffprobe.exe"):
            p = Path(sys._MEIPASS) / sub
            if p.is_file():
                return str(p)

    module_bin = Path(__file__).resolve().parent / "bin" / "ffprobe.exe"
    if module_bin.is_file():
        return str(module_bin)

    appdata = os.environ.get("APPDATA")
    if appdata:
        for app_folder in ("YouTubeDownloaderLS", "YouTubeDownloader"):
            appdata_ffprobe = Path(appdata) / app_folder / "bin" / "ffprobe.exe"
            if appdata_ffprobe.is_file():
                return str(appdata_ffprobe)

    for sub in ("bin/ffprobe.exe", "ffprobe.exe"):
        p = Path.cwd() / sub
        if p.is_file():
            return str(p)

    path_ffprobe = shutil.which("ffprobe")
    if path_ffprobe:
        return path_ffprobe

    return None


def ensure_ffmpeg(status_callback: Callable[[str], None] | None = None) -> str | None:
    """Ensure ffmpeg is available. If missing, download Windows static build into APPDATA."""
    found = find_ffmpeg()
    if found:
        return found

    if status_callback:
        status_callback("Acquiring FFmpeg (one-time background setup)...")

    appdata = os.environ.get("APPDATA")
    base_bin = Path(appdata) / "YouTubeDownloaderLS" / "bin" if appdata else Path.home() / ".youtubedownloaderls" / "bin"
    base_bin.mkdir(parents=True, exist_ok=True)
    target_ffmpeg = base_bin / "ffmpeg.exe"

    if target_ffmpeg.is_file():
        return str(target_ffmpeg)

    import zipfile
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = base_bin / "ffmpeg.zip"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp, open(zip_path, "wb") as out:
            shutil.copyfileobj(resp, out)

        with zipfile.ZipFile(zip_path, "r") as z:
            for item in z.namelist():
                if item.endswith("bin/ffmpeg.exe"):
                    with z.open(item) as src, open(target_ffmpeg, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    break
        if zip_path.is_file():
            zip_path.unlink()
        return str(target_ffmpeg)
    except Exception as e:
        if status_callback:
            status_callback(f"FFmpeg acquisition notice: {e}")
        return None

    module_bin = Path(__file__).resolve().parent / "bin" / "ffprobe.exe"
    if module_bin.is_file():
        return str(module_bin)

    cwd_bin = Path.cwd() / "bin" / "ffprobe.exe"
    if cwd_bin.is_file():
        return str(cwd_bin)
    cwd_ffprobe = Path.cwd() / "ffprobe.exe"
    if cwd_ffprobe.is_file():
        return str(cwd_ffprobe)

    path_ffprobe = shutil.which("ffprobe")
    if path_ffprobe:
        return path_ffprobe

    return None


def get_ffmpeg_location() -> str | None:
    """Return the directory containing ffmpeg or the executable path for ydl_opts."""
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return None
    # Passing the directory allows yt-dlp to find both ffmpeg and ffprobe
    p = Path(ffmpeg_path)
    if p.is_file():
        return str(p.parent)
    return str(p)


def parse_time_to_seconds(time_str: str | None) -> float | None:
    """Parse a time string formatted as SS, MM:SS, or HH:MM:SS into float seconds."""
    if not time_str:
        return None
    cleaned = time_str.strip()
    if not cleaned:
        return None

    try:
        parts = cleaned.split(":")
        if len(parts) == 1:
            return float(parts[0])
        elif len(parts) == 2:
            minutes, seconds = float(parts[0]), float(parts[1])
            if minutes < 0 or seconds < 0:
                return None
            return minutes * 60.0 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = float(parts[0]), float(parts[1]), float(parts[2])
            if hours < 0 or minutes < 0 or seconds < 0:
                return None
            return hours * 3600.0 + minutes * 60.0 + seconds
    except (ValueError, TypeError):
        return None
    return None


def format_duration(seconds: int | float | None) -> str:
    """Format duration in seconds into HH:MM:SS or MM:SS."""
    if seconds is None:
        return "Unknown"
    sec = int(seconds)
    hours = sec // 3600
    minutes = (sec % 3600) // 60
    remaining_secs = sec % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{remaining_secs:02d}"
    return f"{minutes:02d}:{remaining_secs:02d}"


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from strings."""
    ansi_regex = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
    return ansi_regex.sub("", text)


def format_progress(d: dict[str, Any]) -> tuple[float, str]:
    """Parse yt-dlp progress hook data into (percentage_float, formatted_status_str)."""
    status = d.get("status")
    if status == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        downloaded = d.get("downloaded_bytes", 0)

        if total and total > 0:
            pct_float = max(0.0, min(1.0, downloaded / total))
            pct_str = f"{pct_float * 100:.1f}%"
        else:
            raw_pct = d.get("_percent_str", "")
            raw_clean = strip_ansi(raw_pct).replace("%", "").strip()
            try:
                pct_float = max(0.0, min(1.0, float(raw_clean) / 100.0))
                pct_str = f"{pct_float * 100:.1f}%"
            except ValueError:
                pct_float = 0.0
                pct_str = "0.0%"

        speed_raw = d.get("_speed_str") or ""
        speed_clean = strip_ansi(speed_raw).strip() or "N/A"

        eta_raw = d.get("_eta_str") or ""
        eta_clean = strip_ansi(eta_raw).strip() or "--:--"

        status_text = f"Downloading: {pct_str} | Speed: {speed_clean} | ETA: {eta_clean}"
        return pct_float, status_text

    elif status == "finished":
        return 1.0, "Download completed. Processing..."
    elif status == "error":
        return 0.0, "Download error encountered."

    return 0.0, "Preparing..."


def extract_resolution_height(resolution_str: str) -> str | None:
    """Extract numeric height from resolution string like '1080p' -> '1080'."""
    if not resolution_str or "Best" in resolution_str:
        return None
    match = re.search(r"(\d+)", resolution_str)
    return match.group(1) if match else None


def extract_bitrate(bitrate_str: str) -> str:
    """Extract numeric bitrate like '320 kbps (Best)' -> '320'."""
    match = re.search(r"(\d+)", bitrate_str)
    return match.group(1) if match else "192"


def build_ydl_opts(
    output_dir: str,
    mode: str = "Video (MP4)",
    resolution: str = "Best Available (4K/8K)",
    audio_bitrate: str = "320 kbps (Best)",
    audio_format: str = "M4A (Raw Audio)",
    embed_thumbnail: bool = True,
    embed_metadata: bool = True,
    download_subtitles: bool = False,
    download_playlist: bool = False,
    start_time: str | None = None,
    end_time: str | None = None,
    progress_hook: Callable[[dict[str, Any]], None] | None = None,
    postprocessor_hook: Callable[[dict[str, Any]], None] | None = None,
    ffmpeg_location: str | None = None,
    cookies_browser: str | None = None,
    cookies_file: str | None = None,
) -> dict[str, Any]:
    """Build yt-dlp options dictionary according to project rules."""
    has_cookies = bool(
        (cookies_file and os.path.isfile(cookies_file))
        or (cookies_browser and cookies_browser.lower() not in ("none", ""))
    )

    opts: dict[str, Any] = {
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "windowsfilenames": True,
        "noplaylist": not download_playlist,
        "quiet": True,
        "no_warnings": False,
        "remote_components": ["ejs:github"],
    }

    # Only force mobile/alternate client fallback when unauthenticated (avoids 429 bot checks).
    # When cookies are passed, yt-dlp uses its default authenticated client chain (iOS/Android do not support cookies).
    if not has_cookies:
        opts["extractor_args"] = {
            "youtube": {
                "player_client": ["ios", "android", "mweb", "web"]
            }
        }

    # Cookies configuration for age-gated or private videos
    if cookies_file and os.path.isfile(cookies_file):
        opts["cookiefile"] = cookies_file
    elif cookies_browser and cookies_browser.lower() not in ("none", ""):
        opts["cookiesfrombrowser"] = (cookies_browser.lower(),)

    # FFmpeg path resolution
    resolved_ffmpeg = ffmpeg_location or get_ffmpeg_location()
    if resolved_ffmpeg:
        opts["ffmpeg_location"] = resolved_ffmpeg

    # JavaScript runtime resolution (Node, Deno, Bun)
    js_runtimes: dict[str, Any] = {}
    if shutil.which("node"):
        js_runtimes["node"] = {}
    if shutil.which("deno"):
        js_runtimes["deno"] = {}
    if shutil.which("bun"):
        js_runtimes["bun"] = {}
    if js_runtimes:
        opts["js_runtimes"] = js_runtimes

    # Postprocessors list
    postprocessors: list[dict[str, Any]] = []

    # Format logic based on mode
    norm_mode = mode.lower()
    height = extract_resolution_height(resolution)

    if "video (mp4)" in norm_mode:
        if height:
            opts["format"] = (
                f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]/"
                f"b[height<={height}][ext=mp4]/"
                f"bv*[height<={height}]+ba/"
                f"b[height<={height}]"
            )
        else:
            opts["format"] = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
        opts["merge_output_format"] = "mp4"

    elif "audio only (mp3)" in norm_mode:
        opts["format"] = "bestaudio/best"
        bitrate_val = extract_bitrate(audio_bitrate)
        postprocessors.append({
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": bitrate_val,
        })

    elif "audio only" in norm_mode:  # M4A / WAV / FLAC
        audio_choice = audio_format.lower()
        if "m4a" in audio_choice:
            # Raw M4A without re-encoding
            opts["format"] = "bestaudio[ext=m4a]/bestaudio"
        else:
            opts["format"] = "bestaudio/best"
            codec = "flac" if "flac" in audio_choice else "wav"
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": codec,
            })

    elif "video only" in norm_mode:  # Muted MP4
        if height:
            opts["format"] = f"bv*[height<={height}][ext=mp4]/bv*[height<={height}]"
        else:
            opts["format"] = "bv*[ext=mp4]/bv*"
        opts["merge_output_format"] = "mp4"

    else:
        # Default fallback
        opts["format"] = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
        opts["merge_output_format"] = "mp4"

    # Subtitles
    if download_subtitles:
        opts["writesubtitles"] = True
        opts["writeautomaticsub"] = True
        opts["subtitleslangs"] = ["en", "en-US", "en-GB"]
        # If in a video mode, embed subtitles into container
        if "video" in norm_mode:
            postprocessors.append({"key": "FFmpegEmbedSubtitle"})

    # Embed Thumbnail
    if embed_thumbnail:
        opts["writethumbnail"] = True
        postprocessors.append({"key": "EmbedThumbnail"})

    # Embed Metadata
    if embed_metadata:
        postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})

    if postprocessors:
        opts["postprocessors"] = postprocessors

    # Clip / Trim range
    s_sec = parse_time_to_seconds(start_time)
    e_sec = parse_time_to_seconds(end_time)
    if s_sec is not None or e_sec is not None:
        start_val = s_sec if s_sec is not None else 0.0
        end_val = e_sec if e_sec is not None else float("inf")
        opts["download_ranges"] = download_range_func(None, [(start_val, end_val)])
        opts["force_keyframes_at_cuts"] = True

    # Hooks
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    if postprocessor_hook:
        opts["postprocessor_hooks"] = [postprocessor_hook]

    return opts


def fetch_video_info(
    url: str,
    cookies_browser: str | None = None,
    cookies_file: str | None = None,
) -> dict[str, Any]:
    """Fetch video metadata asynchronously or synchronously without downloading."""
    ffmpeg_loc = get_ffmpeg_location()
    has_cookies = bool(
        (cookies_file and os.path.isfile(cookies_file))
        or (cookies_browser and cookies_browser.lower() not in ("none", ""))
    )

    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
        "extract_flat": False,
        "remote_components": ["ejs:github"],
    }
    if not has_cookies:
        ydl_opts["extractor_args"] = {
            "youtube": {
                "player_client": ["ios", "android", "mweb", "web"]
            }
        }

    if cookies_file and os.path.isfile(cookies_file):
        ydl_opts["cookiefile"] = cookies_file
    elif cookies_browser and cookies_browser.lower() not in ("none", ""):
        ydl_opts["cookiesfrombrowser"] = (cookies_browser.lower(),)

    if ffmpeg_loc:
        ydl_opts["ffmpeg_location"] = ffmpeg_loc

    js_runtimes: dict[str, Any] = {}
    if shutil.which("node"):
        js_runtimes["node"] = {}
    if shutil.which("deno"):
        js_runtimes["deno"] = {}
    if shutil.which("bun"):
        js_runtimes["bun"] = {}
    if js_runtimes:
        ydl_opts["js_runtimes"] = js_runtimes

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError("No video metadata could be retrieved.")

        # In case a playlist URL was passed with extract_flat=False
        if "entries" in info and info["entries"]:
            info = info["entries"][0]

        duration = info.get("duration")
        view_count = info.get("view_count")

        return {
            "title": info.get("title") or "Unknown Title",
            "channel": info.get("uploader") or info.get("channel") or "Unknown Channel",
            "duration": duration,
            "duration_formatted": format_duration(duration),
            "thumbnail_url": info.get("thumbnail"),
            "view_count": view_count,
            "views_formatted": f"{view_count:,} views" if view_count is not None else "",
            "webpage_url": info.get("webpage_url") or url,
        }


def fetch_thumbnail_image(thumbnail_url: str | None) -> Image.Image | None:
    """Download thumbnail image into memory and return a PIL Image."""
    if not thumbnail_url:
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(thumbnail_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read()
            return Image.open(io.BytesIO(data))
    except Exception:
        return None


def download_video(url: str, ydl_opts: dict[str, Any]) -> None:
    """Execute download for the given URL using the configured options."""
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


# -----------------------------------------------------------------------------
# Application Version & GitHub Update Helpers
# -----------------------------------------------------------------------------
APP_VERSION = "1.0.3"
GITHUB_REPO = "lsutorus/ytd-ls"


def parse_version_tuple(v: str) -> tuple[int, ...]:
    """Convert a version string into a tuple of integers for comparison."""
    nums = re.findall(r"\d+", v)
    return tuple(int(n) for n in nums) if nums else (0,)


def check_for_app_update(
    current_version: str = APP_VERSION,
    repo: str = GITHUB_REPO,
) -> dict[str, Any] | None:
    """Query GitHub Releases API to detect if a newer release is published."""
    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "YouTubeDownloaderLS"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            tag = data.get("tag_name", "").lstrip("v")
            if parse_version_tuple(tag) > parse_version_tuple(current_version):
                msi_url = None
                for asset in data.get("assets", []):
                    if asset.get("name", "").endswith(".msi"):
                        msi_url = asset.get("browser_download_url")
                        break
                return {
                    "version": tag,
                    "tag": data.get("tag_name"),
                    "html_url": data.get("html_url"),
                    "msi_url": msi_url or data.get("html_url"),
                    "notes": data.get("body", ""),
                }
    except Exception:
        pass
    return None


def download_update_msi(msi_url: str, progress_callback: Callable[[float], None] | None = None) -> str | None:
    """Download the MSI installer to a temp file and return its absolute path."""
    try:
        temp_dir = Path(tempfile.gettempdir())
        msi_dest = temp_dir / "YouTubeDownloaderLS-Update.msi"
        req = urllib.request.Request(msi_url, headers={"User-Agent": "YouTubeDownloaderLS"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(msi_dest, "wb") as f:
            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0
            while chunk := resp.read(65536):
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total_size > 0:
                    progress_callback(min(1.0, downloaded / total_size))
        return str(msi_dest.resolve())
    except Exception:
        return None
