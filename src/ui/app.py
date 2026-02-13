"""Main Flet application — orchestrates setup and classification views."""

import atexit
import json
import os
import platform
import signal
import socket
import sys
import threading
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import flet as ft

from src.adapters.classifier import DEFAULT_PROVIDER, PROVIDERS
from src.adapters.config.json_config_adapter import JsonConfigAdapter
from src.adapters.progress.json_progress_adapter import JsonProgressAdapter
from src.adapters.spotify.auth import get_spotify_client
from src.adapters.spotify.playlist_adapter import SpotifyPlaylistAdapter
from src.adapters.spotify.track_adapter import SpotifyTrackAdapter
from src.domain.model import Theme
from src.ui.theme import ACCENT, BG, BG_CARD, FG, FG_DIM
from src.version import __version__

THEMES = {
    "ambiance": Theme(
        key="ambiance",
        name="Ambiance",
        description="Mid-tempo, groovy, warm, melodic tracks. Can move gently but stays chill.",
        shortcut="1",
    ),
    "lets_dance": Theme(
        key="lets_dance",
        name="Let's Dance",
        description="Upbeat, danceable, recent party hits. High energy.",
        shortcut="2",
    ),
}

THEMES_DICT = {k: {"name": v.name, "description": v.description, "key": v.shortcut} for k, v in THEMES.items()}

LOCK_FILE = Path.home() / ".tidy-ur-spotify.lock"


def _get_lock_pid() -> int | None:
    """Read PID from lock file, return None if not found or invalid."""
    try:
        if LOCK_FILE.exists():
            return int(LOCK_FILE.read_text().strip())
    except (ValueError, OSError):
        pass
    return None


def _is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _kill_previous_instance() -> bool:
    """Kill previous instance if running. Returns True if killed."""
    pid = _get_lock_pid()
    if pid and _is_process_running(pid):
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except OSError:
            return False
    return False


def _create_lock():
    """Create lock file with current PID."""
    LOCK_FILE.write_text(str(os.getpid()))
    atexit.register(_remove_lock)


