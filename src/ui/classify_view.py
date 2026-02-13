"""Flet-based classification view with queue and action-focused UX."""

import threading
from typing import Callable

import flet as ft

from src.domain.model import ClassificationSession, Decision, Theme, Track
from src.domain.ports import ClassifierPort, PlaylistPort, ProgressPort
from src.ui.legal import LEGAL_DISCLAIMER_FULL
from src.ui.theme import ACCENT, BG, BG_CARD, BG_INPUT, BORDER, DANGER, FG, FG_DIM
from src.ui.workflow_header import build_workflow_header
from src.usecases.classify_track import ClassifyTrackUseCase
from src.usecases.export_session import ExportSessionUseCase
from src.usecases.resume_session import ResumeSessionUseCase
from src.usecases.undo_decision import UndoDecisionUseCase

DEFAULT_WINDOW_PAST = 3
DEFAULT_WINDOW_FUTURE = 3
PRELOAD_LOOKAHEAD = 20
PRELOAD_BATCH_SIZE = 10


class ClassifyView(ft.Column):
    """Main classification interface."""

    def __init__(
        self,
        page: ft.Page,
        tracks: list[Track],
        themes: dict[str, Theme],
        classifier: ClassifierPort,
        playlist: PlaylistPort,
        progress: ProgressPort,
        simulation_mode: bool = False,
        on_back_to_step2: Callable[[], None] | None = None,
    ):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0)
        self._page = page
        self.bgcolor = BG
        self.tracks = tracks
        self.themes = themes
        self.simulation_mode = simulation_mode
        self.on_back_to_step2 = on_back_to_step2

        self.is_compact_layout = False
        self.window_past = DEFAULT_WINDOW_PAST
        self.window_future = DEFAULT_WINDOW_FUTURE
        self.cover_size = 180
        self._apply_layout_flags()

        # Use cases
        self.classify_uc = ClassifyTrackUseCase(classifier, playlist, progress)
        self.undo_uc = UndoDecisionUseCase(playlist, progress)
        self.export_uc = ExportSessionUseCase(progress)
        resume_uc = ResumeSessionUseCase(progress)
        self.session: ClassificationSession = resume_uc.execute(tracks)
        self.classifier = classifier

        self._analysis_job_id = 0
        self._analysis_track_ids: list[str] = []
        self._analysis_running = False
        self._analysis_error = ""

        # UI state refs
        self.progress_bar = ft.ProgressBar(value=0, bgcolor=BG_INPUT, color=ACCENT, width=float("inf"))
        self.progress_label = ft.Text("", size=12, color=FG)
        self.stats_label = ft.Text("", size=11, color=FG_DIM)
        self.analysis_label = ft.Text("", size=11, color=FG_DIM)
        self.workflow_context_label = ft.Text("", size=11, color=FG_DIM)
        destination_names = ", ".join(theme.name for theme in self.themes.values())
        self.ux_help_label = ft.Text(
            f"{destination_names} are destination playlists. "
            "[S] keeps this track unclassified. [<-] undoes the previous decision.",
            size=11,
            color=FG_DIM,
            text_align=ft.TextAlign.CENTER,
        )
        self.current_position = ft.Text("", size=11, color=FG_DIM, text_align=ft.TextAlign.CENTER)
        self.current_cover = ft.Image(
            src="",
            width=self.cover_size,
            height=self.cover_size,
            border_radius=8,
            visible=False,
        )
        self.current_cover_placeholder = ft.Text("No cover image", size=11, color=FG_DIM, visible=True)
        self.current_title_switcher = ft.AnimatedSwitcher(
            content=ft.Text("", size=20, weight=ft.FontWeight.BOLD, color=FG, text_align=ft.TextAlign.CENTER),
            duration=220,
            transition=ft.AnimatedSwitcherTransition.SCALE,
        )
        self.current_artist_switcher = ft.AnimatedSwitcher(
            content=ft.Text("", size=14, color=FG_DIM, text_align=ft.TextAlign.CENTER),
            duration=180,
            transition=ft.AnimatedSwitcherTransition.FADE,
        )
        self.current_context = ft.Text("", size=11, color=FG_DIM, text_align=ft.TextAlign.CENTER)
        self.suggestion_label = ft.Text("", size=13, color=ACCENT, italic=True, text_align=ft.TextAlign.CENTER)

        self.past_labels: list[ft.Text] = []
        self.future_labels: list[ft.Text] = []
        self._sync_window_labels()

        self.snack = ft.SnackBar(content=ft.Text(""))

        self._build_ui()
        self._refresh_display()
        self._preload_llm()

    def _build_ui(self):
        header = ft.Container(
            content=build_workflow_header(
                page=self._page,
                current_step=2,
                subtitle="Step 2/2 - Track qualification",
                width=float("inf"),
                mode_label="Audit" if self.simulation_mode else "Standard",
                step_labels=["Pre-analysis", "Qualification"],
            ),
            width=float("inf"),
            padding=ft.padding.only(top=8, bottom=8),
        )

        context_controls: list[ft.Control] = [
            self.workflow_context_label,
            ft.Container(expand=True),
        ]
        if self.simulation_mode:
            context_controls.append(ft.Text("Audit mode: no Spotify write operations", size=11, color=FG_DIM))
        if self.on_back_to_step2:
            context_controls.append(
                ft.TextButton(
                    "Back to pre-analysis",
                    on_click=lambda _: self.on_back_to_step2(),
                    style=ft.ButtonStyle(color=FG_DIM),
                )
            )

        context_row = ft.Container(
            content=ft.Row(context_controls, alignment=ft.MainAxisAlignment.START, wrap=True),
            padding=ft.padding.symmetric(horizontal=20, vertical=2),
        )

        progress_row = ft.Container(
            content=ft.Column(
                [self.progress_bar, self.progress_label, self.stats_label, self.analysis_label],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=8),
        )

        side_width = None if self.is_compact_layout else 210
        center_expand = not self.is_compact_layout

        left_panel = ft.Container(
            width=side_width,
            expand=1 if self.is_compact_layout else None,
            bgcolor=BG_CARD,
            border=ft.border.all(1, BORDER),
            border_radius=8,
            padding=10,
            content=ft.Column(
                [
                    ft.Text("<- Already processed", size=12, color=FG_DIM, weight=ft.FontWeight.BOLD),
                    ft.Text("Previous decisions", size=10, color=FG_DIM),
                    ft.Container(height=4),
                    *self.past_labels,
                ],
                spacing=3,
            ),
        )

        center_panel = ft.Container(
            width=None if self.is_compact_layout else 440,
            expand=1 if center_expand else None,
            bgcolor=BG_CARD,
            border=ft.border.all(2, ACCENT),
            border_radius=8,
            padding=16,
            content=ft.Column(
                [
                    ft.Text("Current track to classify", size=14, color=ACCENT, weight=ft.FontWeight.BOLD),
                    ft.Text("Choose where this track should be stored.", size=11, color=FG_DIM),
                    self.current_position,
                    ft.Container(height=6),
                    self.current_cover,
                    self.current_cover_placeholder,
                    self.current_title_switcher,
                    self.current_artist_switcher,
                    self.current_context,
                    ft.Container(height=4),
                    self.suggestion_label,
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        right_panel = ft.Container(
            width=side_width,
            expand=1 if self.is_compact_layout else None,
            bgcolor=BG_CARD,
            border=ft.border.all(1, BORDER),
            border_radius=8,
            padding=10,
            content=ft.Column(
                [
                    ft.Text("Coming next ->", size=12, color=FG_DIM, weight=ft.FontWeight.BOLD),
                    ft.Text("Upcoming queue", size=10, color=FG_DIM),
                    ft.Container(height=4),
                    *self.future_labels,
                ],
                spacing=3,
            ),
        )

        if self.is_compact_layout:
            lanes_content: ft.Control = ft.Column(
                [
                    center_panel,
                    ft.Row([left_panel, right_panel], spacing=8, wrap=True),
                ],
                spacing=8,
            )
        else:
            lanes_content = ft.Row(
                [left_panel, center_panel, right_panel],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )

        lanes_section = ft.Container(
            content=lanes_content,
            padding=ft.padding.symmetric(horizontal=16, vertical=6),
        )

        destination_cards = [self._build_destination_card(key, theme) for key, theme in self.themes.items()]
        actions_section = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Decision actions", size=14, weight=ft.FontWeight.BOLD, color=FG),
                    ft.Text(
                        "Each card below writes this track to a destination playlist on Spotify.",
                        size=11,
                        color=FG_DIM,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Row(destination_cards, alignment=ft.MainAxisAlignment.CENTER, spacing=10, wrap=True),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Skip for now [S]",
                                on_click=lambda _: self._skip(),
                                bgcolor=BG_INPUT,
                                color=FG,
                            ),
                            ft.ElevatedButton(
                                "Undo last decision [<-]",
                                on_click=lambda _: self._undo(),
                                bgcolor=BG_INPUT,
                                color=FG,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=8,
                        wrap=True,
                    ),
                    self.ux_help_label,
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=8),
        )

        bottom_row = ft.Container(
            content=ft.Row(
                [
                    ft.TextButton("Pause & Save", on_click=lambda _: self._pause(), style=ft.ButtonStyle(color=FG_DIM)),
                    ft.TextButton("Stop & Clear", on_click=lambda _: self._stop(), style=ft.ButtonStyle(color=DANGER)),
                    ft.TextButton("Disclaimer", on_click=lambda _: self._show_disclaimer(), style=ft.ButtonStyle(color=FG_DIM)),
                    ft.Container(expand=True),
                    ft.TextButton("Export CSV", on_click=lambda _: self._export(), style=ft.ButtonStyle(color=FG_DIM)),
                ],
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=8),
        )

        self.controls = [
            header,
            context_row,
            progress_row,
            lanes_section,
            actions_section,
            bottom_row,
            self.snack,
        ]

    def _refresh_display(self):
        total = len(self.tracks)
        idx = self.session.current_index
        decided = self.session.decided_count

        self.progress_bar.value = decided / total if total > 0 else 0
        percent = int((decided / total) * 100) if total > 0 else 0
        self.progress_label.value = f"Progress: {decided}/{total} tracks ({percent}%)"
        self.workflow_context_label.value = f"Qualification: {decided}/{total} | Pending validation: {max(total - decided, 0)}"
        self.stats_label.value = self._build_stats_label()
        self._refresh_analysis_status()

        if idx >= total:
            self._finish()
            return

        for i, lbl in enumerate(self.past_labels):
            past_idx = idx - self.window_past + i
            if 0 <= past_idx < total:
                past_track = self.tracks[past_idx]
                decision = self.session.decision_for(past_track.id)
                tag = self._decision_tag(decision)
                lbl.value = f"{past_track.artist} - {past_track.name} {tag}".strip()
            else:
                lbl.value = ""

        track = self.tracks[idx]
        self.current_position.value = f"Track {idx + 1} of {total}"
        self.current_title_switcher.content = ft.Text(
            track.name,
            size=20,
            weight=ft.FontWeight.BOLD,
            color=FG,
            text_align=ft.TextAlign.CENTER,
            key=f"title-{track.id}-{idx}",
        )
        self.current_artist_switcher.content = ft.Text(
            f"{track.artist} - {track.album}",
            size=14,
            color=FG_DIM,
            text_align=ft.TextAlign.CENTER,
            key=f"artist-{track.id}-{idx}",
        )
        self.current_context.value = self._build_track_context(track)

        if track.album_image_url:
            self.current_cover.src = track.album_image_url
            self.current_cover.visible = True
            self.current_cover_placeholder.visible = False
        else:
            self.current_cover.visible = False
            self.current_cover_placeholder.visible = True

        suggestions = self.classifier.get_suggestions(track.id)
        if suggestions:
            best = max(suggestions, key=lambda suggestion: suggestion.confidence)
            theme = self.themes.get(best.theme_key)
            theme_name = theme.name if theme else best.theme_key
            reasoning = best.reasoning.strip()
            if len(reasoning) > 90:
                reasoning = f"{reasoning[:87]}..."
            self.suggestion_label.value = f"AI recommendation: {theme_name} ({best.confidence:.0%}) - {reasoning}"
        else:
            self.suggestion_label.value = "AI recommendation: analyzing this track..."

        for i, lbl in enumerate(self.future_labels):
            future_idx = idx + 1 + i
            if future_idx < total:
                future_track = self.tracks[future_idx]
                lbl.value = f"{future_track.artist} - {future_track.name}"
            else:
                lbl.value = ""

    def handle_keyboard(self, e: ft.KeyboardEvent):
        for theme_key, theme in self.themes.items():
            if e.key == theme.shortcut:
                self._decide(theme_key)
                return

        if e.key.lower() == "s":
            self._skip()
        elif e.key == "Arrow Left":
            self._undo()
        elif e.key == "Escape":
            self._pause()

    def handle_resize(self, _e: ft.ControlEvent):
        previous_state = (self.is_compact_layout, self.window_past, self.window_future, self.cover_size)
        self._apply_layout_flags()
        self._sync_window_labels()
        current_state = (self.is_compact_layout, self.window_past, self.window_future, self.cover_size)
        if current_state != previous_state:
            self._build_ui()
            self._refresh_display()
            self.update()

    # Actions

    def _decide(self, theme_key: str):
        if self.session.current_index >= len(self.tracks):
            return
        track = self.tracks[self.session.current_index]
        self.classify_uc.execute(self.session, track, theme_key)
        self._refresh_display()
        self._preload_llm()
        self.update()

    def _skip(self):
        if self.session.current_index >= len(self.tracks):
            return
        track = self.tracks[self.session.current_index]
        self.classify_uc.skip(self.session, track)
        self._refresh_display()
        self._preload_llm()
        self.update()

    def _undo(self):
        self.undo_uc.execute(self.session)
        self._refresh_display()
        self._preload_llm()
        self.update()

    def _pause(self):
        self._show_snack("Progress saved. You can resume later.")
        self._page.window.close()

    def _stop(self):
        def confirm_yes(_):
            progress = self.classify_uc.progress
            progress.clear()
            dialog.open = False
            self._page.update()
            self._page.window.close()

        def confirm_no(_):
            dialog.open = False
            self._page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Stop & Clear"),
            content=ft.Text("This will delete all progress. Continue?"),
            actions=[
                ft.TextButton("Cancel", on_click=confirm_no),
                ft.TextButton("Delete", on_click=confirm_yes, style=ft.ButtonStyle(color=DANGER)),
            ],
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    def _export(self):
        path = self.export_uc.execute(self.session)
        self._show_snack(f"CSV exported to {path}")

    def _show_disclaimer(self):
        def close_dialog(_):
            dialog.open = False
            self._page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Disclaimer"),
            content=ft.Text(LEGAL_DISCLAIMER_FULL),
            actions=[ft.TextButton("Close", on_click=close_dialog)],
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    def _finish(self):
        path = self.export_uc.execute(self.session)
        self._show_snack(f"All {len(self.tracks)} tracks classified! Exported to {path}")

    # Helpers

    def _apply_layout_flags(self) -> None:
        width = int(getattr(self._page.window, "width", 0) or 0)
        height = int(getattr(self._page.window, "height", 0) or 0)
        is_compact = (width > 0 and width < 980) or (height > 0 and height < 780)

        self.is_compact_layout = is_compact
        self.window_past = 2 if is_compact else DEFAULT_WINDOW_PAST
        self.window_future = 2 if is_compact else DEFAULT_WINDOW_FUTURE
        self.cover_size = 132 if is_compact else 180
        if hasattr(self, "current_cover"):
            self.current_cover.width = self.cover_size
            self.current_cover.height = self.cover_size

    def _sync_window_labels(self) -> None:
        while len(self.past_labels) < self.window_past:
            self.past_labels.append(ft.Text("", size=12, color=FG_DIM))
        while len(self.past_labels) > self.window_past:
            self.past_labels.pop(0)

        while len(self.future_labels) < self.window_future:
            self.future_labels.append(ft.Text("", size=12, color=FG_DIM))
        while len(self.future_labels) > self.window_future:
            self.future_labels.pop()

    def _build_destination_card(self, theme_key: str, theme: Theme) -> ft.Container:
        return ft.Container(
            width=300 if not self.is_compact_layout else None,
            bgcolor=BG_CARD,
            border=ft.border.all(1, BORDER),
            border_radius=8,
            padding=12,
            content=ft.Column(
                [
                    ft.Text(theme.name, size=14, weight=ft.FontWeight.BOLD, color=FG),
                    ft.Text(theme.description, size=11, color=FG_DIM),
                    ft.Text(
                        f"Writes the current track into playlist: {theme.name}",
                        size=10,
                        color=FG_DIM,
                    ),
                    ft.ElevatedButton(
                        f"Classify here [{theme.shortcut}]",
                        on_click=lambda _, selected_theme=theme_key: self._decide(selected_theme),
                        bgcolor=ACCENT,
                        color="white",
                    ),
                ],
                spacing=6,
            ),
        )

    def _build_stats_label(self) -> str:
        theme_counts = {theme_key: 0 for theme_key in self.themes}
        skipped = 0
        for decision in self.session.decisions:
            if decision.skipped:
                skipped += 1
                continue
            for theme_key in decision.themes:
                if theme_key in theme_counts:
                    theme_counts[theme_key] += 1

        parts = [f"{self.themes[theme_key].name}: {count}" for theme_key, count in theme_counts.items()]
        return "Distribution: " + " | ".join(parts + [f"Skipped: {skipped}"])

    def _refresh_analysis_status(self) -> None:
        if not self._analysis_track_ids:
            self.analysis_label.value = "AI preload: idle"
            return

        done = 0
        for track_id in self._analysis_track_ids:
            if self.classifier.get_suggestions(track_id):
                done += 1

        total = len(self._analysis_track_ids)
        if self._analysis_error:
            self.analysis_label.value = f"AI preload: {done}/{total} (partial, {self._analysis_error})"
            return

        state = "running" if self._analysis_running else "ready"
        self.analysis_label.value = f"AI preload: {done}/{total} ({state})"

    def _preload_llm(self):
        self._analysis_job_id += 1
        job_id = self._analysis_job_id
        start = self.session.current_index
        end = min(start + PRELOAD_LOOKAHEAD, len(self.tracks))
        batch = self.tracks[start:end]
        self._analysis_track_ids = [track.id for track in batch]
        self._analysis_running = True
        self._analysis_error = ""
        self._refresh_analysis_status()

        def _run():
            for i in range(0, len(batch), PRELOAD_BATCH_SIZE):
                if job_id != self._analysis_job_id:
                    return
                chunk = batch[i : i + PRELOAD_BATCH_SIZE]
                try:
                    self.classifier.classify_batch(chunk)
                except Exception as error:
                    if job_id != self._analysis_job_id:
                        return
                    self._analysis_error = str(error)[:80]
                    break

                self._refresh_analysis_status()
                if self._page:
                    self._page.update()

            if job_id != self._analysis_job_id:
                return
            self._analysis_running = False
            self._refresh_analysis_status()
            if self._page:
                self._page.update()

        threading.Thread(target=_run, daemon=True).start()

    def _build_track_context(self, track: Track) -> str:
        parts = []
        if track.release_date:
            parts.append(f"Release: {track.release_date}")
        if track.duration_ms > 0:
            parts.append(f"Duration: {self._format_duration(track.duration_ms)}")
        if track.popularity is not None:
            parts.append(f"Popularity: {track.popularity}/100")
        parts.append("Explicit" if track.explicit else "Clean")
        return " | ".join(parts)

    @staticmethod
    def _format_duration(duration_ms: int) -> str:
        total_seconds = max(duration_ms, 0) // 1000
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes}:{seconds:02d}"

    def _decision_tag(self, decision: Decision | None) -> str:
        if not decision:
            return ""
        if decision.skipped:
            return "[skipped]"
        names = [self.themes[theme_key].name for theme_key in decision.themes if theme_key in self.themes]
        return f"[{', '.join(names)}]" if names else ""

    def _show_snack(self, msg: str):
        self.snack.content = ft.Text(msg)
        self.snack.open = True
        self._page.update()
