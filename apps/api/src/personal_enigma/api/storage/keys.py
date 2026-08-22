"""Key hierarchy — master key in Keychain wraps DATA / BLOB / AUDIT keys."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from personal_enigma.api.storage.crypto import (
    WrappedKeyBundle,
    generate_key,
    unwrap_key_bundle,
    wrap_key_bundle,
)
from personal_enigma.api.storage.keychain import (
    ACCOUNT_DEVICE_IDENTITY,
    ACCOUNT_MASTER_KEY,
    KeychainBackend,
)


class KeyHierarchyError(Exception):
    """Raised when key material cannot be loaded or created."""


class VaultKeyRecoveryError(KeyHierarchyError):
    """Vault exists on disk but Keychain master key is missing."""


@dataclass(frozen=True, slots=True)
class KeyMaterial:
    """Runtime key material for an open vault session."""

    master_key: bytes
    data_key: bytes
    blob_key: bytes
    audit_key: bytes


def _load_wrapped_keys(path: Path, master_key: bytes) -> WrappedKeyBundle:
    if not path.exists():
        raise KeyHierarchyError(f"Wrapped keys file missing: {path}")
    try:
        return unwrap_key_bundle(master_key, path.read_bytes())
    except Exception as exc:
        raise KeyHierarchyError("Failed to unwrap data keys with master key") from exc


def _save_wrapped_keys(path: Path, master_key: bytes, bundle: WrappedKeyBundle) -> None:
    path.write_bytes(wrap_key_bundle(master_key, bundle))


def _vault_artifacts_present(wrapped_keys_path: Path) -> bool:
    """True when on-disk vault state implies keys must not be re-bootstrapped."""
    root = wrapped_keys_path.parent
    if wrapped_keys_path.exists():
        return True
    if (root / "vault.db").exists():
        return True
    return False


def load_or_create_key_material(
    keychain: KeychainBackend,
    *,
    wrapped_keys_path: Path,
) -> KeyMaterial:
    """Load or bootstrap MK + wrapped DATA/BLOB/AUDIT keys.

    The master key lives in Keychain only. Wrapped data keys live on disk as
    ciphertext — useless without the master key.
    """
    master_key = keychain.get_secret(ACCOUNT_MASTER_KEY)
    if master_key is None:
        if _vault_artifacts_present(wrapped_keys_path):
            raise VaultKeyRecoveryError(
                "Vault key material exists on disk but the Keychain master key is "
                "missing; restore Keychain backup instead of re-bootstrapping new keys."
            )
        master_key = generate_key()
        keychain.set_secret(ACCOUNT_MASTER_KEY, master_key)
        bundle = WrappedKeyBundle(
            data_key=generate_key(),
            blob_key=generate_key(),
            audit_key=generate_key(),
        )
        _save_wrapped_keys(wrapped_keys_path, master_key, bundle)
    else:
        bundle = _load_wrapped_keys(wrapped_keys_path, master_key)

    if keychain.get_secret(ACCOUNT_DEVICE_IDENTITY) is None:
        keychain.set_secret(ACCOUNT_DEVICE_IDENTITY, generate_key())

    return KeyMaterial(
        master_key=master_key,
        data_key=bundle.data_key,
        blob_key=bundle.blob_key,
        audit_key=bundle.audit_key,
    )
