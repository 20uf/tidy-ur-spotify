"""Shared prompt logic for LLM classifier adapters."""

import json

from src.domain.model import Suggestion, Track


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


def build_system_prompt(themes: dict) -> str:
    parts = []
    for key, theme in themes.items():
        parts.append(f'- "{key}": {theme["name"]} — {theme["description"]}')
    return SYSTEM_PROMPT.format(themes="\n".join(parts))


def build_tracks_prompt(tracks: list[Track]) -> str:
    lines = ["Classify these tracks:\n"]
    for t in tracks:
        popularity = t.popularity if t.popularity is not None else "unknown"
        duration_seconds = round((t.duration_ms or 0) / 1000)
        release_date = t.release_date or "unknown"
        explicit = "yes" if t.explicit else "no"
        lines.append(
            f'- ID: {t.id}, Title: "{t.name}", Artist: "{t.artist}", '
            f'Album: "{t.album}", Release Date: {release_date}, Duration Sec: {duration_seconds}, '
            f'Explicit: {explicit}, Popularity: {popularity}'
        )
    return "\n".join(lines)


def parse_suggestions(text: str) -> list[Suggestion]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
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
            Suggestion(
                track_id=item.get("track_id", ""),
                theme_key=item.get("suggested_theme", ""),
                confidence=float(item.get("confidence", 0.0)),
                reasoning=item.get("reasoning", ""),
            )
        )
    return suggestions
