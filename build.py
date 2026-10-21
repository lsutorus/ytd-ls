"""Automated build and verification script for YouTube Downloader LS.

Ensures that versions match across configs, completely cleans caches,
builds the standalone executable, verifies embedded bytecode version constants,
and packages the Windows MSI installer.
"""

from __future__ import annotations

import hashlib
import json
import marshal
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent


def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def check_version_consistency() -> str:
    print("[1/5] Checking version consistency across project files...")

    # 1. downloader.py
    downloader_file = ROOT_DIR / "downloader.py"
    dl_match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', downloader_file.read_text(encoding="utf-8"))
    if not dl_match:
        raise ValueError("Could not find APP_VERSION in downloader.py")
    ver_dl = dl_match.group(1)

    # 2. pyproject.toml
    pyproject_file = ROOT_DIR / "pyproject.toml"
    pyproj_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', pyproject_file.read_text(encoding="utf-8"))
    if not pyproj_match:
        raise ValueError("Could not find version in pyproject.toml")
    ver_pyproj = pyproj_match.group(1)

    # 3. installer.wxs
    wxs_file = ROOT_DIR / "installer.wxs"
    wxs_match = re.search(r'Version\s*=\s*["\']([^"\']+)["\']', wxs_file.read_text(encoding="utf-8"))
    if not wxs_match:
        raise ValueError("Could not find Version in installer.wxs")
    ver_wxs = wxs_match.group(1)

    print(f"       downloader.py: {ver_dl}")
    print(f"      pyproject.toml: {ver_pyproj}")
    print(f"       installer.wxs: {ver_wxs}")

    if not (ver_dl == ver_pyproj == ver_wxs):
        raise ValueError(
            f"Version mismatch detected!\n"
            f"  downloader.py: {ver_dl}\n"
            f"  pyproject.toml: {ver_pyproj}\n"
            f"  installer.wxs: {ver_wxs}"
        )

    print(f"      -> All versions consistent: v{ver_dl}")
    return ver_dl


def clean_build_artifacts() -> None:
    print("[2/5] Cleaning previous build caches and artifacts...")
    build_dir = ROOT_DIR / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)
        print("      Removed build/ directory.")

    spec_name = ROOT_DIR / "YouTubeDownloaderLS.spec"
    if not spec_name.exists():
        raise FileNotFoundError(f"Missing spec file: {spec_name}")


def build_executable() -> Path:
    print("[3/5] Building executable with PyInstaller (--clean)...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(ROOT_DIR / "YouTubeDownloaderLS.spec"),
    ]
    res = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if res.returncode != 0:
        raise RuntimeError(f"PyInstaller build failed with exit code {res.returncode}")

    exe_path = ROOT_DIR / "dist" / "YouTubeDownloaderLS.exe"
    if not exe_path.is_file():
        raise FileNotFoundError(f"Expected executable not found at: {exe_path}")

    print(f"      -> Built: {exe_path} ({exe_path.stat().st_size:,} bytes)")
    return exe_path


def verify_executable_bytecode(exe_path: Path, expected_version: str) -> None:
    print(f"[4/5] Verifying embedded bytecode version in {exe_path.name}...")
    from PyInstaller.utils.cliutils.archive_viewer import CArchiveReader

    arch = CArchiveReader(str(exe_path))
    pyz = arch.open_embedded_archive("PYZ.pyz")
    if "downloader" not in pyz.toc:
        raise ValueError("Module 'downloader' not found in embedded PYZ archive!")

    code = pyz.extract("downloader")
    version_found = False
    for c in code.co_consts:
        if isinstance(c, str) and c == expected_version:
            version_found = True
            break

    if not version_found:
        found_consts = [c for c in code.co_consts if isinstance(c, str) and re.match(r"^\d+\.\d+", c)]
        raise ValueError(
            f"Bytecode verification failed!\n"
            f"  Expected version: {expected_version}\n"
            f"  Found version-like constants in downloader: {found_consts}"
        )

    print(f"      -> Verified: downloader module contains APP_VERSION = '{expected_version}'")


def build_msi_installer(version: str) -> Path:
    print(f"[5/5] Building MSI installer for v{version} using WiX Toolset...")
    msi_path = ROOT_DIR / "dist" / f"YouTubeDownloaderLS-v{version}.msi"

    cmd = [
        "wix",
        "build",
        str(ROOT_DIR / "installer.wxs"),
        "-ext",
        "WixToolset.UI.wixext",
        "-o",
        str(msi_path),
    ]
    res = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if res.returncode != 0:
        raise RuntimeError(f"WiX build failed with exit code {res.returncode}")

    if not msi_path.is_file():
        raise FileNotFoundError(f"Expected MSI not found at: {msi_path}")

    sha = get_file_sha256(msi_path)
    print(f"      -> Built MSI: {msi_path.name} ({msi_path.stat().st_size:,} bytes)")
    print(f"      -> SHA256: {sha}")
    return msi_path


def main() -> None:
    print("=" * 60)
    print("YouTube Downloader LS - Automated Build & Verification Pipeline")
    print("=" * 60)
    version = check_version_consistency()
    clean_build_artifacts()
    exe_path = build_executable()
    verify_executable_bytecode(exe_path, version)
    msi_path = build_msi_installer(version)
    print("=" * 60)
    print(f"BUILD SUCCEEDED: v{version}")
    print(f"MSI Asset: {msi_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
