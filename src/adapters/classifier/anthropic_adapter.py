"""Anthropic adapter for track classification."""

import logging
import os
import time

from src.adapters.classifier.persistent_cache import (
    PersistentSuggestionCache,
    build_cache_namespace,
    build_track_cache_key,
)
from src.domain.model import Suggestion, Track
from src.domain.ports import ClassifierPort
from src.adapters.classifier._prompt import build_system_prompt, build_tracks_prompt, parse_suggestions

logger = logging.getLogger("tidy_ur_spotify.classifier.anthropic")


class AnthropicClassifierAdapter(ClassifierPort):

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307", themes: dict | None = None):
        self.api_key = api_key
        self.model = model
        self.themes = themes or {}
        self._cache: dict[str, list[Suggestion]] = {}
        self._persistent_cache_enabled = not _is_truthy(os.getenv("TIDY_SPOTIFY_DISABLE_PERSISTENT_CACHE", "0"))
        self._persistent_cache = PersistentSuggestionCache(
            os.getenv("TIDY_SPOTIFY_CACHE_FILE", "classification_cache.json")
        )
        self._namespace = build_cache_namespace("anthropic", self.model, self.themes)

    def classify_batch(self, tracks: list[Track]) -> list[Suggestion]:
        if not tracks:
            return []

        uncached: list[Track] = []
        cache_hits = 0
        for track in tracks:
            if track.id in self._cache:
                continue
            if self._persistent_cache_enabled:
                persistent_key = build_track_cache_key(self._namespace, track)
                persisted = self._persistent_cache.get(persistent_key)
                if persisted:
                    self._cache[track.id] = persisted
                    cache_hits += 1
                    continue
            uncached.append(track)

        if cache_hits > 0:
            logger.info("Anthropic persistent cache hits=%s misses=%s", cache_hits, len(uncached))

        if not uncached:
            return self._get_cached(tracks)

        system = build_system_prompt(self.themes)
        user_msg = build_tracks_prompt(uncached)
        timeout_s = float(os.getenv("TIDY_SPOTIFY_LLM_TIMEOUT", "90"))
        started_at = time.perf_counter()
        logger.info(
            "Anthropic request started (model=%s, uncached_tracks=%s, timeout=%.0fs)",
            self.model,
            len(uncached),
            timeout_s,
        )

        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key, timeout=timeout_s)
        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            )
        except Exception:
            logger.exception("Anthropic request failed")
            raise
        text = response.content[0].text

        suggestions = parse_suggestions(text)
        logger.info(
            "Anthropic request completed (duration=%.1fs, suggestions=%s)",
            time.perf_counter() - started_at,
            len(suggestions),
        )

        uncached_ids = {track.id for track in uncached}
        grouped: dict[str, list[Suggestion]] = {track.id: [] for track in uncached}
        for suggestion in suggestions:
            if suggestion.track_id in uncached_ids:
                grouped[suggestion.track_id].append(suggestion)

        for track in uncached:
            self._cache[track.id] = grouped.get(track.id, [])

        if self._persistent_cache_enabled:
            to_persist: dict[str, list[Suggestion]] = {}
            for track in uncached:
                track_suggestions = self._cache.get(track.id, [])
                if track_suggestions:
                    to_persist[build_track_cache_key(self._namespace, track)] = track_suggestions
            self._persistent_cache.put_many(to_persist)

        return self._get_cached(tracks)

    def get_suggestions(self, track_id: str) -> list[Suggestion]:
        return self._cache.get(track_id, [])

    def preload(self, tracks: list[Track], batch_size: int = 10) -> None:
        for i in range(0, len(tracks), batch_size):
            self.classify_batch(tracks[i : i + batch_size])

    def _get_cached(self, tracks: list[Track]) -> list[Suggestion]:
        result = []
        for t in tracks:
            result.extend(self._cache.get(t.id, []))
        return result


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}
