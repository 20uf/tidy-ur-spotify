"""Fetch all liked songs from Spotify."""

from dataclasses import dataclass
from typing import Optional

import spotipy


@dataclass
class Track:
    id: str
    name: str
    artist: str
    album: str
    preview_url: Optional[str]
    genres: list[str]
    popularity: int
    duration_ms: int


def fetch_liked_songs(sp: spotipy.Spotify, limit: int = 50) -> list[Track]:
    """Fetch all liked songs from the user's Spotify library.

    Paginates through all results using the Spotify API limit of 50 per request.
    """
    tracks: list[Track] = []
    offset = 0

    while True:
        results = sp.current_user_saved_tracks(limit=limit, offset=offset)
        items = results.get("items", [])
        if not items:
            break

        for item in items:
            t = item["track"]
            artists = ", ".join(a["name"] for a in t.get("artists", []))
            track = Track(
                id=t["id"],
                name=t["name"],
                artist=artists,
                album=t.get("album", {}).get("name", ""),
                preview_url=t.get("preview_url"),
                genres=[],  # genres come from artist, fetched separately if needed
                popularity=t.get("popularity", 0),
                duration_ms=t.get("duration_ms", 0),
            )
            tracks.append(track)

        offset += limit
        if offset >= results.get("total", 0):
            break

    return tracks
