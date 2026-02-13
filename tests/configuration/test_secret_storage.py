"""Configuration security behavior for local secret storage."""

import json

from src.adapters.config.json_config_adapter import JsonConfigAdapter


class FakeSecretStore:
    def __init__(self, available: bool = True):
        self.available = available
        self.data: dict[str, str] = {}

    def get(self, key: str):
        return self.data.get(key)

    def set(self, key: str, value: str) -> bool:
        if not self.available:
            return False
        if value:
            self.data[key] = value
        else:
            self.data.pop(key, None)
        return True


def test_sensitive_credentials_go_to_secret_store_when_available(tmp_path):
    secret_store = FakeSecretStore(available=True)
    config_path = tmp_path / "config.json"
    adapter = JsonConfigAdapter(path=str(config_path), secret_store=secret_store)

    adapter.save({
        "spotify_client_id": "client-id",
        "spotify_client_secret": "spotify-secret",
        "llm_provider": "openai",
        "llm_api_key": "sk-test",
    })

    on_disk = json.loads(config_path.read_text(encoding="utf-8"))
    loaded = adapter.load()

    assert on_disk["spotify_client_secret"] == ""
    assert on_disk["llm_api_key"] == ""
    assert secret_store.data["spotify_client_secret"] == "spotify-secret"
    assert secret_store.data["llm_api_key"] == "sk-test"
    assert loaded["spotify_client_secret"] == "spotify-secret"
    assert loaded["llm_api_key"] == "sk-test"


def test_sensitive_credentials_fallback_to_plaintext_if_secret_store_unavailable(tmp_path):
    secret_store = FakeSecretStore(available=False)
    config_path = tmp_path / "config.json"
    adapter = JsonConfigAdapter(path=str(config_path), secret_store=secret_store)

    adapter.save({
        "spotify_client_id": "client-id",
        "spotify_client_secret": "spotify-secret",
        "llm_provider": "openai",
        "llm_api_key": "sk-test",
    })

    on_disk = json.loads(config_path.read_text(encoding="utf-8"))
    loaded = adapter.load()

    assert on_disk["spotify_client_secret"] == "spotify-secret"
    assert on_disk["llm_api_key"] == "sk-test"
    assert loaded["spotify_client_secret"] == "spotify-secret"
    assert loaded["llm_api_key"] == "sk-test"
