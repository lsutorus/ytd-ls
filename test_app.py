"""Unit and integration tests for YouTube Downloader & Converter.

Tests:
1. FFmpeg & FFprobe path resolution.
2. Time duration parsing and formatting.
3. ydl_opts generation for all formats, resolutions, bitrates, and customization flags.
4. Live metadata extraction ("Me at the zoo").
5. Live MP3 download into tmp_path.
6. Live 360p MP4 download into tmp_path.
7. GUI headless/self-test initialization.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import downloader
from app import YouTubeDownloaderApp

ME_AT_THE_ZOO_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"


# -----------------------------------------------------------------------------
# 1. FFmpeg & FFprobe Resolution Tests
# -----------------------------------------------------------------------------
def test_ffmpeg_and_ffprobe_resolution() -> None:
    ffmpeg = downloader.find_ffmpeg()
    ffprobe = downloader.find_ffprobe()
    location = downloader.get_ffmpeg_location()

    assert ffmpeg is not None, "ffmpeg.exe could not be located"
    assert os.path.isfile(ffmpeg), f"ffmpeg path is not a file: {ffmpeg}"

    assert ffprobe is not None, "ffprobe.exe could not be located"
    assert os.path.isfile(ffprobe), f"ffprobe path is not a file: {ffprobe}"

    assert location is not None, "ffmpeg location could not be determined"
    assert os.path.exists(location), f"ffmpeg location path does not exist: {location}"


# -----------------------------------------------------------------------------
# 2. Time Duration & Formatting Tests
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "input_str,expected",
    [
        ("15", 15.0),
        ("00:45", 45.0),
        ("01:23", 83.0),
        ("01:02:03", 3723.0),
        ("0:00", 0.0),
        ("", None),
        ("   ", None),
        (None, None),
        ("invalid", None),
        ("-01:23", None),
    ],
)
def test_parse_time_to_seconds(input_str: str | None, expected: float | None) -> None:
    assert downloader.parse_time_to_seconds(input_str) == expected


def test_format_duration() -> None:
    assert downloader.format_duration(19) == "00:19"
    assert downloader.format_duration(83) == "01:23"
    assert downloader.format_duration(3665) == "1:01:05"
    assert downloader.format_duration(None) == "Unknown"


# -----------------------------------------------------------------------------
# 3. ydl_opts Configuration Matrix Tests
# -----------------------------------------------------------------------------
def test_ydl_opts_video_mp4_best() -> None:
    opts = downloader.build_ydl_opts(
        output_dir="test_out",
        mode="Video (MP4)",
        resolution="Best Available (4K/8K)",
    )
    assert opts["format"] == "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
    assert opts["merge_output_format"] == "mp4"
    assert opts["windowsfilenames"] is True
    assert opts["outtmpl"] == os.path.join("test_out", "%(title)s.%(ext)s")


@pytest.mark.parametrize("res,height", [("1080p", "1080"), ("720p", "720"), ("480p", "480"), ("360p", "360")])
def test_ydl_opts_video_mp4_resolutions(res: str, height: str) -> None:
    opts = downloader.build_ydl_opts(
        output_dir="test_out",
        mode="Video (MP4)",
        resolution=res,
    )
    expected_fmt = (
        f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]/"
        f"b[height<={height}][ext=mp4]/"
        f"bv*[height<={height}]+ba/"
        f"b[height<={height}]"
    )
    assert opts["format"] == expected_fmt
    assert opts["merge_output_format"] == "mp4"


@pytest.mark.parametrize("bitrate_choice,expected_quality", [
    ("320 kbps (Best)", "320"),
    ("192 kbps (Standard)", "192"),
    ("128 kbps (Small)", "128"),
])
def test_ydl_opts_audio_mp3(bitrate_choice: str, expected_quality: str) -> None:
    opts = downloader.build_ydl_opts(
        output_dir="test_out",
        mode="Audio Only (MP3)",
        audio_bitrate=bitrate_choice,
    )
    assert opts["format"] == "bestaudio/best"
    extract_pps = [p for p in opts.get("postprocessors", []) if p.get("key") == "FFmpegExtractAudio"]
    assert len(extract_pps) == 1
    assert extract_pps[0]["preferredcodec"] == "mp3"
    assert extract_pps[0]["preferredquality"] == expected_quality


def test_ydl_opts_audio_m4a_raw() -> None:
    opts = downloader.build_ydl_opts(
        output_dir="test_out",
        mode="Audio Only (M4A / WAV / FLAC)",
        audio_format="M4A (Raw Audio)",
    )
    assert opts["format"] == "bestaudio[ext=m4a]/bestaudio"
    extract_pps = [p for p in opts.get("postprocessors", []) if p.get("key") == "FFmpegExtractAudio"]
    assert len(extract_pps) == 0


@pytest.mark.parametrize("fmt,codec", [
    ("WAV (Lossless)", "wav"),
    ("FLAC (Lossless)", "flac"),
])
def test_ydl_opts_audio_lossless(fmt: str, codec: str) -> None:
    opts = downloader.build_ydl_opts(
        output_dir="test_out",
        mode="Audio Only (M4A / WAV / FLAC)",
        audio_format=fmt,
    )
    assert opts["format"] == "bestaudio/best"
    extract_pps = [p for p in opts.get("postprocessors", []) if p.get("key") == "FFmpegExtractAudio"]
    assert len(extract_pps) == 1
    assert extract_pps[0]["preferredcodec"] == codec


def test_ydl_opts_video_only_muted() -> None:
    opts_best = downloader.build_ydl_opts(
        output_dir="test_out",
        mode="Video Only (Muted MP4)",
        resolution="Best Available (4K/8K)",
    )
    assert opts_best["format"] == "bv*[ext=mp4]/bv*"
    assert opts_best["merge_output_format"] == "mp4"

    opts_720 = downloader.build_ydl_opts(
        output_dir="test_out",
        mode="Video Only (Muted MP4)",
        resolution="720p",
    )
    assert opts_720["format"] == "bv*[height<=720][ext=mp4]/bv*[height<=720]"
    assert opts_720["merge_output_format"] == "mp4"


def test_ydl_opts_customization_checkboxes() -> None:
    # All enabled
    opts_all = downloader.build_ydl_opts(
        output_dir="test_out",
        mode="Video (MP4)",
        embed_thumbnail=True,
        embed_metadata=True,
        download_subtitles=True,
        download_playlist=True,
    )
    pps = opts_all.get("postprocessors", [])
    pp_keys = [p.get("key") for p in pps]

    assert opts_all["writethumbnail"] is True
    assert "EmbedThumbnail" in pp_keys

    assert "FFmpegMetadata" in pp_keys
    meta_pp = next(p for p in pps if p.get("key") == "FFmpegMetadata")
    assert meta_pp.get("add_metadata") is True

    assert opts_all["writesubtitles"] is True
    assert opts_all["subtitleslangs"] == ["en", "en-US", "en-GB"]
    assert "FFmpegEmbedSubtitle" in pp_keys

    assert opts_all["noplaylist"] is False

    # All disabled
    opts_none = downloader.build_ydl_opts(
        output_dir="test_out",
        mode="Video (MP4)",
        embed_thumbnail=False,
        embed_metadata=False,
        download_subtitles=False,
        download_playlist=False,
    )
    assert "writethumbnail" not in opts_none
    assert "writesubtitles" not in opts_none
    assert opts_none.get("postprocessors") is None or len(opts_none.get("postprocessors", [])) == 0
    assert opts_none["noplaylist"] is True


def test_ydl_opts_time_trimming() -> None:
    opts = downloader.build_ydl_opts(
        output_dir="test_out",
        start_time="00:05",
        end_time="00:15",
    )
    assert "download_ranges" in opts
    assert opts.get("force_keyframes_at_cuts") is True

    # Test the range function call
    dummy_info = {"duration": 30}
    ranges = list(opts["download_ranges"](dummy_info, None))
    assert ranges == [{"start_time": 5.0, "end_time": 15.0}]


# -----------------------------------------------------------------------------
# 4. Live End-to-End Tests ("Me at the zoo")
# -----------------------------------------------------------------------------
def test_live_metadata_extraction() -> None:
    info = downloader.fetch_video_info(ME_AT_THE_ZOO_URL)
    assert "Me at the zoo" in info["title"]
    assert info["duration"] == 19
    assert info["channel"] == "jawed"
    assert info["duration_formatted"] == "00:19"
    assert info["thumbnail_url"] is not None


def test_live_download_mp3(tmp_path: Path) -> None:
    opts = downloader.build_ydl_opts(
        output_dir=str(tmp_path),
        mode="Audio Only (MP3)",
        audio_bitrate="192 kbps (Standard)",
        embed_thumbnail=False,
        embed_metadata=False,
    )
    downloader.download_video(ME_AT_THE_ZOO_URL, opts)

    mp3_files = list(tmp_path.glob("*.mp3"))
    assert len(mp3_files) >= 1, f"Expected .mp3 file in {tmp_path}, found: {list(tmp_path.iterdir())}"
    assert mp3_files[0].stat().st_size > 0, "Downloaded .mp3 file is empty"


def test_live_download_360p_mp4(tmp_path: Path) -> None:
    opts = downloader.build_ydl_opts(
        output_dir=str(tmp_path),
        mode="Video (MP4)",
        resolution="360p",
        embed_thumbnail=False,
        embed_metadata=False,
    )
    downloader.download_video(ME_AT_THE_ZOO_URL, opts)

    mp4_files = list(tmp_path.glob("*.mp4"))
    assert len(mp4_files) >= 1, f"Expected .mp4 file in {tmp_path}, found: {list(tmp_path.iterdir())}"
    assert mp4_files[0].stat().st_size > 0, "Downloaded .mp4 file is empty"


# -----------------------------------------------------------------------------
# 5. Config Persistence Tests
# -----------------------------------------------------------------------------
def test_config_persistence(tmp_path: Path) -> None:
    test_cfg = tmp_path / "config.json"
    assert downloader.load_config(test_cfg) == {}

    downloader.save_config({"default_output_dir": str(tmp_path)}, test_cfg)
    loaded = downloader.load_config(test_cfg)
    assert loaded.get("default_output_dir") == str(tmp_path)

    default_dir = downloader.get_default_save_dir(test_cfg)
    assert default_dir == str(tmp_path)

    cookie_dummy = tmp_path / "test_cookies.txt"
    cookie_dummy.write_text("# Netscape HTTP Cookie File", encoding="utf-8")
    downloader.save_config({"cookie_file_path": str(cookie_dummy)}, test_cfg)
    assert downloader.get_saved_cookie_file(test_cfg) == str(cookie_dummy)

    downloader.save_config({"cookie_file_path": str(tmp_path / "non_existent.txt")}, test_cfg)
    assert downloader.get_saved_cookie_file(test_cfg) is None


# -----------------------------------------------------------------------------
# 6. GUI Instantiation Smoke Test
# -----------------------------------------------------------------------------
def test_gui_instantiation() -> None:
    app = YouTubeDownloaderApp(self_test=True)
    # Verify core attributes & widgets exist
    assert hasattr(app, "url_entry")
    assert hasattr(app, "mode_selector")
    assert hasattr(app, "dynamic_menu")
    assert hasattr(app, "cust_tabview")
    assert hasattr(app, "progress_bar")
    assert hasattr(app, "btn_download")
    assert hasattr(app, "btn_open_folder")
    assert hasattr(app, "btn_set_default")
    assert hasattr(app, "btn_cookie_guide")
    assert hasattr(app, "btn_clear_cookie")
    assert hasattr(app, "btn_app_update")
    assert hasattr(app, "app_version_label")

    # Verify default mode is Audio Only (MP3)
    assert app.mode_selector.get() == "Audio Only (MP3)"
    assert app.dynamic_label.cget("text") == "Audio Bitrate:"

    # Verify default tab & checkbox states
    assert app.cust_tabview.get() == "General"
    assert app.var_embed_thumb.get() is True
    assert app.var_embed_meta.get() is True
    assert app.var_subtitles.get() is False
    assert app.var_playlist.get() is False

    # Destroy window immediately
    app.destroy()


# -----------------------------------------------------------------------------
# 7. App Updater Unit Tests
# -----------------------------------------------------------------------------
def test_parse_version_tuple() -> None:
    assert downloader.parse_version_tuple("1.0.3") == (1, 0, 3)
    assert downloader.parse_version_tuple("v1.0.3") == (1, 0, 3)
    assert downloader.parse_version_tuple("v2.1.0-beta") == (2, 1, 0)
    assert downloader.parse_version_tuple("v1.0.4") > downloader.parse_version_tuple("v1.0.3")
    assert downloader.parse_version_tuple("v1.1.0") > downloader.parse_version_tuple("v1.0.9")

# -----------------------------------------------------------------------------
# 8. yt-dlp Updater Unit Tests
# -----------------------------------------------------------------------------
def test_get_ytdlp_updates_dir(tmp_path: Path) -> None:
    updates = downloader.get_ytdlp_updates_dir(tmp_path)
    assert updates == tmp_path / "updates"


def test_init_ytdlp_updates_path(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "yt_dlp"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("# dummy", encoding="utf-8")

    downloader.init_ytdlp_updates_path(tmp_path)
    import sys
    assert str(tmp_path.resolve()) in sys.path
    if str(tmp_path.resolve()) in sys.path:
        sys.path.remove(str(tmp_path.resolve()))


def test_get_current_ytdlp_version() -> None:
    import re
    ver = downloader.get_current_ytdlp_version()
    assert ver != "unknown"
    assert len(re.findall(r"\d+", ver)) >= 2


def test_check_for_ytdlp_update_mocked_available(monkeypatch: pytest.MonkeyPatch) -> None:
    import json
    import urllib.request
    from typing import Any

    mock_response = json.dumps({
        "info": {"version": "2099.01.01"},
        "urls": [{"filename": "yt_dlp-2099.1.1-py3-none-any.whl", "url": "https://example.com/yt_dlp.whl"}],
    }).encode("utf-8")

    class MockResp:
        def read(self) -> bytes:
            return mock_response
        def __enter__(self) -> "MockResp":
            return self
        def __exit__(self, *args: Any) -> None:
            pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=10: MockResp())

    info = downloader.check_for_ytdlp_update(current_version="2026.08.19")
    assert info is not None
    assert info["update_available"] is True
    assert info["latest_version"] == "2099.01.01"
    assert info["wheel_url"] == "https://example.com/yt_dlp.whl"


def test_check_for_ytdlp_update_mocked_already_up_to_date(monkeypatch: pytest.MonkeyPatch) -> None:
    import json
    import urllib.request
    from typing import Any

    mock_response = json.dumps({
        "info": {"version": "2026.08.19"},
        "urls": [{"filename": "yt_dlp-2026.8.19-py3-none-any.whl", "url": "https://example.com/yt_dlp.whl"}],
    }).encode("utf-8")

    class MockResp:
        def read(self) -> bytes:
            return mock_response
        def __enter__(self) -> "MockResp":
            return self
        def __exit__(self, *args: Any) -> None:
            pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=10: MockResp())

    info = downloader.check_for_ytdlp_update(current_version="2026.08.19")
    assert info is not None
    assert info["update_available"] is False


def test_check_for_ytdlp_update_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request
    import urllib.error
    from typing import Any

    def _mock_err(*args: Any, **kwargs: Any) -> Any:
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", _mock_err)
    info = downloader.check_for_ytdlp_update()
    assert info is None


def test_install_ytdlp_wheel_mocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import zipfile
    import urllib.request

    mock_whl = tmp_path / "test_yt_dlp.whl"
    with zipfile.ZipFile(mock_whl, "w") as zf:
        zf.writestr("yt_dlp/__init__.py", "__version__ = '2099.9.9'\n")
        zf.writestr("yt_dlp/version.py", "__version__ = '2099.09.09'\n")
        zf.writestr("yt_dlp/utils.py", "def download_range_func(): pass\n")

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=30: open(mock_whl, "rb"))

    updates_dir = tmp_path / "updates"
    success, new_ver = downloader.install_ytdlp_wheel("https://dummy.url/pkg.whl", updates_dir=updates_dir)
    assert success is True
    assert new_ver == "2099.09.09"
    assert (updates_dir / "yt_dlp" / "__init__.py").is_file()

    # Clean up sys.path and sys.modules
    if str(updates_dir.resolve()) in sys.path:
        sys.path.remove(str(updates_dir.resolve()))
    for mod in list(sys.modules.keys()):
        if mod == "yt_dlp" or mod.startswith("yt_dlp."):
            sys.modules.pop(mod, None)
    downloader.reload_ytdlp_module()


def test_app_ytdlp_update_ui_state() -> None:
    app = YouTubeDownloaderApp(self_test=True)

    # 1. Test already up to date UI transition
    app._on_ytdlp_already_up_to_date("2026.08.19", "https://dummy.whl")
    assert "already up to date" in app.status_label.cget("text")
    assert app.btn_update.cget("state") == "normal"
    assert app.btn_update.cget("text") == "Update yt-dlp"

    # 2. Test successful install UI transition
    app._on_ytdlp_install_success("2026.09.01")
    assert "updated successfully" in app.status_label.cget("text")
    assert "2026.09.01" in app.version_label.cget("text")
    assert app.btn_update.cget("state") == "normal"

    # 3. Test check failed UI transition
    app._on_ytdlp_check_failed("PyPI unreachable")
    assert "check failed" in app.status_label.cget("text")
    assert app.btn_update.cget("state") == "normal"

    # 4. Test install failed UI transition
    app._on_ytdlp_install_failed("Disk full")
    assert "failed" in app.status_label.cget("text")
    assert app.btn_update.cget("state") == "normal"

    app.destroy()

