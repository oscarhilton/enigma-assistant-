"""OAuth refresh token storage — Keychain ONLY (SECRET class)."""

from __future__ import annotations

from personal_enigma.api.storage.keychain import KeychainBackend, oauth_account


class OAuthTokenStore:
    """Persist provider OAuth refresh tokens outside the vault directory."""

    def __init__(self, keychain: KeychainBackend) -> None:
        self._keychain = keychain

    def set_refresh_token(self, provider: str, token: str) -> None:
        """Store a refresh token in Keychain — never in vault.db."""
        account = oauth_account(provider, kind="refresh")
        self._keychain.set_secret(account, token.encode("utf-8"))

    def get_refresh_token(self, provider: str) -> str | None:
        account = oauth_account(provider, kind="refresh")
        raw = self._keychain.get_secret(account)
        if raw is None:
            return None
        return raw.decode("utf-8")

    def delete_refresh_token(self, provider: str) -> None:
        account = oauth_account(provider, kind="refresh")
        self._keychain.delete_secret(account)
