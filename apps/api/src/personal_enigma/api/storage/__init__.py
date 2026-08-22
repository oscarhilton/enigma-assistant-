"""Private vault — encrypted structured state, blob store, and Keychain secrets."""

from personal_enigma.api.storage.classification import DataClass
from personal_enigma.api.storage.oauth import OAuthTokenStore
from personal_enigma.api.storage.paths import (
    VAULT_DB_FILENAME,
    VaultPaths,
    default_vault_paths,
    ensure_vault_layout,
)
from personal_enigma.api.storage.source_record import SourceRecord
from personal_enigma.api.storage.vault import PrivateVault, VaultError

__all__ = [
    "DataClass",
    "OAuthTokenStore",
    "PrivateVault",
    "SourceRecord",
    "VAULT_DB_FILENAME",
    "VaultError",
    "VaultPaths",
    "default_vault_paths",
    "ensure_vault_layout",
]
