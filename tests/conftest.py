"""Shared in-memory adapters and fixtures for all bounded contexts."""

from typing import Optional

import pytest

from src.domain.model import ClassificationSession, Decision, Suggestion, Track
from src.domain.ports import ClassifierPort, ConfigPort, PlaylistPort, ProgressPort


# ── In-memory adapters ──────────────────────────────────────────────


class InMemoryClassifier(ClassifierPort):
    def __init__(self, default_theme: str = "ambiance"):
        self._suggestions: dict[str, list[Suggestion]] = {}
        self._default_theme = default_theme

    def classify_batch(self, tracks: list[Track]) -> list[Suggestion]:
        result = []
        for t in tracks:
            s = Suggestion(track_id=t.id, theme_key=self._default_theme, confidence=0.85, reasoning="Test suggestion")
            self._suggestions.setdefault(t.id, []).append(s)
            result.append(s)
        return result

    def get_suggestions(self, track_id: str) -> list[Suggestion]:
        return self._suggestions.get(track_id, [])

    def preload(self, tracks: list[Track], batch_size: int) -> None:
        self.classify_batch(tracks)


class InMemoryPlaylist(PlaylistPort):
    def __init__(self):
        self.added: list[tuple[str, str]] = []
        self.removed: list[tuple[str, str]] = []

    def add_track(self, theme_key: str, track_id: str) -> None:
        self.added.append((theme_key, track_id))

    def remove_track(self, theme_key: str, track_id: str) -> None:
        self.removed.append((theme_key, track_id))

    def tracks_in(self, theme_key: str) -> list[str]:
        added_ids = [tid for tk, tid in self.added if tk == theme_key]
        removed_ids = {tid for tk, tid in self.removed if tk == theme_key}
        return [tid for tid in added_ids if tid not in removed_ids]


class InMemoryProgress(ProgressPort):
    def __init__(self):
        self._data: Optional[ClassificationSession] = None
        self._csv_exports: list[str] = []

    def save(self, session: ClassificationSession) -> None:
        self._data = session

    def load(self) -> Optional[ClassificationSession]:
        return self._data

    def clear(self) -> None:
        self._data = None

    def exists(self) -> bool:
        return self._data is not None

    def export_csv(self, decisions: list[Decision], path: str) -> str:
        self._csv_exports.append(path)
        return path


class InMemoryConfig(ConfigPort):
    def __init__(self, data: Optional[dict] = None):
        self._data = data or {}

    def load(self) -> dict:
        return dict(self._data)

    def save(self, cfg: dict) -> None:
        self._data = dict(cfg)

    def is_configured(self) -> bool:
        return bool(self._data.get("spotify_client_id") and self._data.get("llm_api_key"))


# ── Shared fixtures ─────────────────────────────────────────────────


@pytest.fixture
def track_a():
    return Track(id="t1", name="Chill Vibes", artist="DJ Smooth", album="Late Night", popularity=72)


@pytest.fixture
def track_b():
    return Track(id="t2", name="Party Starter", artist="MC Hype", album="Friday Night", popularity=88)


@pytest.fixture
def track_c():
    return Track(id="t3", name="Slow Motion", artist="The Drifters", album="Sunset", popularity=55)


@pytest.fixture
def liked_songs(track_a, track_b, track_c):
    return [track_a, track_b, track_c]


@pytest.fixture
def classifier():
    return InMemoryClassifier()


@pytest.fixture
def playlist():
    return InMemoryPlaylist()


@pytest.fixture
def progress():
    return InMemoryProgress()
