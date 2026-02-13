"""JSON file-based config adapter."""

import json
import os
import sys

from src.domain.ports import ConfigPort

_DEFAULTS = {
    "spotify_client_id": "",
    "spotify_client_secret": "",
    "spotify_redirect_uri": "http://127.0.0.1:8888/callback",
    "llm_provider": "openai",
    "llm_api_key": "",
    "llm_model": "",
}


def _config_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()


class JsonConfigAdapter(ConfigPort):

    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(_config_dir(), "config.json")

    def load(self) -> dict:
        cfg = dict(_DEFAULTS)
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        return cfg

    def save(self, cfg: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)

    def is_configured(self) -> bool:
        cfg = self.load()
        return bool(
            cfg.get("spotify_client_id")
            and cfg.get("spotify_client_secret")
            and cfg.get("llm_api_key")
            and cfg.get("llm_provider")
        )
