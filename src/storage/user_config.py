"""Persistent user configuration stored as JSON next to the executable."""

import json
import os
import sys


def _config_dir() -> str:
    """Return the directory where config.json lives.

    - PyInstaller bundle: next to the .exe
    - Normal Python: project root (cwd)
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()


CONFIG_PATH = os.path.join(_config_dir(), "config.json")

_DEFAULTS = {
    "spotify_client_id": "",
    "spotify_client_secret": "",
    "spotify_redirect_uri": "http://localhost:8888/callback",
    "llm_provider": "openai",
    "llm_api_key": "",
    "llm_model": "",
}


def load() -> dict:
    """Load config from disk, merged with defaults."""
    cfg = dict(_DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


def save(cfg: dict) -> None:
    """Write config to disk."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def is_configured() -> bool:
    """Return True if all required keys are filled in."""
    cfg = load()
    return bool(
        cfg.get("spotify_client_id")
        and cfg.get("spotify_client_secret")
        and cfg.get("llm_api_key")
        and cfg.get("llm_provider")
    )
