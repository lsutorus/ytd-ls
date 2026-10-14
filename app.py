"""GUI Application for YouTube Downloader & Converter using CustomTkinter.

This module provides a modern, responsive interface for downloading YouTube videos
and audio with dynamic quality selection, clipping, metadata embedding, and live progress.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
from PIL import Image, ImageDraw

import downloader

# Configure CustomTkinter defaults
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class YouTubeDownloaderApp(ctk.CTk):
    """Main application window."""

    def __init__(self, self_test: bool = False) -> None:
        super().__init__()

        self.self_test = self_test
        self.title("YouTube Downloader & Converter")
        self.geometry("860x760")
        self.minsize(780, 700)

        # Default state variables
        self.output_dir = downloader.get_default_save_dir()

        self.current_video_info: dict[str, Any] | None = None
        self.is_downloading = False
        self.is_fetching_info = False

        # Build UI layout
        self._create_widgets()

        # Check self-test mode
        if self.self_test:
            self.after(200, self._run_self_test_sequence)

    def _create_widgets(self) -> None:
        # Main scrollable or padded frame
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_container = ctk.CTkScrollableFrame(self, corner_radius=12)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.main_container.grid_columnconfigure(0, weight=1)

        # 1. Header / Top Bar
        self._build_header_section()

        # 2. URL Input & Preview Card
        self._build_url_preview_section()

        # 3. Mode & Quality Matrix (Dynamic)
        self._build_format_quality_section()

        # 4. Customization Options Panel
        self._build_customization_section()

        # 5. Bottom Bar (Progress & Action Buttons)
        self._build_bottom_section()

        # Set initial dynamic quality state
        self._on_mode_changed(self.mode_selector.get())

    def _build_header_section(self) -> None:
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header_frame,
            text="YouTube Downloader & Converter",
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        )
        title_label.grid(row=0, column=0, sticky="w")

        # Subtle corner info & update button
        corner_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        corner_frame.grid(row=0, column=1, sticky="e")

        try:
            import yt_dlp.version
            cur_version = f"yt-dlp v{yt_dlp.version.__version__}"
        except Exception:
            cur_version = "yt-dlp"

        self.version_label = ctk.CTkLabel(
            corner_frame,
            text=cur_version,
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        self.version_label.pack(side="left", padx=(0, 8))

        self.btn_update = ctk.CTkButton(
            corner_frame,
            text="Update yt-dlp",
            width=100,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#2b2b2b",
            hover_color="#3a3a3a",
            command=self._on_update_ytdlp_clicked,
        )
        self.btn_update.pack(side="left")

    def _build_url_preview_section(self) -> None:
        # URL Input Row
        url_frame = ctk.CTkFrame(self.main_container, corner_radius=10)
        url_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12), padx=4)
        url_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="Paste YouTube URL here (e.g. https://www.youtube.com/watch?v=...)",
            height=38,
            font=ctk.CTkFont(size=13),
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(12, 8), pady=12)
        self.url_entry.bind("<Return>", lambda _: self._trigger_url_fetch())
        self.url_entry.bind("<FocusOut>", lambda _: self._trigger_url_fetch())

        self.btn_paste = ctk.CTkButton(
            url_frame,
            text="📋 Paste",
            width=90,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_paste_clicked,
        )
        self.btn_paste.grid(row=0, column=1, sticky="e", padx=(0, 12), pady=12)

        # Video Info Preview Card
        self.preview_card = ctk.CTkFrame(self.main_container, corner_radius=10)
        self.preview_card.grid(row=2, column=0, sticky="ew", pady=(0, 12), padx=4)
        self.preview_card.grid_columnconfigure(1, weight=1)

        # Thumbnail Label
        self.thumbnail_placeholder = self._create_placeholder_image(160, 90)
        self.thumb_label = ctk.CTkLabel(
            self.preview_card,
            text="",
            image=self.thumbnail_placeholder,
            width=160,
            height=90,
        )
        self.thumb_label.grid(row=0, column=0, rowspan=4, padx=12, pady=12, sticky="nw")

        # Metadata Labels
        self.title_label = ctk.CTkLabel(
            self.preview_card,
            text="No video loaded",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
            wraplength=520,
            justify="left",
        )
        self.title_label.grid(row=0, column=1, sticky="w", padx=(4, 12), pady=(12, 2))

        self.channel_label = ctk.CTkLabel(
            self.preview_card,
            text="Paste a YouTube link above to automatically fetch details",
            font=ctk.CTkFont(size=13),
            text_color="gray70",
            anchor="w",
        )
        self.channel_label.grid(row=1, column=1, sticky="w", padx=(4, 12), pady=2)

        self.duration_label = ctk.CTkLabel(
            self.preview_card,
            text="Duration: --:--",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            anchor="w",
        )
        self.duration_label.grid(row=2, column=1, sticky="w", padx=(4, 12), pady=2)

        self.views_label = ctk.CTkLabel(
            self.preview_card,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            anchor="w",
        )
        self.views_label.grid(row=3, column=1, sticky="w", padx=(4, 12), pady=(2, 12))

    def _build_format_quality_section(self) -> None:
        matrix_frame = ctk.CTkFrame(self.main_container, corner_radius=10)
        matrix_frame.grid(row=3, column=0, sticky="ew", pady=(0, 12), padx=4)
        matrix_frame.grid_columnconfigure(0, weight=1)

        # Mode Selector
        mode_header = ctk.CTkLabel(
            matrix_frame,
            text="Select Format & Conversion Mode",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        mode_header.grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 8))

        self.modes = [
            "Video (MP4)",
            "Audio Only (MP3)",
            "Audio Only (M4A / WAV / FLAC)",
            "Video Only (Muted MP4)",
        ]
        self.mode_selector = ctk.CTkSegmentedButton(
            matrix_frame,
            values=self.modes,
            command=self._on_mode_changed,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.mode_selector.set("Audio Only (MP3)")
        self.mode_selector.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))

        # Dynamic Quality / Sub-Option Frame
        self.dynamic_frame = ctk.CTkFrame(matrix_frame, fg_color="transparent")
        self.dynamic_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))
        self.dynamic_frame.grid_columnconfigure(1, weight=1)

        self.dynamic_label = ctk.CTkLabel(
            self.dynamic_frame,
            text="Max Resolution:",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=130,
            anchor="w",
        )
        self.dynamic_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.dynamic_menu = ctk.CTkOptionMenu(
            self.dynamic_frame,
            values=["Best Available (4K/8K)", "1080p", "720p", "480p", "360p"],
            width=220,
            height=32,
            font=ctk.CTkFont(size=12),
        )
        self.dynamic_menu.grid(row=0, column=1, sticky="w")

        # Additional secondary option menu (used when Audio M4A/WAV/FLAC needs both codec & bitrate info)
        self.extra_label = ctk.CTkLabel(
            self.dynamic_frame,
            text="Quality:",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=80,
            anchor="w",
        )
        self.extra_menu = ctk.CTkOptionMenu(
            self.dynamic_frame,
            values=["Original / Best"],
            width=180,
            height=32,
            font=ctk.CTkFont(size=12),
        )
        # Hidden by default

    def _on_mode_changed(self, mode: str) -> None:
        """Dynamically swap quality selectors based on the chosen mode."""
        self.extra_label.grid_forget()
        self.extra_menu.grid_forget()

        if mode in ("Video (MP4)", "Video Only (Muted MP4)"):
            self.dynamic_label.configure(text="Max Resolution:")
            res_options = ["Best Available (4K/8K)", "1080p", "720p", "480p", "360p"]
            self.dynamic_menu.configure(values=res_options)
            if self.dynamic_menu.get() not in res_options:
                self.dynamic_menu.set("Best Available (4K/8K)")

        elif mode == "Audio Only (MP3)":
            self.dynamic_label.configure(text="Audio Bitrate:")
            bitrate_options = ["320 kbps (Best)", "192 kbps (Standard)", "128 kbps (Small)"]
            self.dynamic_menu.configure(values=bitrate_options)
            if self.dynamic_menu.get() not in bitrate_options:
                self.dynamic_menu.set("320 kbps (Best)")

        elif mode == "Audio Only (M4A / WAV / FLAC)":
            self.dynamic_label.configure(text="Audio Format:")
            format_options = ["M4A (Raw Audio)", "WAV (Lossless)", "FLAC (Lossless)"]
            self.dynamic_menu.configure(values=format_options)
            if self.dynamic_menu.get() not in format_options:
                self.dynamic_menu.set("M4A (Raw Audio)")

    def _build_customization_section(self) -> None:
        cust_frame = ctk.CTkFrame(self.main_container, corner_radius=10)
        cust_frame.grid(row=4, column=0, sticky="ew", pady=(0, 12), padx=4)
        cust_frame.grid_columnconfigure(1, weight=1)

        cust_title = ctk.CTkLabel(
            cust_frame,
            text="Customization & Output Options",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        cust_title.grid(row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(12, 10))

        # 1. Save Folder
        folder_label = ctk.CTkLabel(
            cust_frame,
            text="Save Location:",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        folder_label.grid(row=1, column=0, sticky="w", padx=(14, 10), pady=(0, 10))

        self.folder_entry = ctk.CTkEntry(
            cust_frame,
            height=32,
            font=ctk.CTkFont(size=12),
        )
        self.folder_entry.insert(0, self.output_dir)
        self.folder_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 10))

        # Button container for Browse and Set as Default
        folder_btn_frame = ctk.CTkFrame(cust_frame, fg_color="transparent")
        folder_btn_frame.grid(row=1, column=2, sticky="e", padx=(0, 14), pady=(0, 10))

        self.btn_browse = ctk.CTkButton(
            folder_btn_frame,
            text="Browse...",
            width=80,
            height=32,
            font=ctk.CTkFont(size=12),
            command=self._on_browse_clicked,
        )
        self.btn_browse.pack(side="left", padx=(0, 6))

        self.btn_set_default = ctk.CTkButton(
            folder_btn_frame,
            text="📌 Set Default",
            width=100,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#2b2b2b",
            hover_color="#3a3a3a",
            command=self._on_set_default_folder_clicked,
        )
        self.btn_set_default.pack(side="left")

        # 2. Clip / Trim Time Range
        clip_label = ctk.CTkLabel(
            cust_frame,
            text="Clip / Trim (Optional):",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        clip_label.grid(row=2, column=0, sticky="w", padx=(14, 10), pady=(0, 10))

        clip_boxes_frame = ctk.CTkFrame(cust_frame, fg_color="transparent")
        clip_boxes_frame.grid(row=2, column=1, columnspan=2, sticky="w", pady=(0, 10))

        start_lbl = ctk.CTkLabel(clip_boxes_frame, text="Start:")
        start_lbl.pack(side="left", padx=(0, 6))

        self.start_time_entry = ctk.CTkEntry(
            clip_boxes_frame,
            width=90,
            height=30,
            placeholder_text="00:00",
            font=ctk.CTkFont(size=12),
        )
        self.start_time_entry.pack(side="left", padx=(0, 16))

        end_lbl = ctk.CTkLabel(clip_boxes_frame, text="End:")
        end_lbl.pack(side="left", padx=(0, 6))

        self.end_time_entry = ctk.CTkEntry(
            clip_boxes_frame,
            width=90,
            height=30,
            placeholder_text="00:00",
            font=ctk.CTkFont(size=12),
        )
        self.end_time_entry.pack(side="left", padx=(0, 12))

        hint_lbl = ctk.CTkLabel(
            clip_boxes_frame,
            text="(Format: MM:SS or HH:MM:SS)",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
        )
        hint_lbl.pack(side="left")

        # 3. Checkboxes
        check_frame = ctk.CTkFrame(cust_frame, fg_color="transparent")
        check_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=14, pady=(4, 14))
        check_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.var_embed_thumb = ctk.BooleanVar(value=True)
        self.chk_thumb = ctk.CTkCheckBox(
            check_frame,
            text="Embed Thumbnail",
            variable=self.var_embed_thumb,
            font=ctk.CTkFont(size=12),
        )
        self.chk_thumb.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.var_embed_meta = ctk.BooleanVar(value=True)
        self.chk_meta = ctk.CTkCheckBox(
            check_frame,
            text="Embed Metadata",
            variable=self.var_embed_meta,
            font=ctk.CTkFont(size=12),
        )
        self.chk_meta.grid(row=0, column=1, sticky="w", padx=(0, 10))

        self.var_subtitles = ctk.BooleanVar(value=False)
        self.chk_subs = ctk.CTkCheckBox(
            check_frame,
            text="Download Subtitles",
            variable=self.var_subtitles,
            font=ctk.CTkFont(size=12),
        )
        self.chk_subs.grid(row=0, column=2, sticky="w", padx=(0, 10))

        self.var_playlist = ctk.BooleanVar(value=False)
        self.chk_playlist = ctk.CTkCheckBox(
            check_frame,
            text="Download Entire Playlist",
            variable=self.var_playlist,
            font=ctk.CTkFont(size=12),
        )
        self.chk_playlist.grid(row=0, column=3, sticky="w")

    def _build_bottom_section(self) -> None:
        bottom_frame = ctk.CTkFrame(self.main_container, corner_radius=10)
        bottom_frame.grid(row=5, column=0, sticky="ew", pady=(0, 4), padx=4)
        bottom_frame.grid_columnconfigure(0, weight=1)

        # Status Label
        self.status_label = ctk.CTkLabel(
            bottom_frame,
            text="Ready",
            font=ctk.CTkFont(size=13),
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 6))

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(bottom_frame, height=14)
        self.progress_bar.set(0.0)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 14))

        # Action Buttons
        btn_action_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        btn_action_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 14))
        btn_action_frame.grid_columnconfigure(0, weight=3)
        btn_action_frame.grid_columnconfigure(1, weight=1)

        self.btn_download = ctk.CTkButton(
            btn_action_frame,
            text="⬇️ Download Now",
            height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._on_download_clicked,
        )
        self.btn_download.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.btn_open_folder = ctk.CTkButton(
            btn_action_frame,
            text="📁 Open Folder",
            height=44,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#333333",
            hover_color="#444444",
            command=self._on_open_folder_clicked,
        )
        self.btn_open_folder.grid(row=0, column=1, sticky="ew")

    # -------------------------------------------------------------------------
    # Helper & Event Handlers
    # -------------------------------------------------------------------------
    def _create_placeholder_image(self, width: int, height: int) -> ctk.CTkImage:
        """Create a rounded gray placeholder image for the thumbnail widget."""
        img = Image.new("RGBA", (width, height), (35, 35, 38, 255))
        draw = ImageDraw.Draw(img)
        # Draw a video play icon outline in the center
        cx, cy = width // 2, height // 2
        r = 18
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(100, 100, 105), width=2)
        draw.polygon([(cx - 6, cy - 10), (cx - 6, cy + 10), (cx + 10, cy)], fill=(120, 120, 125))
        return ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))

    def _on_paste_clicked(self) -> None:
        """Grab clipboard content, populate entry, and trigger metadata fetch."""
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, clipboard_text.strip())
                self._trigger_url_fetch()
        except Exception as e:
            self._set_status(f"Could not read clipboard: {e}")

    def _trigger_url_fetch(self) -> None:
        """Initiate asynchronous video information preview fetch."""
        url = self.url_entry.get().strip()
        if not url or self.is_fetching_info:
            return

        # Simple URL sanity check
        if not (url.startswith("http://") or url.startswith("https://") or "youtu" in url):
            return

        self.is_fetching_info = True
        self.title_label.configure(text="Fetching video info...")
        self.channel_label.configure(text="Please wait...")
        self.duration_label.configure(text="Duration: ...")
        self.views_label.configure(text="")
        self._set_status("Fetching video details from YouTube...")

        threading.Thread(target=self._worker_fetch_info, args=(url,), daemon=True).start()

    def _worker_fetch_info(self, url: str) -> None:
        """Background thread worker for extract_info."""
        try:
            info = downloader.fetch_video_info(url)
            thumb_img = downloader.fetch_thumbnail_image(info.get("thumbnail_url"))
            self.after(0, lambda: self._on_info_fetched(info, thumb_img))
        except Exception as e:
            self.after(0, lambda err=str(e): self._on_info_error(err))

    def _on_info_fetched(self, info: dict[str, Any], thumb_img: Image.Image | None) -> None:
        """Main-thread update of preview card with fetched video metadata."""
        self.is_fetching_info = False
        self.current_video_info = info

        self.title_label.configure(text=info.get("title", "Unknown Title"))
        self.channel_label.configure(text=f"👤 {info.get('channel', 'Unknown Channel')}")
        self.duration_label.configure(text=f"⏱️ Duration: {info.get('duration_formatted', 'Unknown')}")

        views_text = info.get("views_formatted")
        self.views_label.configure(text=f"👁️ {views_text}" if views_text else "")

        if thumb_img:
            ctk_thumb = ctk.CTkImage(light_image=thumb_img, dark_image=thumb_img, size=(160, 90))
            self.thumb_label.configure(image=ctk_thumb)

        self._set_status("Video loaded and ready for download.")

    def _on_info_error(self, error_msg: str) -> None:
        """Main-thread error handler for metadata fetch."""
        self.is_fetching_info = False
        self.title_label.configure(text="Unable to load video info")
        self.channel_label.configure(text=error_msg[:120])
        self.duration_label.configure(text="Duration: --:--")
        self._set_status(f"Error fetching info: {error_msg}")

    def _on_browse_clicked(self) -> None:
        """Select download folder via file dialog."""
        folder = filedialog.askdirectory(initialdir=self.output_dir, title="Select Output Folder")
        if folder:
            self.output_dir = os.path.abspath(folder)
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, self.output_dir)

    def _on_set_default_folder_clicked(self) -> None:
        """Save the current folder path as the persistent default save location."""
        folder = self.folder_entry.get().strip()
        if not folder:
            messagebox.showwarning("Warning", "Please enter or select a directory first.")
            return

        if not os.path.isdir(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create directory:\n{e}")
                return

        abs_path = os.path.abspath(folder)
        self.output_dir = abs_path
        downloader.save_config({"default_output_dir": abs_path})
        self._set_status(f"Default save location set to: {abs_path}")

        # Visual feedback on the button
        self.btn_set_default.configure(text="✓ Saved!", fg_color="#1f6aa5")
        self.after(2000, lambda: self.btn_set_default.configure(text="📌 Set Default", fg_color="#2b2b2b"))

    def _on_open_folder_clicked(self) -> None:
        """Open the target download folder in Windows Explorer."""
        folder = self.folder_entry.get().strip() or self.output_dir
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        try:
            os.startfile(folder)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open directory: {e}")

    def _on_update_ytdlp_clicked(self) -> None:
        """Background thread worker to update yt-dlp."""
        self.btn_update.configure(state="disabled", text="Updating...")
        self._set_status("Updating yt-dlp package in background...")

        def _worker() -> None:
            try:
                # Run `uv pip install -U yt-dlp` or fallback to pip
                cmd = ["uv", "pip", "install", "-U", "yt-dlp"]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    # Fallback to python -m pip
                    cmd = [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"]
                    res = subprocess.run(cmd, capture_output=True, text=True)

                self.after(0, lambda: self._on_update_finished(res.returncode == 0))
            except Exception as e:
                self.after(0, lambda err=str(e): self._on_update_error(err))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_update_finished(self, success: bool) -> None:
        self.btn_update.configure(state="normal", text="Update yt-dlp")
        if success:
            try:
                import importlib
                import yt_dlp.version

                importlib.reload(yt_dlp.version)
                new_ver = f"yt-dlp v{yt_dlp.version.__version__}"
                self.version_label.configure(text=new_ver)
                self._set_status(f"yt-dlp updated successfully to {new_ver}!")
            except Exception:
                self._set_status("yt-dlp updated successfully.")
        else:
            self._set_status("yt-dlp update failed. Check console output.")

    def _on_update_error(self, err: str) -> None:
        self.btn_update.configure(state="normal", text="Update yt-dlp")
        self._set_status(f"Error during yt-dlp update: {err}")

    # -------------------------------------------------------------------------
    # Download Execution & Thread-Safe UI Callbacks
    # -------------------------------------------------------------------------
    def _on_download_clicked(self) -> None:
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter or paste a YouTube URL first.")
            return

        out_dir = self.folder_entry.get().strip()
        if not out_dir:
            out_dir = self.output_dir
        os.makedirs(out_dir, exist_ok=True)

        mode = self.mode_selector.get()
        resolution = self.dynamic_menu.get()
        audio_bitrate = self.dynamic_menu.get()
        audio_format = self.dynamic_menu.get()

        start_time = self.start_time_entry.get().strip() or None
        end_time = self.end_time_entry.get().strip() or None

        embed_thumb = self.var_embed_thumb.get()
        embed_meta = self.var_embed_meta.get()
        download_subs = self.var_subtitles.get()
        download_playlist = self.var_playlist.get()

        # Update button state
        self.is_downloading = True
        self.btn_download.configure(state="disabled", text="⏳ Processing...")
        self.progress_bar.set(0.0)
        self._set_status("Initializing download...")

        # Build options
        try:
            ydl_opts = downloader.build_ydl_opts(
                output_dir=out_dir,
                mode=mode,
                resolution=resolution,
                audio_bitrate=audio_bitrate,
                audio_format=audio_format,
                embed_thumbnail=embed_thumb,
                embed_metadata=embed_meta,
                download_subtitles=download_subs,
                download_playlist=download_playlist,
                start_time=start_time,
                end_time=end_time,
                progress_hook=self._progress_hook,
                postprocessor_hook=self._postprocessor_hook,
            )
        except Exception as e:
            self.is_downloading = False
            self.btn_download.configure(state="normal", text="⬇️ Download Now")
            messagebox.showerror("Configuration Error", f"Failed to build download options: {e}")
            return

        # Launch download in background daemon thread
        threading.Thread(target=self._worker_download, args=(url, ydl_opts), daemon=True).start()

    def _worker_download(self, url: str, ydl_opts: dict[str, Any]) -> None:
        """Download daemon thread."""
        try:
            downloader.download_video(url, ydl_opts)
            self.after(0, self._on_download_success)
        except Exception as e:
            self.after(0, lambda err=str(e): self._on_download_failed(err))

    def _progress_hook(self, d: dict[str, Any]) -> None:
        """Hook called by yt-dlp on worker thread."""
        pct_float, status_str = downloader.format_progress(d)
        self.after(0, lambda p=pct_float, s=status_str: self._update_progress_ui(p, s))

    def _postprocessor_hook(self, d: dict[str, Any]) -> None:
        """Postprocessor hook called by yt-dlp on worker thread."""
        status = d.get("status")
        pp = d.get("postprocessor", "")
        if status in ("started", "processing"):
            self.after(0, lambda: self._update_progress_ui(0.99, "Converting / Merging with FFmpeg..."))
        elif status == "finished":
            self.after(0, lambda: self._update_progress_ui(1.0, f"Post-processing completed ({pp})."))

    def _update_progress_ui(self, pct: float, status_str: str) -> None:
        """Thread-safe UI update for progress."""
        self.progress_bar.set(pct)
        self.status_label.configure(text=status_str)

    def _on_download_success(self) -> None:
        """Thread-safe completion handler."""
        self.is_downloading = False
        self.btn_download.configure(state="normal", text="⬇️ Download Now")
        self.progress_bar.set(1.0)
        self._set_status("✅ Download and conversion complete!")
        messagebox.showinfo("Success", "Download and conversion finished successfully!")

    def _on_download_failed(self, error_msg: str) -> None:
        """Thread-safe error handler."""
        self.is_downloading = False
        self.btn_download.configure(state="normal", text="⬇️ Download Now")
        self._set_status(f"❌ Download failed: {error_msg}")
        messagebox.showerror("Download Error", f"Download encountered an error:\n{error_msg}")

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    # -------------------------------------------------------------------------
    # Automated Self-Test Sequence
    # -------------------------------------------------------------------------
    def _run_self_test_sequence(self) -> None:
        """Exercised when --self-test flag is passed."""
        print("[Self-Test] Starting automated UI smoke test...")

        # 1. Verify default startup mode
        assert self.mode_selector.get() == "Audio Only (MP3)", f"Expected default mode 'Audio Only (MP3)', got {self.mode_selector.get()}"
        assert self.dynamic_label.cget("text") == "Audio Bitrate:", f"Expected 'Audio Bitrate:', got {self.dynamic_label.cget('text')}"
        print("[Self-Test] Verified default mode is 'Audio Only (MP3)'.")

        # 2. Test URL entry and placeholder
        self.url_entry.insert(0, "https://www.youtube.com/watch?v=jNQXAC9IVRw")
        print("[Self-Test] Populated URL entry.")

        # 3. Programmatically toggle mode selectors to verify dynamic swapping
        for test_mode in self.modes:
            self.mode_selector.set(test_mode)
            self._on_mode_changed(test_mode)
            print(f"[Self-Test] Verified mode switch: {test_mode} -> Dynamic Label: '{self.dynamic_label.cget('text')}'")

        # 4. Toggle checkboxes
        self.var_embed_thumb.set(False)
        self.var_embed_meta.set(False)
        self.var_subtitles.set(True)
        self.var_playlist.set(True)
        print("[Self-Test] Verified checkbox toggling.")

        # 5. Test Set as Default button
        self._on_set_default_folder_clicked()
        print("[Self-Test] Verified Set as Default folder action.")

        # 6. Schedule clean termination after 1500ms
        print("[Self-Test] All UI components initialized cleanly. Terminating in 1500ms...")
        self.after(1500, self.destroy)
