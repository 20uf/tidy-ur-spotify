"""JSON file-based config adapter."""

import json
import os
import sys
from typing import Optional, Protocol

from src.adapters.config.secret_store import KeyringSecretStore
from src.domain.ports import ConfigPort

_DEFAULTS = {
    "spotify_client_id": "",
    "spotify_client_secret": "",
    "spotify_redirect_uri": "http://127.0.0.1:8888/callback",
    "llm_provider": "openai",
    "llm_api_key": "",
    "llm_model": "",
    "simulation_mode": False,
    "legal_acknowledged": False,
}
_SECRET_FIELDS = ("spotify_client_secret", "llm_api_key")


def _config_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()


class SecretStoreProtocol(Protocol):
    def get(self, key: str) -> Optional[str]:
        ...

    def set(self, key: str, value: str) -> bool:
        ...


class JsonConfigAdapter(ConfigPort):

    def __init__(self, path: str | None = None, secret_store: SecretStoreProtocol | None = None):
        self.path = path or os.path.join(_config_dir(), "config.json")
        self.secret_store = secret_store or KeyringSecretStore()

    def load(self) -> dict:
        cfg = dict(_DEFAULTS)
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))

        for field in _SECRET_FIELDS:
            secret = self.secret_store.get(field)
            if secret:
                cfg[field] = secret

        return cfg

    def save(self, cfg: dict) -> None:
        persisted_cfg = dict(cfg)
        for field in _SECRET_FIELDS:
            value = str(cfg.get(field, "") or "")
            stored = self.secret_store.set(field, value)
            # Keep plaintext only if the keychain backend is unavailable.
            persisted_cfg[field] = "" if stored else value

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(persisted_cfg, f, indent=2)

    def is_configured(self) -> bool:
        cfg = self.load()
        return bool(
            cfg.get("spotify_client_id")
            and cfg.get("spotify_client_secret")
            and cfg.get("llm_api_key")
            and cfg.get("llm_provider")
        )
