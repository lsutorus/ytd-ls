"""Main entry point for YouTube Downloader & Converter application."""

from __future__ import annotations

import argparse
import sys
from app import YouTubeDownloaderApp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YouTube Downloader LS")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run non-blocking automated UI smoke test and exit cleanly with code 0",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = YouTubeDownloaderApp(self_test=args.self_test)
    app.mainloop()
    sys.exit(0)


if __name__ == "__main__":
    main()
