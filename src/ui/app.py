"""Main Flet application — orchestrates setup and classification views."""

import atexit
import asyncio
import json
import logging
import os
import platform
import signal
import socket
import sys
import threading
import time
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import flet as ft

from src.adapters.classifier import DEFAULT_PROVIDER, PROVIDERS
from src.adapters.cache.local_cache import clear_cache
from src.adapters.config.json_config_adapter import JsonConfigAdapter
from src.adapters.progress.json_progress_adapter import JsonProgressAdapter
from src.adapters.spotify.auth import get_spotify_client
from src.adapters.spotify.dry_run_playlist_adapter import DryRunPlaylistAdapter
from src.adapters.spotify.playlist_adapter import SpotifyPlaylistAdapter
from src.adapters.spotify.track_adapter import SpotifyTrackAdapter
from src.domain.model import Theme
from src.ui.branding import app_icon_src, build_logo
from src.ui.legal import LEGAL_ACK_LABEL, LEGAL_DISCLAIMER_FULL
from src.ui.theme import ACCENT, BG, BG_CARD, BG_INPUT, BORDER, DANGER, FG, FG_DIM
from src.ui.workflow_header import build_workflow_header
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
    "original_soundtracks": Theme(
        key="original_soundtracks",
        name="Original Soundtracks",
        description="Film and series soundtracks, orchestral scores, and cinematic instrumentals.",
        shortcut="3",
    ),
}

THEMES_DICT = {k: {"name": v.name, "description": v.description, "key": v.shortcut} for k, v in THEMES.items()}

LOCK_FILE = Path.home() / ".tidy-ur-spotify.lock"
SIMULATION_ENV_VAR = "TIDY_SPOTIFY_SIMULATION"
DISCLAIMER_LOGO_SIZE = 176
READY_LOGO_SIZE = 280
RUNNER_UPCOMING_BG = "#1E293B"
RUNNER_CURRENT_BG = "#1DB95480"
RUNNER_DONE_BG = "#243244"
RUNNER_UPCOMING_TEXT = "#B0BFD1"
RUNNER_DONE_TEXT = "#7C8BA3"
PRE_ANALYSIS_BATCH_SIZE = 10
RUNNER_DONE_LABEL_COUNT = 12
RUNNER_UPCOMING_LABEL_COUNT = 8
RUNNER_CURRENT_LABEL_COUNT = 10
RUNNER_EVENT_MAX = 120
PAUSE_COLOR = "#F59E0B"

