"""Persistent local cache for classifier suggestions."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from src.adapters.classifier._prompt import SYSTEM_PROMPT
from src.domain.model import Suggestion, Track

logger = logging.getLogger("tidy_ur_spotify.classifier.cache")


def _sha1(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def build_cache_namespace(provider: str, model: str, themes: dict) -> str:
    payload = {
        "provider": provider,
        "model": model,
        "themes": themes,
        "prompt_hash": _sha1(SYSTEM_PROMPT),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _sha1(serialized)


def build_track_cache_key(namespace: str, track: Track) -> str:
    metadata = {
        "id": track.id,
        "name": track.name,
        "artist": track.artist,
        "album": track.album,
        "release_date": track.release_date,
        "duration_ms": track.duration_ms,
        "explicit": track.explicit,
        "popularity": track.popularity,
    }
    serialized = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    return f"{namespace}:{track.id}:{_sha1(serialized)}"


class PersistentSuggestionCache:
    """Disk-backed cache for LLM suggestions."""

    def __init__(self, path: str):
        self.path = Path(path)
        self._entries: dict[str, list[dict]] = {}
        self._load()

    def get(self, key: str) -> list[Suggestion]:
        raw_items = self._entries.get(key, [])
        suggestions: list[Suggestion] = []
        for item in raw_items:
            suggestions.append(
                Suggestion(
                    track_id=str(item.get("track_id", "")),
                    theme_key=str(item.get("theme_key", "")),
                    confidence=float(item.get("confidence", 0.0)),
                    reasoning=str(item.get("reasoning", "")),
                )
            )
        return suggestions

    def put_many(self, values: dict[str, list[Suggestion]]) -> None:
        changed = False
        for key, suggestions in values.items():
            if not suggestions:
                continue

            serialized = [
                {
                    "track_id": s.track_id,
                    "theme_key": s.theme_key,
                    "confidence": s.confidence,
                    "reasoning": s.reasoning,
                }
                for s in suggestions
            ]
            if self._entries.get(key) != serialized:
                self._entries[key] = serialized
                changed = True

        if changed:
            self._save()

    def _load(self) -> None:
        if not self.path.exists():
            return

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                entries = payload.get("entries", {})
                if isinstance(entries, dict):
                    self._entries = {
                        str(key): value
                        for key, value in entries.items()
                        if isinstance(value, list)
                    }
        except Exception:
            logger.exception("Failed to load classifier cache from %s", self.path)
            self._entries = {}

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            payload = {"entries": self._entries}
            temp_path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
            temp_path.replace(self.path)
        except Exception:
            logger.exception("Failed to save classifier cache to %s", self.path)
