"""Entry point for Tidy ur Spotify — classify liked songs into themed playlists."""

import sys

from src.version import __version__


def main():
    if "--version" in sys.argv or "-v" in sys.argv:
        print(f"Tidy ur Spotify {__version__}")
        sys.exit(0)

    from src.ui.app import run_app
    run_app()


if __name__ == "__main__":
    main()
