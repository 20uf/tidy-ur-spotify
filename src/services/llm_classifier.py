"""Batch LLM classification of tracks into playlist themes.

Supports multiple providers: OpenAI (default) and Anthropic.
"""

import json
from dataclasses import dataclass

from src.config import LLM_BATCH_SIZE, THEMES


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


# ── Provider registry ──────────────────────────────────────────────

PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "default_model": "gpt-4o-mini",
        "label": "OpenAI (GPT)",
        "url": "https://platform.openai.com/api-keys",
    },
    "anthropic": {
        "name": "Anthropic",
        "default_model": "claude-3-haiku-20240307",
        "label": "Anthropic",
        "url": "https://console.anthropic.com",
    },
}

DEFAULT_PROVIDER = "openai"


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


# ── Provider clients ───────────────────────────────────────────────

def _call_openai(api_key: str, model: str, system: str, user_msg: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=2048,
    )
    return response.choices[0].message.content


def _call_anthropic(api_key: str, model: str, system: str, user_msg: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text


_PROVIDER_CALLERS = {
    "openai": _call_openai,
    "anthropic": _call_anthropic,
}


# ── Classifier ─────────────────────────────────────────────────────

class LLMClassifier:
    """Classify tracks into themes using an LLM provider."""

    def __init__(self, provider: str = DEFAULT_PROVIDER, api_key: str = "", model: str = ""):
        self.provider = provider
        self.api_key = api_key
        self.model = model or PROVIDERS[provider]["default_model"]
        self._caller = _PROVIDER_CALLERS[provider]
        self._cache: dict[str, list[TrackSuggestion]] = {}

    def classify_batch(self, tracks: list[dict]) -> list[TrackSuggestion]:
        if not tracks:
            return []

        uncached = [t for t in tracks if t["id"] not in self._cache]
        if not uncached:
            return self._get_cached(tracks)

        system = SYSTEM_PROMPT.format(themes=_build_themes_description())
        user_msg = _build_tracks_prompt(uncached)

        text = self._caller(self.api_key, self.model, system, user_msg)
        suggestions = self._parse_response(text)

        for s in suggestions:
            self._cache.setdefault(s.track_id, []).append(s)

        return self._get_cached(tracks)

    def get_suggestion(self, track_id: str) -> list[TrackSuggestion]:
        return self._cache.get(track_id, [])

    def preload(self, tracks: list[dict]) -> None:
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
                TrackSuggestion(
                    track_id=item.get("track_id", ""),
                    suggested_theme=item.get("suggested_theme", ""),
                    confidence=float(item.get("confidence", 0.0)),
                    reasoning=item.get("reasoning", ""),
                )
            )
        return suggestions
