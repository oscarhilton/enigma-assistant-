"""OS Keychain adapter for SECRET material (ADR-022).

Production uses ``keyring`` (macOS Keychain on Darwin). Tests and CI set
``ENIGMA_KEYCHAIN_BACKEND=memory`` for an isolated in-process store that never
writes secrets to disk inside the vault directory.
"""

from __future__ import annotations

import base64
import os
from typing import Protocol

ENV_KEYCHAIN_BACKEND = "ENIGMA_KEYCHAIN_BACKEND"
KEYCHAIN_BACKEND_MEMORY = "memory"
KEYCHAIN_BACKEND_KEYRING = "keyring"

SERVICE_NAME = "personal-enigma-private"

ACCOUNT_MASTER_KEY = "master-key"
ACCOUNT_DEVICE_IDENTITY = "device-identity-key"
ACCOUNT_OAUTH_PREFIX = "oauth:"


class KeychainBackend(Protocol):
    """Minimal secret store — Keychain or test double."""

    def get_secret(self, account: str) -> bytes | None: ...

    def set_secret(self, account: str, value: bytes) -> None: ...

    def delete_secret(self, account: str) -> None: ...

    def clear(self) -> None: ...


class MemoryKeychain:
    """In-process secret store for tests — never persists to vault files."""

    def __init__(self) -> None:
        self._values: dict[str, bytes] = {}

    def get_secret(self, account: str) -> bytes | None:
        return self._values.get(account)

    def set_secret(self, account: str, value: bytes) -> None:
        self._values[account] = value

    def delete_secret(self, account: str) -> None:
        self._values.pop(account, None)

    def clear(self) -> None:
        self._values.clear()


class KeyringBackend:
    """Persist secrets via the platform keyring (macOS Keychain on Darwin)."""

    def get_secret(self, account: str) -> bytes | None:
        import keyring

        raw = keyring.get_password(SERVICE_NAME, account)
        if raw is None:
            return None
        return base64.b64decode(raw.encode("ascii"))

    def set_secret(self, account: str, value: bytes) -> None:
        import keyring

        encoded = base64.b64encode(value).decode("ascii")
        keyring.set_password(SERVICE_NAME, account, encoded)

    def delete_secret(self, account: str) -> None:
        import keyring

        try:
            keyring.delete_password(SERVICE_NAME, account)
        except Exception:
            pass

    def clear(self) -> None:
        raise RuntimeError("KeyringBackend.clear() is not supported in production")


_memory_singleton: MemoryKeychain | None = None


def get_keychain_backend() -> KeychainBackend:
    """Return the configured keychain backend."""
    backend = os.environ.get(ENV_KEYCHAIN_BACKEND, KEYCHAIN_BACKEND_KEYRING).strip().lower()
    if backend == KEYCHAIN_BACKEND_MEMORY:
        global _memory_singleton
        if _memory_singleton is None:
            _memory_singleton = MemoryKeychain()
        return _memory_singleton
    if backend == KEYCHAIN_BACKEND_KEYRING:
        return KeyringBackend()
    raise ValueError(
        f"Unknown {ENV_KEYCHAIN_BACKEND}={backend!r}; "
        f"expected {KEYCHAIN_BACKEND_MEMORY!r} or {KEYCHAIN_BACKEND_KEYRING!r}"
    )


def oauth_account(provider: str, *, kind: str = "refresh") -> str:
    """Keychain account name for an OAuth credential."""
    return f"{ACCOUNT_OAUTH_PREFIX}{provider}:{kind}"
