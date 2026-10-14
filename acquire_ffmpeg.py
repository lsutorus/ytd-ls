"""Utility script to acquire FFmpeg and FFprobe binaries.

Checks if ffmpeg.exe and ffprobe.exe exist in ./bin/ or on system PATH.
If missing from both, downloads a Windows static build, extracts them to ./bin/,
and cleans up temporary archive files.
"""

import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path


def get_bin_dir() -> Path:
    base_dir = Path(__file__).resolve().parent
    bin_dir = base_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    return bin_dir


def check_local_binaries(bin_dir: Path) -> bool:
    ffmpeg_exe = bin_dir / "ffmpeg.exe"
    ffprobe_exe = bin_dir / "ffprobe.exe"
    return ffmpeg_exe.is_file() and ffprobe_exe.is_file()


def check_path_binaries() -> tuple[str | None, str | None]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    return ffmpeg, ffprobe


def copy_from_path_to_bin(ffmpeg_path: str, ffprobe_path: str, bin_dir: Path) -> None:
    print(f"Found system FFmpeg: {ffmpeg_path}")
    print(f"Found system FFprobe: {ffprobe_path}")
    dst_ffmpeg = bin_dir / "ffmpeg.exe"
    dst_ffprobe = bin_dir / "ffprobe.exe"
    
    if not dst_ffmpeg.is_file():
        # Follow symlinks if any
        real_ffmpeg = os.path.realpath(ffmpeg_path)
        shutil.copy2(real_ffmpeg, dst_ffmpeg)
        print(f"Copied {real_ffmpeg} -> {dst_ffmpeg}")
        
    if not dst_ffprobe.is_file():
        real_ffprobe = os.path.realpath(ffprobe_path)
        shutil.copy2(real_ffprobe, dst_ffprobe)
        print(f"Copied {real_ffprobe} -> {dst_ffprobe}")


def download_and_extract_ffmpeg(bin_dir: Path) -> None:
    # URL for static Windows build from gyan.dev
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = bin_dir / "ffmpeg.zip"
    
    print(f"Downloading FFmpeg from {url}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response, open(zip_path, "wb") as out_file:
        shutil.copyfileobj(response, out_file)
        
    print("Extracting ffmpeg.exe and ffprobe.exe...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for file in zip_ref.namelist():
            if file.endswith("bin/ffmpeg.exe"):
                with zip_ref.open(file) as source, open(bin_dir / "ffmpeg.exe", "wb") as target:
                    shutil.copyfileobj(source, target)
                print("Extracted ffmpeg.exe")
            elif file.endswith("bin/ffprobe.exe"):
                with zip_ref.open(file) as source, open(bin_dir / "ffprobe.exe", "wb") as target:
                    shutil.copyfileobj(source, target)
                print("Extracted ffprobe.exe")
                
    if zip_path.exists():
        zip_path.unlink()
        print("Cleaned up ffmpeg.zip")


def ensure_ffmpeg() -> Path:
    bin_dir = get_bin_dir()
    if check_local_binaries(bin_dir):
        print(f"FFmpeg and FFprobe already present in {bin_dir}")
        return bin_dir

    ffmpeg_path, ffprobe_path = check_path_binaries()
    if ffmpeg_path and ffprobe_path:
        copy_from_path_to_bin(ffmpeg_path, ffprobe_path, bin_dir)
        return bin_dir

    print("FFmpeg not found in PATH or bin/. Initiating automated download...")
    download_and_extract_ffmpeg(bin_dir)
    return bin_dir


if __name__ == "__main__":
    ensure_ffmpeg()
