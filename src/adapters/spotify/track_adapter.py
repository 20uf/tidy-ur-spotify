"""Spotify adapter for fetching liked songs."""

import spotipy

from src.domain.model import Track
from src.domain.ports import TrackSourcePort


class SpotifyTrackAdapter(TrackSourcePort):

    def __init__(self, sp: spotipy.Spotify):
        self.sp = sp

    def fetch_all(self) -> list[Track]:
        tracks: list[Track] = []
        offset = 0
        limit = 50

        while True:
            results = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
            items = results.get("items", [])
            if not items:
                break

            for item in items:
                t = item["track"]
                album = t.get("album", {})
                images = album.get("images", [])
                cover_url = images[0].get("url") if images and isinstance(images[0], dict) else None
                artists = ", ".join(a["name"] for a in t.get("artists", []))
                track = Track(
                    id=t["id"],
                    name=t["name"],
                    artist=artists,
                    album=album.get("name", ""),
                    release_date=album.get("release_date", ""),
                    explicit=bool(t.get("explicit", False)),
                    album_image_url=cover_url,
                    preview_url=t.get("preview_url"),
                    genres=[],
                    popularity=t.get("popularity"),
                    duration_ms=t.get("duration_ms", 0),
                )
                tracks.append(track)

            offset += limit
            if offset >= results.get("total", 0):
                break

        return tracks
