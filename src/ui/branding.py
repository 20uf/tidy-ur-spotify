"""Shared branding controls for the Flet UI."""

from pathlib import Path

import flet as ft

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BRANDING_DIR = PROJECT_ROOT / "assets" / "branding"
UI_LOGO_CANDIDATES = [
    BRANDING_DIR / "logo-in-app.png",
]
MARK_LOGO_CANDIDATES = [
    BRANDING_DIR / "logo-mark.png",
    BRANDING_DIR / "icon.png",
]
APP_ICON_CANDIDATES = [
    BRANDING_DIR / "icon.png",
]


def _first_existing_path(candidates: list[Path]) -> str:
    for path in candidates:
        if path.exists():
            return str(path)
    return ""


def logo_mark_src() -> str:
    """Return symbol-only logo path for compact UI placements."""
    return _first_existing_path(MARK_LOGO_CANDIDATES)


def logo_ui_src() -> str:
    """Return in-app branding logo path."""
    return _first_existing_path(UI_LOGO_CANDIDATES)


def app_icon_src() -> str:
    """Return app/window icon path."""
    return _first_existing_path(APP_ICON_CANDIDATES)


def build_logo(size: int = 72) -> ft.Control:
    """Return in-app logo with a safe fallback when asset is missing."""
    src = logo_ui_src() or logo_mark_src()
    if src:
        return ft.Image(src=src, width=size, height=size)
    return ft.Container(width=size, height=size)


def build_logo_mark(size: int = 72) -> ft.Control:
    """Return compact symbol logo for small placements."""
    src = logo_mark_src()
    if src:
        return ft.Image(src=src, width=size, height=size)
    return ft.Container(width=size, height=size)


def responsive_logo_size(page: ft.Page, small: int = 72, medium: int = 100, large: int = 128) -> int:
    """Pick a logo size from the current window width."""
    width = int(getattr(page.window, "width", 0) or 0)
    if width > 0 and width < 720:
        return small
    if width > 0 and width < 1100:
        return medium
    return large
