"""Unit tests for persistent classifier cache behavior."""

from pathlib import Path

from src.adapters.classifier.persistent_cache import (
    PersistentSuggestionCache,
    build_cache_namespace,
    build_track_cache_key,
)
from src.domain.model import Suggestion, Track


def _track(**overrides) -> Track:
    base = {
        "id": "track-1",
        "name": "Song A",
        "artist": "Artist A",
        "album": "Album A",
        "release_date": "2024-01-01",
        "duration_ms": 180000,
        "explicit": False,
        "popularity": 42,
    }
    base.update(overrides)
    return Track(**base)


def test_persistent_cache_roundtrip(tmp_path: Path):
    path = tmp_path / "classifier-cache.json"
    cache = PersistentSuggestionCache(str(path))
    namespace = build_cache_namespace(
        "openai",
        "gpt-4o-mini",
        {"ambiance": {"name": "Ambiance", "description": "Warm and chill", "key": "1"}},
    )
    key = build_track_cache_key(namespace, _track())
    suggestions = [Suggestion(track_id="track-1", theme_key="ambiance", confidence=0.9, reasoning="Warm vibe")]

    cache.put_many({key: suggestions})
    reloaded = PersistentSuggestionCache(str(path))

    assert reloaded.get(key) == suggestions


def test_track_cache_key_changes_when_metadata_changes():
    namespace = build_cache_namespace(
        "openai",
        "gpt-4o-mini",
        {"ambiance": {"name": "Ambiance", "description": "Warm and chill", "key": "1"}},
    )
    key_a = build_track_cache_key(namespace, _track())
    key_b = build_track_cache_key(namespace, _track(duration_ms=181000))

    assert key_a != key_b


def test_track_cache_key_changes_when_namespace_changes():
    track = _track()
    ns_a = build_cache_namespace(
        "openai",
        "gpt-4o-mini",
        {"ambiance": {"name": "Ambiance", "description": "Warm and chill", "key": "1"}},
    )
    ns_b = build_cache_namespace(
        "openai",
        "gpt-4.1-mini",
        {"ambiance": {"name": "Ambiance", "description": "Warm and chill", "key": "1"}},
    )

    assert build_track_cache_key(ns_a, track) != build_track_cache_key(ns_b, track)


def test_corrupt_cache_file_is_ignored(tmp_path: Path):
    path = tmp_path / "broken-cache.json"
    path.write_text("{not-json", encoding="utf-8")

    cache = PersistentSuggestionCache(str(path))
    namespace = build_cache_namespace(
        "openai",
        "gpt-4o-mini",
        {"ambiance": {"name": "Ambiance", "description": "Warm and chill", "key": "1"}},
    )
    key = build_track_cache_key(namespace, _track())

    assert cache.get(key) == []
