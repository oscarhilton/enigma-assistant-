"""Key hierarchy and Keychain separation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from personal_enigma.api.storage.crypto import (
    CryptoError,
    WrappedKeyBundle,
    generate_key,
    unwrap_key_bundle,
    wrap_key_bundle,
)
from personal_enigma.api.storage.keychain import MemoryKeychain
from personal_enigma.api.storage.keys import load_or_create_key_material
from personal_enigma.api.storage.paths import VaultPaths, ensure_vault_layout
from personal_enigma.api.storage.vault import PrivateVault


@pytest.fixture
def memory_keychain(monkeypatch: pytest.MonkeyPatch) -> MemoryKeychain:
    monkeypatch.setenv("ENIGMA_KEYCHAIN_BACKEND", "memory")
    return MemoryKeychain()


def test_master_key_wraps_distinct_data_keys(
    tmp_path: Path,
    memory_keychain: MemoryKeychain,
) -> None:
    mk = generate_key()
    bundle = WrappedKeyBundle(
        data_key=generate_key(),
        blob_key=generate_key(),
        audit_key=generate_key(),
    )
    wrapped = wrap_key_bundle(mk, bundle)
    restored = unwrap_key_bundle(mk, wrapped)
    assert restored.data_key == bundle.data_key
    assert restored.blob_key == bundle.blob_key
    assert restored.audit_key == bundle.audit_key
    assert len({restored.data_key, restored.blob_key, restored.audit_key}) == 3


def test_wrong_master_key_cannot_unwrap_data_keys() -> None:
    mk = generate_key()
    bundle = WrappedKeyBundle(
        data_key=generate_key(),
        blob_key=generate_key(),
        audit_key=generate_key(),
    )
    wrapped = wrap_key_bundle(mk, bundle)
    with pytest.raises(CryptoError):
        unwrap_key_bundle(generate_key(), wrapped)


def test_wrapped_keys_file_is_not_plaintext_master_key(
    tmp_path: Path,
    memory_keychain: MemoryKeychain,
) -> None:
    paths = VaultPaths(root=tmp_path / "private")
    ensure_vault_layout(paths)
    material = load_or_create_key_material(memory_keychain, wrapped_keys_path=paths.wrapped_keys)
    raw = paths.wrapped_keys.read_bytes()
    assert material.master_key not in raw
    assert material.data_key not in raw
    assert material.blob_key not in raw
    assert material.audit_key not in raw


def test_vault_directory_never_contains_master_key(
    tmp_path: Path,
    memory_keychain: MemoryKeychain,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    monkeypatch.setenv("ENIGMA_PRIVATE_STORAGE_ROOT", str(root))
    with PrivateVault.open(root=root, keychain=memory_keychain) as vault:
        mk = vault.keys.master_key

    for path in root.rglob("*"):
        if path.is_file():
            assert mk not in path.read_bytes()
