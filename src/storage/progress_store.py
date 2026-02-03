"""Save, load, and clear classification progress to/from disk."""

import csv
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Optional

from src.config import EXPORT_CSV_FILE, PROGRESS_FILE


@dataclass
class TrackDecision:
    track_id: str
    track_name: str
    artist: str
    themes: list[str] = field(default_factory=list)  # can belong to multiple
    skipped: bool = False


@dataclass
class ProgressState:
    current_index: int = 0
    decisions: list[TrackDecision] = field(default_factory=list)
    track_ids: list[str] = field(default_factory=list)  # ordered liked songs IDs


class ProgressStore:
    """Persist classification progress as JSON. Supports save/load/clear."""

    def __init__(self, path: str = PROGRESS_FILE):
        self.path = path

    def save(self, state: ProgressState) -> None:
        data = {
            "current_index": state.current_index,
            "track_ids": state.track_ids,
            "decisions": [asdict(d) for d in state.decisions],
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> Optional[ProgressState]:
        if not os.path.exists(self.path):
            return None
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        state = ProgressState(
            current_index=data["current_index"],
            track_ids=data.get("track_ids", []),
            decisions=[TrackDecision(**d) for d in data.get("decisions", [])],
        )
        return state

    def clear(self) -> None:
        if os.path.exists(self.path):
            os.remove(self.path)

    def exists(self) -> bool:
        return os.path.exists(self.path)

    @staticmethod
    def export_csv(decisions: list[TrackDecision], path: str = EXPORT_CSV_FILE) -> str:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["track_id", "track_name", "artist", "themes", "skipped"])
            for d in decisions:
                writer.writerow([
                    d.track_id,
                    d.track_name,
                    d.artist,
                    "|".join(d.themes),
                    d.skipped,
                ])
        return path
