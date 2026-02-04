"""Spotify adapter for playlist management."""

from typing import Optional

import spotipy

from src.domain.ports import PlaylistPort


class SpotifyPlaylistAdapter(PlaylistPort):

    def __init__(self, sp: spotipy.Spotify, themes: dict):
        self.sp = sp
        self.themes = themes
        self._playlist_cache: dict[str, str] = {}

    def add_track(self, theme_key: str, track_id: str) -> None:
        playlist_id = self._get_or_create_playlist(theme_key)
        if not self._track_in_playlist(playlist_id, track_id):
            self.sp.playlist_add_items(playlist_id, [track_id])

    def remove_track(self, theme_key: str, track_id: str) -> None:
        if theme_key not in self._playlist_cache:
            return
        playlist_id = self._playlist_cache[theme_key]
        self.sp.playlist_remove_all_occurrences_of_items(playlist_id, [track_id])

    def _get_or_create_playlist(self, theme_key: str) -> str:
        if theme_key in self._playlist_cache:
            return self._playlist_cache[theme_key]

        theme = self.themes[theme_key]
        playlist_name = f"\U0001f3b5 {theme['name']}"

        existing_id = self._find_playlist(playlist_name)
        if existing_id:
            self._playlist_cache[theme_key] = existing_id
            return existing_id

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

    def _find_playlist(self, name: str) -> Optional[str]:
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
