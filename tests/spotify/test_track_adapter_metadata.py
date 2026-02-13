"""Spotify track adapter metadata mapping."""

from src.adapters.spotify.track_adapter import SpotifyTrackAdapter


class FakeSpotify:
    def current_user_saved_tracks(self, limit: int, offset: int):
        if offset > 0:
            return {"items": [], "total": 1}
        return {
            "total": 1,
            "items": [
                {
                    "track": {
                        "id": "track-1",
                        "name": "Risk It All",
                        "artists": [{"name": "Bruno Mars"}],
                        "album": {
                            "name": "Movie OST",
                            "release_date": "2026-02-27",
                            "images": [{"url": "https://cdn.example/cover.jpg"}],
                        },
                        "explicit": True,
                        "duration_ms": 204068,
                        "preview_url": None,
                        "popularity": None,
                    }
                }
            ],
        }


def test_track_adapter_maps_available_spotify_metadata():
    adapter = SpotifyTrackAdapter(FakeSpotify())

    tracks = adapter.fetch_all()

    assert len(tracks) == 1
    track = tracks[0]
    assert track.id == "track-1"
    assert track.artist == "Bruno Mars"
    assert track.album == "Movie OST"
    assert track.release_date == "2026-02-27"
    assert track.explicit is True
    assert track.album_image_url == "https://cdn.example/cover.jpg"
    assert track.duration_ms == 204068
    assert track.popularity is None
