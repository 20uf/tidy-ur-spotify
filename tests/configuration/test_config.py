"""Bounded context: Configuration

Business rules for first-launch detection and config persistence.
"""

import json
import os

import pytest

from src.adapters.config.json_config_adapter import JsonConfigAdapter


class TestFirstLaunchDetection:
    """The app detects whether configuration exists to show the setup wizard."""

    def test_unconfigured_when_no_file_exists(self, tmp_path):
        adapter = JsonConfigAdapter(path=str(tmp_path / "config.json"))
        assert not adapter.is_configured()

    def test_unconfigured_when_keys_are_empty(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        with open(config_path, "w") as f:
            json.dump({"spotify_client_id": "", "llm_api_key": ""}, f)
        adapter = JsonConfigAdapter(path=config_path)
        assert not adapter.is_configured()

    def test_configured_after_setup_wizard(self, tmp_path):
        adapter = JsonConfigAdapter(path=str(tmp_path / "config.json"))
        adapter.save({
            "spotify_client_id": "abc123",
            "spotify_client_secret": "secret",
            "llm_provider": "openai",
            "llm_api_key": "sk-test",
        })
        assert adapter.is_configured()


class TestConfigPersistence:
    """Configuration is saved to disk and survives app restarts."""

    def test_save_and_load_round_trip(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        adapter = JsonConfigAdapter(path=config_path)

        adapter.save({
            "spotify_client_id": "abc123",
            "spotify_client_secret": "secret",
            "llm_provider": "openai",
            "llm_api_key": "sk-test",
            "llm_model": "gpt-4o-mini",
        })

        loaded = adapter.load()
        assert loaded["spotify_client_id"] == "abc123"
        assert loaded["llm_provider"] == "openai"
        assert loaded["llm_api_key"] == "sk-test"

    def test_load_returns_defaults_when_no_file(self, tmp_path):
        adapter = JsonConfigAdapter(path=str(tmp_path / "config.json"))
        loaded = adapter.load()

        assert loaded["spotify_redirect_uri"] == "http://127.0.0.1:8888/callback"
        assert loaded["llm_provider"] == "openai"

    def test_config_file_is_written_to_disk(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        adapter = JsonConfigAdapter(path=config_path)
        adapter.save({"spotify_client_id": "test"})

        assert os.path.exists(config_path)
        with open(config_path, "r") as f:
            data = json.load(f)
        assert data["spotify_client_id"] == "test"
