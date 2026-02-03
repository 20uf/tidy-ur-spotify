"""Batch LLM classification of tracks into playlist themes."""

import json
from dataclasses import dataclass

import anthropic

from src.config import LLM_API_KEY, LLM_BATCH_SIZE, LLM_MODEL, THEMES


@dataclass
class TrackSuggestion:
    track_id: str
    suggested_theme: str  # theme key from THEMES
    confidence: float     # 0.0 - 1.0
    reasoning: str


SYSTEM_PROMPT = """You are a music classification assistant. You classify songs into playlist themes based on their metadata.

Available themes:
{themes}

For each track, suggest the BEST matching theme. A track can match multiple themes.
Respond with valid JSON only - an array of objects with these fields:
- track_id: string
- suggested_theme: string (theme key)
- confidence: float (0.0-1.0)
- reasoning: string (brief explanation)

If a track could fit multiple themes, return one entry per theme for that track."""


def _build_themes_description() -> str:
    parts = []
    for key, theme in THEMES.items():
        parts.append(f'- "{key}": {theme["name"]} — {theme["description"]}')
    return "\n".join(parts)


def _build_tracks_prompt(tracks: list[dict]) -> str:
    lines = ["Classify these tracks:\n"]
    for t in tracks:
        lines.append(
            f'- ID: {t["id"]}, Title: "{t["name"]}", Artist: "{t["artist"]}", '
            f'Album: "{t["album"]}", Popularity: {t["popularity"]}'
        )
    return "\n".join(lines)


class LLMClassifier:
    """Classify tracks into themes using an LLM."""

    def __init__(self, api_key: str = LLM_API_KEY, model: str = LLM_MODEL):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self._cache: dict[str, list[TrackSuggestion]] = {}

    def classify_batch(self, tracks: list[dict]) -> list[TrackSuggestion]:
        """Classify a batch of tracks (up to LLM_BATCH_SIZE).

        Args:
            tracks: List of dicts with keys: id, name, artist, album, popularity

        Returns:
            List of TrackSuggestion for all tracks in the batch.
        """
        if not tracks:
            return []

        # Check cache first
        uncached = [t for t in tracks if t["id"] not in self._cache]
        if not uncached:
            return self._get_cached(tracks)

        system = SYSTEM_PROMPT.format(themes=_build_themes_description())
        user_msg = _build_tracks_prompt(uncached)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )

        text = response.content[0].text
        suggestions = self._parse_response(text)

        # Cache results by track_id
        for s in suggestions:
            self._cache.setdefault(s.track_id, []).append(s)

        return self._get_cached(tracks)

    def get_suggestion(self, track_id: str) -> list[TrackSuggestion]:
        """Get cached suggestions for a single track."""
        return self._cache.get(track_id, [])

    def preload(self, tracks: list[dict]) -> None:
        """Pre-classify tracks in batches of LLM_BATCH_SIZE."""
        for i in range(0, len(tracks), LLM_BATCH_SIZE):
            batch = tracks[i : i + LLM_BATCH_SIZE]
            self.classify_batch(batch)

    def _get_cached(self, tracks: list[dict]) -> list[TrackSuggestion]:
        result = []
        for t in tracks:
            result.extend(self._cache.get(t["id"], []))
        return result

    @staticmethod
    def _parse_response(text: str) -> list[TrackSuggestion]:
        """Parse JSON response from LLM into TrackSuggestion objects."""
        # Strip markdown code fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]  # remove opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return []

        suggestions = []
        for item in data:
            suggestions.append(
                TrackSuggestion(
                    track_id=item.get("track_id", ""),
                    suggested_theme=item.get("suggested_theme", ""),
                    confidence=float(item.get("confidence", 0.0)),
                    reasoning=item.get("reasoning", ""),
                )
            )
        return suggestions
