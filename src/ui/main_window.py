"""Main GUI window using Tkinter for the Spotify Ranger classification flow."""

import io
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from src.config import THEMES, WINDOW_FUTURE, WINDOW_PAST
from src.version import __version__
from src.services.llm_classifier import LLMClassifier, TrackSuggestion
from src.services.playlist_manager import PlaylistManager
from src.services.track_fetcher import Track
from src.storage.progress_store import (
    ProgressState,
    ProgressStore,
    TrackDecision,
)


class MainWindow:
    """Tkinter-based GUI for classifying Spotify tracks into playlists."""

    def __init__(
        self,
        tracks: list[Track],
        classifier: LLMClassifier,
        playlist_manager: PlaylistManager,
        progress_store: ProgressStore,
        audio_player: Optional[object] = None,
    ):
        self.tracks = tracks
        self.classifier = classifier
        self.playlist_mgr = playlist_manager
        self.store = progress_store
        self.audio_player = audio_player

        # State
        self.state = self._load_or_init_state()
        self.decisions: list[TrackDecision] = list(self.state.decisions)
        self.current_index: int = self.state.current_index

        # Build UI
        self.root = tk.Tk()
        self.root.title(f"Spotify Ranger {__version__}")
        self.root.geometry("900x700")
        self.root.configure(bg="#191414")
        self._build_ui()
        self._bind_keys()

        # Kick off LLM preload in background
        self._preload_llm()

    def _load_or_init_state(self) -> ProgressState:
        existing = self.store.load()
        if existing:
            return existing
        return ProgressState(
            current_index=0,
            track_ids=[t.id for t in self.tracks],
            decisions=[],
        )

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Header
        header = tk.Frame(self.root, bg="#1DB954", height=50)
        header.pack(fill=tk.X)
        tk.Label(
            header, text="Spotify Ranger", font=("Helvetica", 18, "bold"),
            bg="#1DB954", fg="white",
        ).pack(pady=10)

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self.root, variable=self.progress_var, maximum=len(self.tracks),
        )
        self.progress_bar.pack(fill=tk.X, padx=20, pady=5)

        self.progress_label = tk.Label(
            self.root, text="", bg="#191414", fg="white", font=("Helvetica", 10),
        )
        self.progress_label.pack()

        # Main content frame
        content = tk.Frame(self.root, bg="#191414")
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Past tracks (left context)
        past_frame = tk.LabelFrame(
            content, text="Previous", bg="#191414", fg="#B3B3B3",
            font=("Helvetica", 10),
        )
        past_frame.pack(fill=tk.X, pady=5)
        self.past_labels: list[tk.Label] = []
        for _ in range(WINDOW_PAST):
            lbl = tk.Label(past_frame, text="", bg="#191414", fg="#B3B3B3", anchor="w")
            lbl.pack(fill=tk.X, padx=10)
            self.past_labels.append(lbl)

        # Current track (center)
        current_frame = tk.LabelFrame(
            content, text="Now Playing", bg="#282828", fg="#1DB954",
            font=("Helvetica", 12, "bold"),
        )
        current_frame.pack(fill=tk.X, pady=10)

        self.current_title = tk.Label(
            current_frame, text="", bg="#282828", fg="white",
            font=("Helvetica", 16, "bold"),
        )
        self.current_title.pack(pady=(10, 2))

        self.current_artist = tk.Label(
            current_frame, text="", bg="#282828", fg="#B3B3B3",
            font=("Helvetica", 12),
        )
        self.current_artist.pack(pady=(0, 5))

        self.suggestion_label = tk.Label(
            current_frame, text="", bg="#282828", fg="#1DB954",
            font=("Helvetica", 11, "italic"),
        )
        self.suggestion_label.pack(pady=(0, 10))

        # Future tracks (right context)
        future_frame = tk.LabelFrame(
            content, text="Coming Up", bg="#191414", fg="#B3B3B3",
            font=("Helvetica", 10),
        )
        future_frame.pack(fill=tk.X, pady=5)
        self.future_labels: list[tk.Label] = []
        for _ in range(WINDOW_FUTURE):
            lbl = tk.Label(future_frame, text="", bg="#191414", fg="#B3B3B3", anchor="w")
            lbl.pack(fill=tk.X, padx=10)
            self.future_labels.append(lbl)

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#191414")
        btn_frame.pack(fill=tk.X, padx=20, pady=10)

        for theme_key, theme in THEMES.items():
            btn = tk.Button(
                btn_frame,
                text=f"[{theme['key']}] {theme['name']}",
                bg="#1DB954", fg="white", font=("Helvetica", 12, "bold"),
                command=lambda k=theme_key: self._decide(k),
                width=18,
            )
            btn.pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="[S] Skip", bg="#535353", fg="white",
            font=("Helvetica", 12), command=self._skip, width=10,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="[←] Undo", bg="#535353", fg="white",
            font=("Helvetica", 12), command=self._undo, width=10,
        ).pack(side=tk.LEFT, padx=5)

        # Bottom bar
        bottom = tk.Frame(self.root, bg="#191414")
        bottom.pack(fill=tk.X, padx=20, pady=5)

        tk.Button(
            bottom, text="Pause & Save", bg="#B3B3B3", fg="#191414",
            command=self._pause,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            bottom, text="Stop & Clear", bg="#E74C3C", fg="white",
            command=self._stop,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            bottom, text="Export CSV", bg="#B3B3B3", fg="#191414",
            command=self._export,
        ).pack(side=tk.RIGHT, padx=5)

        self._refresh_display()

    def _bind_keys(self):
        self.root.bind("1", lambda e: self._decide("ambiance"))
        self.root.bind("2", lambda e: self._decide("lets_dance"))
        self.root.bind("s", lambda e: self._skip())
        self.root.bind("S", lambda e: self._skip())
        self.root.bind("<Left>", lambda e: self._undo())
        self.root.bind("<Escape>", lambda e: self._pause())

    def _refresh_display(self):
        total = len(self.tracks)
        idx = self.current_index

        # Progress
        decided = len(self.decisions)
        self.progress_var.set(decided)
        self.progress_label.config(text=f"{decided} / {total} tracks classified")

        if idx >= total:
            self._finish()
            return

        # Past tracks
        for i, lbl in enumerate(self.past_labels):
            past_idx = idx - WINDOW_PAST + i
            if 0 <= past_idx < total:
                t = self.tracks[past_idx]
                decision = self._get_decision(t.id)
                tag = self._decision_tag(decision)
                lbl.config(text=f"  {t.artist} — {t.name} {tag}")
            else:
                lbl.config(text="")

        # Current track
        track = self.tracks[idx]
        self.current_title.config(text=track.name)
        self.current_artist.config(text=f"{track.artist}  •  {track.album}")

        # LLM suggestion
        suggestions = self.classifier.get_suggestion(track.id)
        if suggestions:
            best = max(suggestions, key=lambda s: s.confidence)
            theme_name = THEMES.get(best.suggested_theme, {}).get("name", best.suggested_theme)
            self.suggestion_label.config(
                text=f"AI suggests: {theme_name} ({best.confidence:.0%}) — {best.reasoning}"
            )
        else:
            self.suggestion_label.config(text="AI: analyzing...")

        # Future tracks
        for i, lbl in enumerate(self.future_labels):
            fut_idx = idx + 1 + i
            if fut_idx < total:
                t = self.tracks[fut_idx]
                lbl.config(text=f"  {t.artist} — {t.name}")
            else:
                lbl.config(text="")

        # Play audio preview
        self._play_preview(track)

    def _decide(self, theme_key: str):
        if self.current_index >= len(self.tracks):
            return
        track = self.tracks[self.current_index]

        # Check if already decided (update)
        existing = self._get_decision(track.id)
        if existing:
            if theme_key not in existing.themes:
                existing.themes.append(theme_key)
        else:
            decision = TrackDecision(
                track_id=track.id,
                track_name=track.name,
                artist=track.artist,
                themes=[theme_key],
            )
            self.decisions.append(decision)

        # Add to Spotify playlist in background
        threading.Thread(
            target=self.playlist_mgr.add_track,
            args=(theme_key, track.id),
            daemon=True,
        ).start()

        self.current_index += 1
        self._save_state()
        self._refresh_display()

    def _skip(self):
        if self.current_index >= len(self.tracks):
            return
        track = self.tracks[self.current_index]
        decision = TrackDecision(
            track_id=track.id,
            track_name=track.name,
            artist=track.artist,
            skipped=True,
        )
        self.decisions.append(decision)
        self.current_index += 1
        self._save_state()
        self._refresh_display()

    def _undo(self):
        if self.current_index <= 0 or not self.decisions:
            return

        last = self.decisions.pop()
        self.current_index -= 1

        # Undo playlist additions in background
        if last.themes:
            for theme_key in last.themes:
                threading.Thread(
                    target=self.playlist_mgr.remove_track,
                    args=(theme_key, last.track_id),
                    daemon=True,
                ).start()

        self._save_state()
        self._refresh_display()

    def _pause(self):
        self._save_state()
        self._stop_audio()
        messagebox.showinfo("Paused", "Progress saved. You can resume later.")
        self.root.destroy()

    def _stop(self):
        if messagebox.askyesno("Stop", "This will delete all progress. Continue?"):
            self.store.clear()
            self._stop_audio()
            self.root.destroy()

    def _export(self):
        path = ProgressStore.export_csv(self.decisions)
        messagebox.showinfo("Exported", f"CSV exported to {path}")

    def _finish(self):
        self._stop_audio()
        self._save_state()
        path = ProgressStore.export_csv(self.decisions)
        messagebox.showinfo(
            "Done!",
            f"All {len(self.tracks)} tracks classified!\nExported to {path}",
        )

    def _save_state(self):
        state = ProgressState(
            current_index=self.current_index,
            track_ids=[t.id for t in self.tracks],
            decisions=list(self.decisions),
        )
        self.store.save(state)

    def _get_decision(self, track_id: str) -> Optional[TrackDecision]:
        for d in self.decisions:
            if d.track_id == track_id:
                return d
        return None

    @staticmethod
    def _decision_tag(decision: Optional[TrackDecision]) -> str:
        if not decision:
            return ""
        if decision.skipped:
            return "[skipped]"
        names = [THEMES[k]["name"] for k in decision.themes if k in THEMES]
        return f"[{', '.join(names)}]" if names else ""

    def _preload_llm(self):
        """Pre-classify upcoming tracks in a background thread."""
        def _run():
            start = self.current_index
            end = min(start + 20, len(self.tracks))  # preload 20 ahead
            batch_dicts = [
                {
                    "id": t.id,
                    "name": t.name,
                    "artist": t.artist,
                    "album": t.album,
                    "popularity": t.popularity,
                }
                for t in self.tracks[start:end]
            ]
            self.classifier.preload(batch_dicts)
            # Refresh display to show suggestion
            if self.root.winfo_exists():
                self.root.after(0, self._refresh_display)

        threading.Thread(target=_run, daemon=True).start()

    def _play_preview(self, track: Track):
        """Play audio preview using pygame if available."""
        if not self.audio_player or not track.preview_url:
            return
        try:
            self.audio_player.play(track.preview_url)
        except Exception:
            pass  # Preview not critical

    def _stop_audio(self):
        if self.audio_player:
            try:
                self.audio_player.stop()
            except Exception:
                pass

    def run(self):
        self.root.mainloop()
