"""Dry-run playlist adapter that never writes to Spotify."""

from src.domain.ports import PlaylistPort


class DryRunPlaylistAdapter(PlaylistPort):
    """No-op playlist adapter used for safe simulation runs."""

    def __init__(self):
        self.added: list[tuple[str, str]] = []
        self.removed: list[tuple[str, str]] = []

    def add_track(self, theme_key: str, track_id: str) -> None:
        self.added.append((theme_key, track_id))

    def remove_track(self, theme_key: str, track_id: str) -> None:
        self.removed.append((theme_key, track_id))
