"""Ports (interfaces) for the hexagonal architecture."""

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.model import (
    ClassificationSession,
    Decision,
    Suggestion,
    Theme,
    Track,
)


class TrackSourcePort(ABC):
    @abstractmethod
    def fetch_all(self) -> list[Track]:
        ...


class ClassifierPort(ABC):
    @abstractmethod
    def classify_batch(self, tracks: list[Track]) -> list[Suggestion]:
        ...

    @abstractmethod
    def get_suggestions(self, track_id: str) -> list[Suggestion]:
        ...

    @abstractmethod
    def preload(self, tracks: list[Track], batch_size: int) -> None:
        ...


class PlaylistPort(ABC):
    @abstractmethod
    def add_track(self, theme_key: str, track_id: str) -> None:
        ...

    @abstractmethod
    def remove_track(self, theme_key: str, track_id: str) -> None:
        ...


class ProgressPort(ABC):
    @abstractmethod
    def save(self, session: ClassificationSession) -> None:
        ...

    @abstractmethod
    def load(self) -> Optional[ClassificationSession]:
        ...

    @abstractmethod
    def clear(self) -> None:
        ...

    @abstractmethod
    def exists(self) -> bool:
        ...

    @abstractmethod
    def export_csv(self, decisions: list[Decision], path: str) -> str:
        ...


class ConfigPort(ABC):
    @abstractmethod
    def load(self) -> dict:
        ...

    @abstractmethod
    def save(self, cfg: dict) -> None:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        ...
