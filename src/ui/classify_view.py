"""Flet-based classification view — sliding window UI."""

import threading

import flet as ft

from src.domain.model import ClassificationSession, Decision, Suggestion, Theme, Track
from src.domain.ports import ClassifierPort, PlaylistPort, ProgressPort
from src.ui.theme import ACCENT, BG, BG_CARD, BG_INPUT, BORDER, DANGER, FG, FG_DIM
from src.usecases.classify_track import ClassifyTrackUseCase
from src.usecases.export_session import ExportSessionUseCase
from src.usecases.resume_session import ResumeSessionUseCase
from src.usecases.undo_decision import UndoDecisionUseCase

WINDOW_PAST = 3
WINDOW_FUTURE = 3


class ClassifyView(ft.Column):
    """Main classification interface with sliding window."""

    def __init__(
        self,
        page: ft.Page,
        tracks: list[Track],
        themes: dict[str, Theme],
        classifier: ClassifierPort,
        playlist: PlaylistPort,
        progress: ProgressPort,
    ):
        super().__init__(expand=True)
        self.page = page
        self.tracks = tracks
        self.themes = themes

        # Use cases
        self.classify_uc = ClassifyTrackUseCase(classifier, playlist, progress)
        self.undo_uc = UndoDecisionUseCase(playlist, progress)
        self.export_uc = ExportSessionUseCase(progress)
        resume_uc = ResumeSessionUseCase(progress)
        self.session: ClassificationSession = resume_uc.execute(tracks)
        self.classifier = classifier

        # UI state refs
        self.progress_bar = ft.ProgressBar(value=0, bgcolor=BG_INPUT, color=ACCENT, width=float("inf"))
        self.progress_label = ft.Text("", size=12, color=FG)
        self.past_labels: list[ft.Text] = [ft.Text("", size=12, color=FG_DIM) for _ in range(WINDOW_PAST)]
        self.current_title = ft.Text("", size=20, weight=ft.FontWeight.BOLD, color=FG)
        self.current_artist = ft.Text("", size=14, color=FG_DIM)
        self.suggestion_label = ft.Text("", size=13, color=ACCENT, italic=True)
        self.future_labels: list[ft.Text] = [ft.Text("", size=12, color=FG_DIM) for _ in range(WINDOW_FUTURE)]
        self.snack = ft.SnackBar(content=ft.Text(""))

        self._build_ui()
        self._refresh_display()
        self._preload_llm()

    def _build_ui(self):
        # Header
        header = ft.Container(
            content=ft.Text("Tidy ur Spotify", size=20, weight=ft.FontWeight.BOLD, color="white"),
            bgcolor=ACCENT,
            padding=ft.padding.symmetric(vertical=12, horizontal=20),
            alignment=ft.alignment.center,
        )

        # Progress
        progress_row = ft.Container(
            content=ft.Column([self.progress_bar, self.progress_label], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=20, vertical=8),
        )

        # Past tracks
        past_section = ft.Container(
            content=ft.Column(
                [ft.Text("Previous", size=12, color=FG_DIM, weight=ft.FontWeight.BOLD)] + self.past_labels,
                spacing=4,
            ),
            bgcolor=BG_CARD,
            border=ft.border.all(1, BORDER),
            border_radius=8,
            padding=12,
            margin=ft.margin.symmetric(horizontal=20),
        )

        # Current track
        current_section = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Now Playing", size=13, color=ACCENT, weight=ft.FontWeight.BOLD),
                    self.current_title,
                    self.current_artist,
                    ft.Container(height=4),
                    self.suggestion_label,
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=BG_CARD,
            border=ft.border.all(2, ACCENT),
            border_radius=8,
            padding=20,
            margin=ft.margin.symmetric(horizontal=20, vertical=8),
        )

        # Future tracks
        future_section = ft.Container(
            content=ft.Column(
                [ft.Text("Coming Up", size=12, color=FG_DIM, weight=ft.FontWeight.BOLD)] + self.future_labels,
                spacing=4,
            ),
            bgcolor=BG_CARD,
            border=ft.border.all(1, BORDER),
            border_radius=8,
            padding=12,
            margin=ft.margin.symmetric(horizontal=20),
        )

        # Theme buttons
        theme_buttons = []
        for key, theme in self.themes.items():
            theme_buttons.append(
                ft.ElevatedButton(
                    f"[{theme.shortcut}] {theme.name}",
                    on_click=lambda _, k=key: self._decide(k),
                    bgcolor=ACCENT,
                    color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                    width=160,
                )
            )

        theme_buttons.append(
            ft.ElevatedButton(
                "[S] Skip",
                on_click=lambda _: self._skip(),
                bgcolor=BG_INPUT,
                color=FG,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                width=100,
            )
        )
        theme_buttons.append(
            ft.ElevatedButton(
                "[\u2190] Undo",
                on_click=lambda _: self._undo(),
                bgcolor=BG_INPUT,
                color=FG,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                width=100,
            )
        )

        buttons_row = ft.Container(
            content=ft.Row(theme_buttons, alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
        )

        # Bottom actions
        bottom_row = ft.Container(
            content=ft.Row(
                [
                    ft.TextButton("Pause & Save", on_click=lambda _: self._pause(), style=ft.ButtonStyle(color=FG_DIM)),
                    ft.TextButton("Stop & Clear", on_click=lambda _: self._stop(), style=ft.ButtonStyle(color=DANGER)),
                    ft.Container(expand=True),
                    ft.TextButton("Export CSV", on_click=lambda _: self._export(), style=ft.ButtonStyle(color=FG_DIM)),
                ],
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=8),
        )

        self.controls = [
            header,
            progress_row,
            past_section,
            current_section,
            future_section,
            buttons_row,
            ft.Container(expand=True),
            bottom_row,
            self.snack,
        ]

    def _refresh_display(self):
        total = len(self.tracks)
        idx = self.session.current_index
        decided = self.session.decided_count

        self.progress_bar.value = decided / total if total > 0 else 0
        self.progress_label.value = f"{decided} / {total} tracks classified"

        if idx >= total:
            self._finish()
            return

        # Past tracks
        for i, lbl in enumerate(self.past_labels):
            past_idx = idx - WINDOW_PAST + i
            if 0 <= past_idx < total:
                t = self.tracks[past_idx]
                decision = self.session.decision_for(t.id)
                tag = self._decision_tag(decision)
                lbl.value = f"  {t.artist} \u2014 {t.name} {tag}"
            else:
                lbl.value = ""

        # Current track
        track = self.tracks[idx]
        self.current_title.value = track.name
        self.current_artist.value = f"{track.artist}  \u2022  {track.album}"

        # AI suggestion
        suggestions = self.classifier.get_suggestions(track.id)
        if suggestions:
            best = max(suggestions, key=lambda s: s.confidence)
            theme = self.themes.get(best.theme_key)
            theme_name = theme.name if theme else best.theme_key
            self.suggestion_label.value = f"AI suggests: {theme_name} ({best.confidence:.0%}) \u2014 {best.reasoning}"
        else:
            self.suggestion_label.value = "AI: analyzing..."

        # Future tracks
        for i, lbl in enumerate(self.future_labels):
            fut_idx = idx + 1 + i
            if fut_idx < total:
                t = self.tracks[fut_idx]
                lbl.value = f"  {t.artist} \u2014 {t.name}"
            else:
                lbl.value = ""

    def handle_keyboard(self, e: ft.KeyboardEvent):
        if e.key == "1":
            self._decide("ambiance")
        elif e.key == "2":
            self._decide("lets_dance")
        elif e.key.lower() == "s":
            self._skip()
        elif e.key == "Arrow Left":
            self._undo()
        elif e.key == "Escape":
            self._pause()

    # ── Actions ─────────────────────────────────────────────────────

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
        self.update()

    def _undo(self):
        self.undo_uc.execute(self.session)
        self._refresh_display()
        self.update()

    def _pause(self):
        self._show_snack("Progress saved. You can resume later.")
        self.page.window.close()

    def _stop(self):
        def confirm_yes(_):
            from src.adapters.progress.json_progress_adapter import JsonProgressAdapter
            progress = self.classify_uc.progress
            progress.clear()
            dialog.open = False
            self.page.update()
            self.page.window.close()

        def confirm_no(_):
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Stop & Clear"),
            content=ft.Text("This will delete all progress. Continue?"),
            actions=[
                ft.TextButton("Cancel", on_click=confirm_no),
                ft.TextButton("Delete", on_click=confirm_yes, style=ft.ButtonStyle(color=DANGER)),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _export(self):
        path = self.export_uc.execute(self.session)
        self._show_snack(f"CSV exported to {path}")

    def _finish(self):
        path = self.export_uc.execute(self.session)
        self._show_snack(f"All {len(self.tracks)} tracks classified! Exported to {path}")

    # ── Helpers ─────────────────────────────────────────────────────

    def _preload_llm(self):
        def _run():
            start = self.session.current_index
            end = min(start + 20, len(self.tracks))
            batch = self.tracks[start:end]
            self.classifier.preload(batch, batch_size=10)
            if self.page:
                self.page.update()

        threading.Thread(target=_run, daemon=True).start()

    def _decision_tag(self, decision: Decision | None) -> str:
        if not decision:
            return ""
        if decision.skipped:
            return "[skipped]"
        names = [self.themes[k].name for k in decision.themes if k in self.themes]
        return f"[{', '.join(names)}]" if names else ""

    def _show_snack(self, msg: str):
        self.snack.content = ft.Text(msg)
        self.snack.open = True
        self.page.update()
