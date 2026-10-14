# YouTube Downloader & Converter

Vibe-coded using Gemini 3.8 Flash High.

A lightweight, self-updating desktop YouTube downloader and converter built for Windows using Python, `customtkinter`, and `yt-dlp`.

## Features

- **Effortless UX:** Paste any YouTube link (or click **📋 Paste**) to instantly fetch video details and thumbnail preview.
- **Dynamic Format Matrix:**
  - `Video (MP4)`: Select maximum resolution (`Best Available (4K/8K)`, `1080p`, `720p`, `480p`, `360p`).
  - `Audio Only (MP3)`: Select audio bitrate (`320 kbps (Best)`, `192 kbps (Standard)`, `128 kbps (Small)`).
  - `Audio Only (M4A / WAV / FLAC)`: Choose raw M4A or lossless WAV / FLAC conversions.
  - `Video Only (Muted MP4)`: Download video streams without audio tracks.
- **Customization Options:**
  - Save folder selector with Windows file dialog.
  - Clip / trim time ranges (`MM:SS` or `HH:MM:SS`) using `download_range_func`.
  - Embed thumbnails & metadata tags directly into output files.
  - Optional subtitle extraction & embedding.
  - Toggle full playlist downloading.
- **Real-Time Progress & Status:**
  - Float progress bar with live download percentage, transfer speed, and ETA.
  - Postprocessor status tracking during FFmpeg conversions.
  - One-click button to open download directory in Windows Explorer.
  - In-app `yt-dlp` update button with version display.
- **Robust Architecture:**
  - Headless backend (`downloader.py`) cleanly separated from the GUI (`app.py`).
  - 100% thread-safe: all network and FFmpeg tasks run on background daemon threads, marshaling updates to the UI thread via `after(0, ...)`.
  - Auto-resolving FFmpeg/FFprobe binaries from `./bin/`, `PATH`, or `sys._MEIPASS`.

## Installation & Downloads

Download the latest version from the [v1.0.0 Releases Page](https://github.com/lsutorus/yt-mp3-ls/releases/tag/v1.0.0):

- [**`YouTubeDownloader-v1.0.0-Setup.exe`**](https://github.com/lsutorus/yt-mp3-ls/releases/download/v1.0.0/YouTubeDownloader-v1.0.0-Setup.exe): Recommended Windows installer. Installs to Program Files, creates Start Menu & Desktop shortcuts, and includes an uninstaller.
- [**`YouTubeDownloader.exe`**](https://github.com/lsutorus/yt-mp3-ls/releases/download/v1.0.0/YouTubeDownloader.exe): Portable standalone executable.
- [**`YouTubeDownloader-v1.0.0-windows-x64.zip`**](https://github.com/lsutorus/yt-mp3-ls/releases/download/v1.0.0/YouTubeDownloader-v1.0.0-windows-x64.zip): Zip archive containing the standalone executable.

---

## Launching from Source

To launch the GUI for human testing:

```pwsh
uv run main.py
```

To run the automated UI smoke test (non-blocking, exits with code 0):

```pwsh
uv run main.py --self-test
```

---

## Automated Test Suite

Run the full pytest suite (including unit tests, configuration matrix tests, and live YouTube download integration tests):

```pwsh
uv run pytest -v
```
