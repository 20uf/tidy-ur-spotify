"""Prompt building behavior for metadata-rich track classification."""

from src.adapters.classifier._prompt import build_tracks_prompt
from src.domain.model import Track


def test_tracks_prompt_includes_release_duration_and_explicit_flags():
    prompt = build_tracks_prompt([
        Track(
            id="t1",
            name="Song A",
            artist="Artist A",
            album="Album A",
            release_date="2024-10-11",
            duration_ms=210000,
            explicit=True,
            popularity=52,
        )
    ])

    assert 'Release Date: 2024-10-11' in prompt
    assert 'Duration Sec: 210' in prompt
    assert 'Explicit: yes' in prompt
    assert 'Popularity: 52' in prompt


def test_tracks_prompt_uses_safe_defaults_for_missing_metadata():
    prompt = build_tracks_prompt([
        Track(
            id="t2",
            name="Song B",
            artist="Artist B",
            album="Album B",
        )
    ])

    assert 'Release Date: unknown' in prompt
    assert 'Duration Sec: 0' in prompt
    assert 'Explicit: no' in prompt
    assert 'Popularity: unknown' in prompt
