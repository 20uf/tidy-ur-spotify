"""Entry point for Tidy ur Spotify — classify liked songs into themed playlists."""

import logging
import os
import sys
from pathlib import Path

from src.version import __version__


def _setup_logging() -> None:
    level_name = os.getenv("TIDY_SPOTIFY_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    log_format = "%(asctime)s %(levelname)s %(name)s - %(message)s"
    date_format = "%H:%M:%S"
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    # In debug mode, persist logs to a local file so runs can be inspected later.
    if level <= logging.DEBUG:
        log_file = os.getenv("TIDY_SPOTIFY_LOG_FILE", "logs/tidy-ur-spotify-debug.log")
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, mode="w", encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True,
    )


def main():
    if "--version" in sys.argv or "-v" in sys.argv:
        print(f"Tidy ur Spotify {__version__}")
        sys.exit(0)

    _setup_logging()
    logging.getLogger(__name__).info("Starting Tidy ur Spotify %s", __version__)

    from src.ui.app import run_app
    run_app()


if __name__ == "__main__":
    main()
