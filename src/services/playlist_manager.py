"""Manage Spotify playlists: find or create, add/remove tracks."""

from typing import Optional

import spotipy

from src.config import THEMES


class PlaylistManager:
    """Create and manage themed playlists on Spotify."""

    def __init__(self, sp: spotipy.Spotify):
        self.sp = sp
        self._playlist_cache: dict[str, str] = {}  # theme_key -> playlist_id

    def get_or_create_playlist(self, theme_key: str) -> str:
        """Get existing playlist ID for theme, or create a new one.

        Returns the Spotify playlist ID.
        """
        if theme_key in self._playlist_cache:
            return self._playlist_cache[theme_key]

        theme = THEMES[theme_key]
        playlist_name = f"🎵 {theme['name']}"

        # Search existing playlists
        existing_id = self._find_playlist(playlist_name)
        if existing_id:
            self._playlist_cache[theme_key] = existing_id
            return existing_id

        # Create new playlist
        user_id = self.sp.current_user()["id"]
        playlist = self.sp.user_playlist_create(
            user=user_id,
            name=playlist_name,
            public=False,
            description=theme["description"],
        )
        playlist_id = playlist["id"]
        self._playlist_cache[theme_key] = playlist_id
        return playlist_id

    def add_track(self, theme_key: str, track_id: str) -> None:
        """Add a track to the themed playlist (skips if already present)."""
        playlist_id = self.get_or_create_playlist(theme_key)

        if not self._track_in_playlist(playlist_id, track_id):
            self.sp.playlist_add_items(playlist_id, [track_id])

    def remove_track(self, theme_key: str, track_id: str) -> None:
        """Remove a track from the themed playlist (for undo)."""
        if theme_key not in self._playlist_cache:
            return
        playlist_id = self._playlist_cache[theme_key]
        self.sp.playlist_remove_all_occurrences_of_items(playlist_id, [track_id])

    def _find_playlist(self, name: str) -> Optional[str]:
        """Search user's playlists for one matching the given name."""
        offset = 0
        while True:
            results = self.sp.current_user_playlists(limit=50, offset=offset)
            items = results.get("items", [])
            if not items:
                break
            for pl in items:
                if pl["name"] == name:
                    return pl["id"]
            offset += 50
            if offset >= results.get("total", 0):
                break
        return None

    def _track_in_playlist(self, playlist_id: str, track_id: str) -> bool:
        """Check if a track is already in a playlist."""
        offset = 0
        while True:
            results = self.sp.playlist_items(playlist_id, limit=100, offset=offset)
            items = results.get("items", [])
            if not items:
                break
            for item in items:
                if item.get("track", {}).get("id") == track_id:
                    return True
            offset += 100
            if offset >= results.get("total", 0):
                break
        return False

    def get_existing_playlist_tracks(self, theme_key: str) -> set[str]:
        """Get all track IDs already in a themed playlist."""
        playlist_name = f"🎵 {THEMES[theme_key]['name']}"
        playlist_id = self._find_playlist(playlist_name)
        if not playlist_id:
            return set()

        track_ids = set()
        offset = 0
        while True:
            results = self.sp.playlist_items(playlist_id, limit=100, offset=offset)
            items = results.get("items", [])
            if not items:
                break
            for item in items:
                tid = item.get("track", {}).get("id")
                if tid:
                    track_ids.add(tid)
            offset += 100
            if offset >= results.get("total", 0):
                break
        return track_ids
