"""Secret storage helpers for local credentials."""

from __future__ import annotations

from typing import Optional

try:
    import keyring
    from keyring.errors import KeyringError
except Exception:  # pragma: no cover - fallback when dependency is unavailable
    keyring = None

    class KeyringError(Exception):
        pass


DEFAULT_SERVICE_NAME = "tidy-ur-spotify"


class KeyringSecretStore:
    """Store and retrieve secrets from the OS keychain."""

    def __init__(self, service_name: str = DEFAULT_SERVICE_NAME):
        self.service_name = service_name

    def get(self, key: str) -> Optional[str]:
        if keyring is None:
            return None
        try:
            return keyring.get_password(self.service_name, key)
        except KeyringError:
            return None

    def set(self, key: str, value: str) -> bool:
        if keyring is None:
            return False
        try:
            if value:
                keyring.set_password(self.service_name, key, value)
            else:
                self.delete(key)
            return True
        except KeyringError:
            return False

    def delete(self, key: str) -> bool:
        if keyring is None:
            return False
        try:
            keyring.delete_password(self.service_name, key)
            return True
        except KeyringError:
            return False
