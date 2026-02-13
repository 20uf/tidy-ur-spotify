"""Pure domain objects — no framework dependency."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Track:
    id: str
    name: str
    artist: str
    album: str
    popularity: int | None = None
    duration_ms: int = 0
    release_date: str = ""
    explicit: bool = False
    album_image_url: Optional[str] = None
    preview_url: Optional[str] = None
    genres: list[str] = field(default_factory=list)


@dataclass
class Theme:
    key: str
    name: str
    description: str
    shortcut: str


@dataclass
class Suggestion:
    track_id: str
    theme_key: str
    confidence: float
    reasoning: str


@dataclass
class Decision:
    track_id: str
    track_name: str
    artist: str
    themes: list[str] = field(default_factory=list)
    skipped: bool = False


@dataclass
class ClassificationSession:
    current_index: int = 0
    track_ids: list[str] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)

    @property
    def decided_count(self) -> int:
        return len(self.decisions)

    def decision_for(self, track_id: str) -> Optional[Decision]:
        for d in self.decisions:
            if d.track_id == track_id:
                return d
        return None

    def add_decision(self, decision: Decision) -> None:
        self.decisions.append(decision)
        self.current_index += 1

    def undo_last(self) -> Optional[Decision]:
        if not self.decisions or self.current_index <= 0:
            return None
        last = self.decisions.pop()
        self.current_index -= 1
        return last