def _remove_lock():
    """Remove lock file on exit."""
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def _is_port_available(port: int) -> bool:
    """Check if a port is available for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _get_port_from_uri(uri: str) -> int:
    """Extract port number from redirect URI."""
    parsed = urlparse(uri)
    return parsed.port or 8888


def _generate_bug_report(error: Exception, config: dict, context: str = "") -> str:
    """Generate a bug report with debug context."""
    # Mask sensitive data
    safe_config = {}
    for key, value in config.items():
        if any(secret in key.lower() for secret in ["secret", "key", "token", "password"]):
            safe_config[key] = "***MASKED***" if value else "(empty)"
        else:
            safe_config[key] = value

    report = {
        "timestamp": datetime.now().isoformat(),
        "version": __version__,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        },
        "context": context,
        "error": {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        },
        "config": safe_config,
    }
    return json.dumps(report, indent=2, default=str)


def run_app():
    # Single instance: kill previous instance if running
    _kill_previous_instance()
    _create_lock()

    def main(page: ft.Page):
        page.title = f"Tidy ur Spotify {__version__}"
        page.bgcolor = BG
        page.window.width = 700
        page.window.height = 700
        page.window.min_width = 500
        page.window.min_height = 600

        config = JsonConfigAdapter()

        def show_error_view(error: Exception, context: str, cfg: dict, start_step: int = 1):
            """Display error view with bug report download option."""
            report_content = _generate_bug_report(error, cfg, context)

            def save_report(_):
                picker = ft.FilePicker(on_result=lambda e: _save_report_file(e, report_content))
                page.overlay.append(picker)
                page.update()
                picker.save_file(
                    file_name=f"tidy-ur-spotify-bug-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json",
                    allowed_extensions=["json"],
                )

            def _save_report_file(e: ft.FilePickerResultEvent, content: str):
                if e.path:
                    Path(e.path).write_text(content)

            # Determine user-friendly error message
            error_str = str(error)
            if "INVALID_CLIENT" in error_str or "Invalid redirect URI" in error_str:
                hint = "The redirect URI in your Spotify app settings doesn't match.\nExpected: http://127.0.0.1:8888/callback"
            elif "invalid_client" in error_str.lower():
                hint = "Your Client ID or Client Secret is incorrect."
            elif "Address already in use" in error_str:
                hint = "Port 8888 is already in use. Close other instances and retry."
            else:
                hint = "Check your Spotify Developer credentials and try again."

            page.controls.clear()
            page.add(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.ERROR_OUTLINE, color="red", size=48),
                            ft.Text("Authentication Error", color="red", size=20, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=ft.Text(hint, color=FG, size=14, text_align=ft.TextAlign.CENTER),
                                padding=ft.padding.symmetric(horizontal=20),
                            ),
                            ft.Container(
                                content=ft.Text(
                                    f"Technical details: {type(error).__name__}",
                                    color=FG_DIM,
                                    size=11,
                                ),
                                padding=ft.padding.only(top=10),
                            ),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.ElevatedButton(
                                            "Reconfigure",
                                            icon=ft.Icons.SETTINGS,
                                            on_click=lambda _: start_setup_wizard(start_step),
                                            bgcolor=ACCENT,
                                            color="white",
                                        ),
                                        ft.OutlinedButton(
                                            "Download Bug Report",
                                            icon=ft.Icons.DOWNLOAD,
                                            on_click=save_report,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=12,
                                ),
                                padding=ft.padding.only(top=20),
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                )
            )
            page.update()

        def start_setup_wizard(start_step: int = 0):
            """Show setup wizard to reconfigure, optionally starting at a specific step."""
            page.controls.clear()
            from src.ui.setup_view import SetupView
            setup = SetupView(page=page, config=config, on_complete=launch_classification, start_step=start_step)
            setup.expand = True
            page.add(setup)
            page.update()

        def launch_classification():
            page.controls.clear()
            page.add(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.ProgressRing(color=ACCENT),
                            ft.Text("Authenticating with Spotify...", color=FG, size=14),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                    ),
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                )
            )
            page.update()

            cfg = config.load()
            redirect_uri = cfg.get("spotify_redirect_uri", "http://127.0.0.1:8888/callback")
            port = _get_port_from_uri(redirect_uri)

            if not _is_port_available(port):
                page.controls.clear()
                page.add(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Port unavailable", color="red", size=18, weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    f"Port {port} is already in use by another application.",
                                    color=FG,
                                    size=14,
                                ),
                                ft.Text(
                                    "Close any other instance of Tidy ur Spotify or application using this port, then restart.",
                                    color=FG_DIM,
                                    size=12,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=8,
                        ),
                        expand=True,
                        alignment=ft.Alignment(0, 0),
                    )
                )
                page.update()
                return

            try:
                sp = get_spotify_client(
                    client_id=cfg["spotify_client_id"],
                    client_secret=cfg["spotify_client_secret"],
                    redirect_uri=redirect_uri,
                )
                user = sp.current_user()
            except Exception as e:
                show_error_view(e, "Spotify authentication", cfg, start_step=1)
                return

            page.controls.clear()
            page.add(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.ProgressRing(color=ACCENT),
                            ft.Text(f"Logged in as {user['display_name']}", color=FG, size=14),
                            ft.Text("Fetching liked songs...", color=FG_DIM, size=12),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                )
            )
            page.update()

            track_source = SpotifyTrackAdapter(sp)
            tracks = track_source.fetch_all()

            if not tracks:
                page.controls.clear()
                page.add(ft.Text("No liked songs found.", color=FG, size=14))
                page.update()
                return

            # Build classifier adapter
            provider = cfg.get("llm_provider", DEFAULT_PROVIDER)
            api_key = cfg.get("llm_api_key", "")
            model = cfg.get("llm_model", "") or PROVIDERS[provider]["default_model"]

            if provider == "anthropic":
                from src.adapters.classifier.anthropic_adapter import AnthropicClassifierAdapter
                classifier = AnthropicClassifierAdapter(api_key=api_key, model=model, themes=THEMES_DICT)
            else:
                from src.adapters.classifier.openai_adapter import OpenAIClassifierAdapter
                classifier = OpenAIClassifierAdapter(api_key=api_key, model=model, themes=THEMES_DICT)

            playlist = SpotifyPlaylistAdapter(sp, THEMES_DICT)
            progress = JsonProgressAdapter()

            from src.ui.classify_view import ClassifyView
            view = ClassifyView(
                page=page,
                tracks=tracks,
                themes=THEMES,
                classifier=classifier,
                playlist=playlist,
                progress=progress,
            )

            page.on_keyboard_event = view.handle_keyboard
            page.controls.clear()
            page.add(view)
            page.update()

        def _check_for_update():
            """Run update check in background thread, show banner if newer version exists."""
            from src.usecases.check_update import CheckUpdateUseCase
            info = CheckUpdateUseCase().execute()
            if info:
                banner = ft.Banner(
                    bgcolor=BG_CARD,
                    content=ft.Text(
                        f"A new version is available: v{info.latest} (current: v{info.current})",
                        color=FG, size=13,
                    ),
                    actions=[
                        ft.TextButton(
                            "Download",
                            on_click=lambda _: webbrowser.open(info.release_url),
                            style=ft.ButtonStyle(color=ACCENT),
                        ),
                        ft.TextButton(
                            "Dismiss",
                            on_click=lambda _: _dismiss_banner(banner),
                            style=ft.ButtonStyle(color=FG_DIM),
                        ),
                    ],
                )
                page.overlay.append(banner)
                banner.open = True
                page.update()

        def _dismiss_banner(banner):
            banner.open = False
            page.update()

        # Check for updates in background
        threading.Thread(target=_check_for_update, daemon=True).start()

        if not config.is_configured():
            from src.ui.setup_view import SetupView
            setup = SetupView(page=page, config=config, on_complete=launch_classification)
            setup.expand = True
            page.add(setup)
        else:
            launch_classification()

    ft.app(target=main)