logger = logging.getLogger("tidy_ur_spotify.ui")


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
    logger.info("App boot sequence started")

    def main(page: ft.Page):
        page.title = f"Tidy ur Spotify {__version__}"
        page.bgcolor = BG
        page.window.width = 980
        page.window.height = 900
        page.window.min_width = 700
        page.window.min_height = 760
        icon_path = app_icon_src()
        if hasattr(page.window, "icon") and icon_path:
            page.window.icon = icon_path

        config = JsonConfigAdapter()

        def build_section(title: str, controls: list[ft.Control], accent: bool = False, width: int = 680) -> ft.Container:
            return ft.Container(
                width=width,
                bgcolor=BG_CARD,
                border=ft.border.all(2 if accent else 1, ACCENT if accent else BORDER),
                border_radius=10,
                padding=14,
                content=ft.Column(
                    [
                        ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=ACCENT if accent else FG),
                        ft.Container(height=1, bgcolor=BORDER),
                        *controls,
                    ],
                    spacing=8,
                ),
            )

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
            logger.info("Opening setup wizard (step=%s)", start_step)
            page.on_keyboard_event = None
            page.on_resized = None
            page.controls.clear()
            from src.ui.setup_view import SetupView
            setup = SetupView(
                page=page,
                config=config,
                on_complete=launch_classification,
                start_step=start_step,
                on_cancel=lambda: launch_classification() if config.is_configured() else show_legal_gate(),
            )
            setup.expand = True
            page.add(setup)
            page.update()

        def show_legal_gate():
            cfg = config.load()
            logger.info("Showing legal gate (acknowledged=%s)", bool(cfg.get("legal_acknowledged", False)))

            logo_control = build_logo(DISCLAIMER_LOGO_SIZE)
            ack_checkbox = ft.Checkbox(
                label=LEGAL_ACK_LABEL,
                value=bool(cfg.get("legal_acknowledged", False)),
                check_color=BG,
                fill_color=ACCENT,
                label_style=ft.TextStyle(color=FG),
            )
            continue_button = ft.ElevatedButton(
                "Continue",
                disabled=not bool(cfg.get("legal_acknowledged", False)),
                bgcolor=ACCENT,
                color="white",
            )

            def on_ack_change(e):
                continue_button.disabled = not bool(e.control.value)
                page.update()

            def on_continue(_):
                cfg["legal_acknowledged"] = bool(ack_checkbox.value)
                config.save(cfg)
                logger.info("Legal disclaimer acknowledged, continuing")
                if config.is_configured():
                    launch_classification()
                else:
                    start_setup_wizard(0)

            ack_checkbox.on_change = on_ack_change
            continue_button.on_click = on_continue

            page.on_keyboard_event = None
            page.on_resized = None
            page.controls.clear()
            page.add(
                ft.Container(
                    content=ft.Column(
                        [
                            logo_control,
                            ft.Text(
                                "Disclaimer acknowledgment required",
                                size=22,
                                weight=ft.FontWeight.BOLD,
                                color=FG,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            build_section(
                                "Safety and responsibility",
                                [
                                    ft.Text(LEGAL_DISCLAIMER_FULL, color=FG_DIM, size=12),
                                ],
                                accent=True,
                                width=700,
                            ),
                            build_section(
                                "Required confirmation",
                                [
                                    ft.Row([ack_checkbox], alignment=ft.MainAxisAlignment.CENTER),
                                    ft.Text(
                                        "You must accept this disclaimer before any setup or classification.",
                                        size=11,
                                        color=FG_DIM,
                                        text_align=ft.TextAlign.CENTER,
                                    ),
                                    ft.Row([continue_button], alignment=ft.MainAxisAlignment.CENTER),
                                ],
                                width=700,
                            ),
                        ],
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                )
            )
            page.update()

        def launch_classification():
            logger.info("Launching classification home")
            page.on_keyboard_event = None
            page.on_resized = None

            def open_disclaimer(_):
                dialog = ft.AlertDialog(
                    title=ft.Text("Disclaimer"),
                    content=ft.Text(LEGAL_DISCLAIMER_FULL),
                    actions=[ft.TextButton("Close", on_click=lambda _: close_disclaimer())],
                )

                def close_disclaimer():
                    dialog.open = False
                    page.update()

                page.overlay.append(dialog)
                dialog.open = True
                page.update()

            page.controls.clear()
            page.add(
                ft.Container(
                    content=ft.Column(
                        [
                            build_logo(84),
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
            simulation_mode = bool(cfg.get("simulation_mode", False)) or _is_truthy(os.getenv(SIMULATION_ENV_VAR, ""))
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
                logger.info("Spotify auth success (user=%s)", user.get("display_name") or user.get("id"))
            except Exception as e:
                logger.exception("Spotify authentication failed")
                show_error_view(e, "Spotify authentication", cfg, start_step=0)
                return

            page.controls.clear()
            page.add(
                ft.Container(
                    content=ft.Column(
                        [
                            build_logo(72),
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
            logger.info("Liked tracks loaded (count=%s)", len(tracks))

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

            def start_session(audit_mode: bool):
                cfg["simulation_mode"] = audit_mode
                config.save(cfg)

                if audit_mode:
                    playlist = DryRunPlaylistAdapter()
                else:
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
                    simulation_mode=audit_mode,
                    on_back_to_step2=lambda: launch_classification(),
                )

                page.on_keyboard_event = view.handle_keyboard
                page.on_resized = view.handle_resize
                page.controls.clear()
                page.add(view)
                page.update()

            force_audit = _is_truthy(os.getenv(SIMULATION_ENV_VAR, ""))
            radio_standard = ft.Radio(
                value="standard",
                label="Standard mode (writes to Spotify)",
                disabled=force_audit,
            )
            radio_audit = ft.Radio(
                value="audit",
                label="Audit mode (no writes)",
                disabled=force_audit,
            )
            session_mode = ft.RadioGroup(
                value="audit" if simulation_mode or force_audit else "standard",
                content=ft.Column(
                    [
                        radio_standard,
                        radio_audit,
                    ],
                    spacing=4,
                ),
            )

            forced_msg = None
            if force_audit:
                forced_msg = ft.Text(
                    f"Audit mode forced by {SIMULATION_ENV_VAR}=1",
                    size=11,
                    color=FG_DIM,
                )

            preview_progress = JsonProgressAdapter()
            preview_session = preview_progress.load()
            resume_index = 0
            if preview_session:
                resume_index = min(max(preview_session.current_index, 0), max(len(tracks) - 1, 0))

            track_by_id = {track.id: track for track in tracks}
            analysis_total = max(len(tracks) - resume_index, 0)

            analysis_status = ft.Text("Ready to analyze.", size=11, color=FG_DIM)
            analysis_metrics = ft.Text("", size=11, color=FG_DIM)
            analysis_progress = ft.ProgressBar(value=0, bgcolor=BG_INPUT, color=ACCENT, width=float("inf"))
            ai_activity_title = ft.Text("AI waiting.", size=13, color=FG_DIM, weight=ft.FontWeight.BOLD)
            analysis_activity = ft.ProgressRing(width=14, height=14, color=ACCENT, visible=False)
            setup_activity = ft.ProgressRing(width=14, height=14, color=ACCENT, visible=False)
            disconnect_activity = ft.ProgressRing(width=14, height=14, color=DANGER, visible=False)
            last_event_label = ft.Text("", size=11, color=FG_DIM)
            analysis_events = ft.ListView(spacing=4, auto_scroll=True, expand=True)

            upcoming_list = ft.ListView(spacing=4, auto_scroll=False, expand=True)
            current_list = ft.ListView(spacing=4, auto_scroll=False, expand=True)
            done_list = ft.ListView(spacing=4, auto_scroll=False, expand=True)

            analysis_state = {
                "running": False,
                "paused": False,
                "cancel_requested": False,
                "processed_ids": [],
                "current_ids": [],
                "next_index": resume_index,
                "batch_done": 0,
                "batch_total": 0,
                "active_batch": 0,
                "has_run": False,
                "completed": False,
                "ai_animating": False,
            }

            start_button = ft.ElevatedButton("Start analysis", bgcolor=ACCENT, color="white")
            pause_button = ft.ElevatedButton("Pause", bgcolor=PAUSE_COLOR, color="white")
            cancel_button = ft.ElevatedButton("Cancel", bgcolor=DANGER, color="white")

            def _push_event(message: str, color: str = FG_DIM):
                logger.info("Pre-analysis event: %s", message)
                last_event_label.value = f"Latest event: {message}"
                last_event_label.color = color
                timestamp = datetime.now().strftime("%H:%M:%S")
                analysis_events.controls.append(ft.Text(f"[{timestamp}] {message}", size=10, color=color))
                if len(analysis_events.controls) > RUNNER_EVENT_MAX:
                    analysis_events.controls.pop(0)

            async def _animate_ai_title():
                if analysis_state["ai_animating"]:
                    return
                analysis_state["ai_animating"] = True
                slogans = [
                    "Spotifing",
                    "Playli-stitching",
                    "Groove mining",
                    "Beat sorting",
                ]
                tick = 0
                try:
                    while analysis_state["running"] and not analysis_state["paused"]:
                        base = slogans[tick % len(slogans)]
                        dots = "." * ((tick % 3) + 1)
                        ai_activity_title.value = f"{base}{dots}"
                        ai_activity_title.color = ACCENT
                        page.update()
                        tick += 1
                        await asyncio.sleep(0.45)
                finally:
                    analysis_state["ai_animating"] = False

            def _best_suggestion_label(track_id: str) -> str:
                suggestions = classifier.get_suggestions(track_id)
                if not suggestions:
                    return "analysis in progress"
                best = max(suggestions, key=lambda suggestion: suggestion.confidence)
                theme = THEMES.get(best.theme_key)
                theme_name = theme.name if theme else best.theme_key
                return f"{theme_name} ({best.confidence:.0%})"

            def _refresh_track_runner():
                upcoming_list.controls.clear()
                current_list.controls.clear()
                done_list.controls.clear()

                upcoming_tracks = tracks[analysis_state["next_index"] : analysis_state["next_index"] + RUNNER_UPCOMING_LABEL_COUNT]
                for track in upcoming_tracks:
                    upcoming_list.controls.append(ft.Text(f"• {track.artist} - {track.name}", size=11, color=RUNNER_UPCOMING_TEXT))
                if not upcoming_tracks:
                    upcoming_list.controls.append(ft.Text("• No pending tracks.", size=11, color=FG_DIM))

                current_items = 0
                for track_id in analysis_state["current_ids"][:RUNNER_CURRENT_LABEL_COUNT]:
                    track = track_by_id.get(track_id)
                    if track:
                        current_list.controls.append(
                            ft.Text(f"• {track.artist} - {track.name}", size=11, color=ACCENT, weight=ft.FontWeight.W_600)
                        )
                        current_items += 1

                if analysis_state["running"] and current_items == 0:
                    current_list.controls.append(ft.Text("• Preparing next batch...", size=11, color=FG_DIM))

                recent_done = analysis_state["processed_ids"][-RUNNER_DONE_LABEL_COUNT:]
                for track_id in reversed(recent_done):
                    track = track_by_id.get(track_id)
                    if track:
                        done_list.controls.append(
                            ft.Text(
                                f"• {track.artist} - {track.name} -> {_best_suggestion_label(track_id)}",
                                size=11,
                                color=RUNNER_DONE_TEXT,
                            )
                        )

                if analysis_state["batch_total"] > 0:
                    progress_value = analysis_state["batch_done"] / analysis_state["batch_total"]
                    if analysis_state["running"] and analysis_state["current_ids"]:
                        progress_value += 0.5 / analysis_state["batch_total"]
                    analysis_progress.value = min(progress_value, 1.0)
                else:
                    analysis_progress.value = 0

                if analysis_total > 0:
                    lot_total_display = analysis_state["batch_total"] if analysis_state["batch_total"] > 0 else 0
                    analysis_metrics.value = (
                        f"Processed tracks: {len(analysis_state['processed_ids'])}/{analysis_total} | "
                        f"Batches: {analysis_state['batch_done']}/{lot_total_display}"
                    )
                else:
                    analysis_metrics.value = "No tracks to analyze."

                if analysis_state["running"]:
                    lot_total = max(analysis_state["batch_total"], 1)
                    active_batch = analysis_state["active_batch"] if analysis_state["active_batch"] > 0 else min(
                        analysis_state["batch_done"] + 1,
                        lot_total,
                    )
                    if analysis_state["paused"]:
                        ai_activity_title.value = "AI paused."
                        ai_activity_title.color = FG_DIM
                        analysis_status.value = (
                            f"Analysis paused - batch {active_batch}/{lot_total}"
                        )
                    else:
                        if analysis_state["current_ids"]:
                            analysis_status.value = f"Analysis running - batch {active_batch}/{lot_total} (AI call running...)"
                        else:
                            analysis_status.value = f"Analysis running - batch {active_batch}/{lot_total}"
                elif analysis_state["cancel_requested"]:
                    ai_activity_title.value = "AI interrupted."
                    ai_activity_title.color = DANGER
                    analysis_status.value = "Analysis canceled."
                elif analysis_state["batch_done"] > 0 and len(analysis_state["processed_ids"]) >= analysis_total > 0:
                    ai_activity_title.value = "AI idle, suggestions ready."
                    ai_activity_title.color = ACCENT
                    analysis_status.value = "Analysis complete. Automatically switching to qualification."
                elif analysis_total == 0:
                    ai_activity_title.value = "Nothing to analyze."
                    ai_activity_title.color = FG_DIM
                    analysis_status.value = "No tracks to analyze."
                else:
                    ai_activity_title.value = "AI waiting."
                    ai_activity_title.color = FG_DIM
                    analysis_status.value = "Ready to analyze."

                if not analysis_state["running"] and not analysis_state["current_ids"] and current_items == 0:
                    current_list.controls.append(ft.Text("• No active batch.", size=11, color=FG_DIM))
                if not analysis_state["processed_ids"]:
                    done_list.controls.append(ft.Text("• No processed tracks yet.", size=11, color=FG_DIM))

                start_button.disabled = analysis_state["running"]
                radio_standard.disabled = force_audit or analysis_state["running"]
                radio_audit.disabled = force_audit or analysis_state["running"]
                if analysis_state["running"]:
                    start_button.text = "Analyzing..."
                elif analysis_total == 0:
                    start_button.text = "Go to qualification"
                elif analysis_state["completed"]:
                    start_button.text = "Restart analysis"
                elif analysis_state["has_run"]:
                    start_button.text = "Analyze again"
                else:
                    start_button.text = "Start analysis"
                pause_button.disabled = not analysis_state["running"]
                pause_button.text = "Resume" if analysis_state["paused"] else "Pause"
                cancel_button.disabled = not analysis_state["running"]
                cancel_button.text = "Canceling..." if analysis_state["cancel_requested"] else "Cancel"
                analysis_activity.visible = analysis_state["running"]

                page.update()

            async def _run_analysis():
                remaining = tracks[resume_index:]
                analysis_state["batch_total"] = (
                    (len(remaining) + PRE_ANALYSIS_BATCH_SIZE - 1) // PRE_ANALYSIS_BATCH_SIZE if remaining else 0
                )
                started_at = time.perf_counter()
                _push_event(
                    f"Pre-analysis started: {analysis_total} tracks to process, {analysis_state['batch_total']} batches.",
                    ACCENT,
                )
                logger.info(
                    "Pre-analysis started (resume_index=%s, remaining=%s, total_batches=%s)",
                    resume_index,
                    len(remaining),
                    analysis_state["batch_total"],
                )

                try:
                    for start in range(resume_index, len(tracks), PRE_ANALYSIS_BATCH_SIZE):
                        current_batch_number = ((start - resume_index) // PRE_ANALYSIS_BATCH_SIZE) + 1

                        while analysis_state["paused"] and not analysis_state["cancel_requested"]:
                            await asyncio.sleep(0.1)

                        if analysis_state["cancel_requested"]:
                            break

                        batch = tracks[start : start + PRE_ANALYSIS_BATCH_SIZE]
                        analysis_state["active_batch"] = current_batch_number
                        analysis_state["current_ids"] = [track.id for track in batch]
                        analysis_state["next_index"] = min(start + PRE_ANALYSIS_BATCH_SIZE, len(tracks))
                        _push_event(
                            f"Batch {current_batch_number}/{max(analysis_state['batch_total'], 1)} in progress ({len(batch)} tracks).",
                            ACCENT,
                        )
                        logger.info(
                            "Batch %s/%s started (size=%s, next_index=%s)",
                            current_batch_number,
                            max(analysis_state["batch_total"], 1),
                            len(batch),
                            analysis_state["next_index"],
                        )
                        _refresh_track_runner()

                        await asyncio.to_thread(classifier.classify_batch, batch)

                        analysis_state["processed_ids"].extend([track.id for track in batch])
                        analysis_state["current_ids"] = []
                        analysis_state["batch_done"] = current_batch_number
                        _push_event(
                            f"Batch {current_batch_number}/{max(analysis_state['batch_total'], 1)} completed "
                            f"({len(analysis_state['processed_ids'])}/{analysis_total} tracks).",
                            RUNNER_DONE_TEXT,
                        )
                        logger.info(
                            "Batch %s/%s completed (processed=%s/%s)",
                            current_batch_number,
                            max(analysis_state["batch_total"], 1),
                            len(analysis_state["processed_ids"]),
                            analysis_total,
                        )
                        _refresh_track_runner()
                except Exception as error:
                    analysis_state["running"] = False
                    analysis_state["completed"] = False
                    _push_event(f"Analysis error: {str(error)[:120]}", DANGER)
                    logger.exception("Pre-analysis failed")
                    analysis_status.value = f"Analysis error: {str(error)[:80]}"
                    page.update()
                    return

                analysis_state["running"] = False
                analysis_state["paused"] = False
                analysis_state["current_ids"] = []
                analysis_state["active_batch"] = 0
                analysis_state["completed"] = (
                    not analysis_state["cancel_requested"]
                    and len(analysis_state["processed_ids"]) >= analysis_total > 0
                )
                if analysis_state["cancel_requested"]:
                    _push_event("Pre-analysis canceled by user.", DANGER)
                elif analysis_state["completed"]:
                    _push_event(
                        f"Pre-analysis completed in {time.perf_counter() - started_at:.1f}s.",
                        RUNNER_DONE_TEXT,
                    )
                logger.info(
                    "Pre-analysis finished (completed=%s, processed=%s/%s, duration=%.1fs)",
                    analysis_state["completed"],
                    len(analysis_state["processed_ids"]),
                    analysis_total,
                    time.perf_counter() - started_at,
                )
                _refresh_track_runner()
                if analysis_state["completed"]:
                    _push_event("Opening qualification automatically...", ACCENT)
                    await asyncio.sleep(0.35)
                    start_session((session_mode.value or "audit") == "audit")

            def on_start_analysis(_):
                if analysis_state["running"]:
                    return
                if analysis_total == 0:
                    _push_event("No tracks to pre-analyze, opening qualification.", FG_DIM)
                    start_session((session_mode.value or "audit") == "audit")
                    return
                logger.info("Start analysis clicked")
                _push_event("Start requested by user.", ACCENT)
                analysis_state["running"] = True
                analysis_state["paused"] = False
                analysis_state["cancel_requested"] = False
                analysis_state["processed_ids"] = []
                analysis_state["current_ids"] = []
                analysis_state["next_index"] = resume_index
                analysis_state["batch_done"] = 0
                analysis_state["active_batch"] = 0
                analysis_state["has_run"] = True
                analysis_state["completed"] = False
                analysis_state["batch_total"] = (
                    (analysis_total + PRE_ANALYSIS_BATCH_SIZE - 1) // PRE_ANALYSIS_BATCH_SIZE if analysis_total else 0
                )
                _refresh_track_runner()
                page.run_task(_animate_ai_title)
                page.run_task(_run_analysis)

            def on_pause_analysis(_):
                if not analysis_state["running"]:
                    return
                analysis_state["paused"] = not analysis_state["paused"]
                _push_event("Analysis paused." if analysis_state["paused"] else "Analysis resumed.", FG_DIM)
                logger.info("Analysis pause toggled (paused=%s)", analysis_state["paused"])
                _refresh_track_runner()
                if not analysis_state["paused"]:
                    page.run_task(_animate_ai_title)

            def on_cancel_analysis(_):
                if not analysis_state["running"]:
                    return
                analysis_state["cancel_requested"] = True
                analysis_state["paused"] = False
                _push_event("Cancellation requested. Current batch will finish, then stop.", DANGER)
                logger.info("Analysis cancellation requested")
                _refresh_track_runner()

            def on_modify_configuration(_):
                setup_activity.visible = True
                page.update()
                start_setup_wizard(0)

            def on_disconnect(_):
                disconnect_activity.visible = True
                page.update()

                def confirm_yes(__):
                    dialog.open = False
                    page.update()
                    config.save(
                        {
                            "spotify_client_id": "",
                            "spotify_client_secret": "",
                            "spotify_redirect_uri": "http://127.0.0.1:8888/callback",
                            "llm_provider": "openai",
                            "llm_api_key": "",
                            "llm_model": "",
                            "simulation_mode": False,
                            "legal_acknowledged": False,
                        }
                    )
                    try:
                        os.remove(config.path)
                    except OSError:
                        pass
                    clear_cache(include_progress=True)
                    disconnect_activity.visible = False
                    show_legal_gate()

                def confirm_no(__):
                    dialog.open = False
                    disconnect_activity.visible = False
                    page.update()

                dialog = ft.AlertDialog(
                    title=ft.Text("Disconnect"),
                    content=ft.Text("Remove local configuration and restart onboarding?"),
                    actions=[
                        ft.TextButton("Cancel", on_click=confirm_no),
                        ft.TextButton("Confirm", on_click=confirm_yes, style=ft.ButtonStyle(color=DANGER)),
                    ],
                )
                page.overlay.append(dialog)
                dialog.open = True
                page.update()

            start_button.on_click = on_start_analysis
            pause_button.on_click = on_pause_analysis
            cancel_button.on_click = on_cancel_analysis

            modify_config_button = ft.ElevatedButton(
                "Edit configuration",
                on_click=on_modify_configuration,
                bgcolor=BG_INPUT,
                color=FG,
            )
            disconnect_button = ft.ElevatedButton(
                "Disconnect",
                on_click=on_disconnect,
                bgcolor=BG_INPUT,
                color=DANGER,
            )

            def _lane_container(title: str, title_color: str, bg_color: str, border_color: str, content: ft.Control, width: int, height: int):
                return ft.Container(
                    width=width,
                    height=height,
                    bgcolor=bg_color,
                    border=ft.border.all(1 if title_color != ACCENT else 2, border_color),
                    border_radius=8,
                    padding=10,
                    content=ft.Column(
                        [
                            ft.Text(title, size=12, color=title_color, weight=ft.FontWeight.BOLD),
                            content,
                        ],
                        spacing=4,
                        expand=True,
                    ),
                )

            def _build_launcher_content() -> list[ft.Control]:
                window_width = int(getattr(page.window, "width", 0) or 980)
                compact = window_width < 980
                content_width = max(min(window_width - 48, 1080), 320)
                logo_size = 196 if compact else READY_LOGO_SIZE
                logo_block_width = content_width if compact else max(260, int(content_width * 0.30))
                connection_width = content_width if compact else max(360, content_width - logo_block_width - 12)
                lane_width = content_width if compact else max(210, int((content_width - 16) / 3))
                lane_height = 200 if compact else 220

                account_controls: list[ft.Control] = [
                    ft.Text("Spotify: connected", size=12, color=FG),
                    ft.Text(f"Account: {user['display_name']}", size=12, color=FG_DIM),
                    ft.Text(f"AI provider: {provider.upper()}", size=12, color=FG_DIM),
                    ft.Row(
                        [
                            modify_config_button,
                            setup_activity,
                            disconnect_button,
                            disconnect_activity,
                        ],
                        spacing=10,
                        wrap=True,
                    ),
                ]

                mode_controls: list[ft.Control] = [
                    ai_activity_title,
                    ft.Text(f"{len(tracks)} liked tracks loaded", size=12, color=FG),
                    ft.Text(f"Resume position: {resume_index + 1}/{len(tracks)}", size=11, color=FG_DIM),
                    session_mode,
                    ft.Text(
                        "AI pre-analysis: computes read-only suggestions. "
                        "Then automatically opens qualification so you can apply your decisions.",
                        size=11,
                        color=FG_DIM,
                    ),
                ]
                if forced_msg:
                    mode_controls.append(forced_msg)
                mode_controls.append(last_event_label)
                mode_controls.append(
                    ft.Row(
                        [
                            start_button,
                            pause_button,
                            cancel_button,
                            analysis_activity,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=8,
                        wrap=True,
                    )
                )

                if compact:
                    top_block: ft.Control = ft.Column(
                        [
                            ft.Container(
                                width=content_width,
                                alignment=ft.Alignment(0, 0),
                                content=build_logo(logo_size),
                            ),
                            build_section("Connection status", account_controls, width=content_width),
                        ],
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                    lanes_block: ft.Control = ft.Column(
                        [
                            _lane_container("Upcoming batch", RUNNER_UPCOMING_TEXT, RUNNER_UPCOMING_BG, "#2F3D55", upcoming_list, lane_width, lane_height),
                            _lane_container("Current batch", ACCENT, RUNNER_CURRENT_BG, ACCENT, current_list, lane_width, lane_height),
                            _lane_container("Analyzed tracks", RUNNER_DONE_TEXT, RUNNER_DONE_BG, "#2C7A53", done_list, lane_width, lane_height),
                        ],
                        spacing=8,
                    )
                else:
                    top_block = ft.Row(
                        [
                            ft.Container(
                                width=logo_block_width,
                                alignment=ft.Alignment(0, 0),
                                content=build_logo(logo_size),
                            ),
                            build_section("Connection status", account_controls, width=connection_width),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                        wrap=False,
                    )
                    lanes_block = ft.Row(
                        [
                            _lane_container("Upcoming batch", RUNNER_UPCOMING_TEXT, RUNNER_UPCOMING_BG, "#2F3D55", upcoming_list, lane_width, lane_height),
                            _lane_container("Current batch", ACCENT, RUNNER_CURRENT_BG, ACCENT, current_list, lane_width, lane_height),
                            _lane_container("Analyzed tracks", RUNNER_DONE_TEXT, RUNNER_DONE_BG, "#2C7A53", done_list, lane_width, lane_height),
                        ],
                        spacing=8,
                        wrap=False,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    )

                return [
                    build_workflow_header(
                        page=page,
                        current_step=1,
                        subtitle="Step 1/2 - Pre-analysis of liked tracks",
                        width=float("inf"),
                        mode_label="Audit" if (session_mode.value or "standard") == "audit" else "Standard",
                        step_labels=["Pre-analysis", "Qualification"],
                    ),
                    top_block,
                    build_section("AI Workshop", mode_controls, accent=True, width=content_width),
                    build_section(
                        "Track progress",
                        [
                            analysis_progress,
                            analysis_status,
                            analysis_metrics,
                            lanes_block,
                            ft.Container(
                                bgcolor=BG_INPUT,
                                border=ft.border.all(1, BORDER),
                                border_radius=8,
                                height=170 if compact else 190,
                                padding=10,
                                content=ft.Column(
                                    [
                                        ft.Text("AI analysis events", size=12, color=FG, weight=ft.FontWeight.BOLD),
                                        analysis_events,
                                    ],
                                    spacing=6,
                                ),
                            ),
                        ],
                        width=content_width,
                    ),
                ]

            page.controls.clear()
            launcher_column = ft.Column(
                _build_launcher_content(),
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.START,
            )

            page.add(
                ft.Container(
                    content=launcher_column,
                    expand=True,
                    padding=ft.padding.symmetric(vertical=16),
                    alignment=ft.Alignment(0, -1),
                )
            )

            def on_launcher_resized(_e: ft.ControlEvent):
                launcher_column.controls = _build_launcher_content()
                page.update()

            session_mode.on_change = on_launcher_resized
            page.on_resized = on_launcher_resized
            _push_event("Pre-analysis is ready. Start analysis to see live events.", FG_DIM)
            _refresh_track_runner()

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

        cfg = config.load()
        if not bool(cfg.get("legal_acknowledged", False)):
            show_legal_gate()
        elif not config.is_configured():
            from src.ui.setup_view import SetupView
            setup = SetupView(
                page=page,
                config=config,
                on_complete=launch_classification,
                on_cancel=show_legal_gate,
            )
            setup.expand = True
            page.add(setup)
        else:
            launch_classification()

    ft.app(target=main)
