"""Spotify OAuth2 authentication using spotipy."""

import spotipy
from spotipy.oauth2 import SpotifyOAuth

SPOTIFY_SCOPE = "user-library-read playlist-modify-public playlist-modify-private playlist-read-private"
SPOTIFY_CACHE_PATH = "spotify_auth_cache.json"


def get_spotify_client(
    client_id: str,
    client_secret: str,
    redirect_uri: str = "http://127.0.0.1:8888/callback",
) -> spotipy.Spotify:
    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SPOTIFY_SCOPE,
        cache_path=SPOTIFY_CACHE_PATH,
    )
    return spotipy.Spotify(auth_manager=auth_manager)
