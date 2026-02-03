"""Spotify OAuth2 authentication using spotipy."""

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from src.config import (
    SPOTIFY_CACHE_PATH,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPE,
)


def get_spotify_client() -> spotipy.Spotify:
    """Create and return an authenticated Spotify client.

    Opens a browser for OAuth flow on first run; uses cached token afterwards.
    """
    auth_manager = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE,
        cache_path=SPOTIFY_CACHE_PATH,
    )
    return spotipy.Spotify(auth_manager=auth_manager)
