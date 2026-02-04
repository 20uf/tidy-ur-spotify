"""OpenAI adapter for track classification."""

import json

from src.domain.model import Suggestion, Track
from src.domain.ports import ClassifierPort
from src.adapters.classifier._prompt import build_system_prompt, build_tracks_prompt, parse_suggestions


class OpenAIClassifierAdapter(ClassifierPort):

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", themes: dict | None = None):
        self.api_key = api_key
        self.model = model
        self.themes = themes or {}
        self._cache: dict[str, list[Suggestion]] = {}

    def classify_batch(self, tracks: list[Track]) -> list[Suggestion]:
        if not tracks:
            return []

        uncached = [t for t in tracks if t.id not in self._cache]
        if not uncached:
            return self._get_cached(tracks)

        system = build_system_prompt(self.themes)
        user_msg = build_tracks_prompt(uncached)

        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=2048,
        )
        text = response.choices[0].message.content

        suggestions = parse_suggestions(text)
        for s in suggestions:
            self._cache.setdefault(s.track_id, []).append(s)

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
