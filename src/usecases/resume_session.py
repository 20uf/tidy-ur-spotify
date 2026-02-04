"""Use case: resume or start a new classification session."""

from typing import Optional

from src.domain.model import ClassificationSession, Track
from src.domain.ports import ProgressPort


class ResumeSessionUseCase:

    def __init__(self, progress: ProgressPort):
        self.progress = progress

    def execute(self, tracks: list[Track]) -> ClassificationSession:
        existing = self.progress.load()
        if existing:
            return existing
        return ClassificationSession(
            current_index=0,
            track_ids=[t.id for t in tracks],
            decisions=[],
        )
