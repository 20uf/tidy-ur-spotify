"""JSON file-based progress persistence adapter."""

import csv
import json
import os
from dataclasses import asdict
from typing import Optional

from src.domain.model import ClassificationSession, Decision
from src.domain.ports import ProgressPort


class JsonProgressAdapter(ProgressPort):

    def __init__(self, path: str = "progress.json"):
        self.path = path

    def save(self, session: ClassificationSession) -> None:
        data = {
            "current_index": session.current_index,
            "track_ids": session.track_ids,
            "decisions": [asdict(d) for d in session.decisions],
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> Optional[ClassificationSession]:
        if not os.path.exists(self.path):
            return None
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ClassificationSession(
            current_index=data["current_index"],
            track_ids=data.get("track_ids", []),
            decisions=[Decision(**d) for d in data.get("decisions", [])],
        )

    def clear(self) -> None:
        if os.path.exists(self.path):
            os.remove(self.path)

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def export_csv(self, decisions: list[Decision], path: str = "export.csv") -> str:
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
