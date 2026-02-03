"""Configuration: playlist themes, constants, and app settings."""

from src.storage import user_config

_cfg = user_config.load()


def reload():
    """Reload config from disk (call after setup dialog saves)."""
    global _cfg, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, LLM_API_KEY
    _cfg = user_config.load()
    SPOTIFY_CLIENT_ID = _cfg.get("spotify_client_id", "")
    SPOTIFY_CLIENT_SECRET = _cfg.get("spotify_client_secret", "")
    SPOTIFY_REDIRECT_URI = _cfg.get("spotify_redirect_uri", "http://localhost:8888/callback")
    LLM_API_KEY = _cfg.get("llm_api_key", "")


# Spotify API
SPOTIFY_CLIENT_ID = _cfg.get("spotify_client_id", "")
SPOTIFY_CLIENT_SECRET = _cfg.get("spotify_client_secret", "")
SPOTIFY_REDIRECT_URI = _cfg.get("spotify_redirect_uri", "http://localhost:8888/callback")
SPOTIFY_SCOPE = "user-library-read playlist-modify-public playlist-modify-private playlist-read-private"
SPOTIFY_CACHE_PATH = ".spotify_cache"

# LLM API
LLM_API_KEY = _cfg.get("llm_api_key", "")
LLM_MODEL = "claude-3-haiku-20240307"
LLM_BATCH_SIZE = 10  # Pre-classify tracks in batches of 10

# Playlist themes
THEMES = {
    "ambiance": {
        "name": "Ambiance",
        "description": "Mid-tempo, groovy, warm, melodic tracks. Can move gently but stays chill.",
        "key": "1",
    },
    "lets_dance": {
        "name": "Let's Dance",
        "description": "Upbeat, danceable, recent party hits. High energy.",
        "key": "2",
    },
}

# Sliding window config
WINDOW_PAST = 3     # Previous tracks shown for context
WINDOW_FUTURE = 3   # Upcoming tracks shown as preview

# Progress file
PROGRESS_FILE = "progress.json"
EXPORT_CSV_FILE = "export.csv"

# Audio preview
PREVIEW_DURATION_MS = 30_000  # Spotify previews are 30s
