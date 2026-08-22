"""Encryption round-trip and WAL sidecar tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from personal_enigma.api.storage.crypto import decrypt_blob, encrypt_blob, generate_key
from personal_enigma.api.storage.keychain import MemoryKeychain
from personal_enigma.api.storage.paths import VaultPaths
from personal_enigma.api.storage.sqlcipher import SqlCipherError, open_encrypted_db
from personal_enigma.api.storage.vault import PrivateVault, search_directory_for_plaintext


@pytest.fixture
def memory_keychain(monkeypatch: pytest.MonkeyPatch) -> MemoryKeychain:
    monkeypatch.setenv("ENIGMA_KEYCHAIN_BACKEND", "memory")
    return MemoryKeychain()


def test_blob_aead_roundtrip() -> None:
    key = generate_key()
    plaintext = b"raw email mime body with secrets"
    envelope = encrypt_blob(key, plaintext)
    assert plaintext not in envelope
    assert decrypt_blob(key, envelope) == plaintext


def test_source_record_blob_roundtrip(
    tmp_path: Path,
    memory_keychain: MemoryKeychain,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    monkeypatch.setenv("ENIGMA_PRIVATE_STORAGE_ROOT", str(root))
    body = b"Subject: dinner\n\nCan we meet Tuesday?"
    with PrivateVault.open(root=root, keychain=memory_keychain) as vault:
        record = vault.store_raw_source(
            source="gmail",
            external_id="msg-100",
            raw_content=body,
            record_id="src-100",
        )
        assert vault.read_raw_source("src-100") == body
        blob_path = root / "blobs" / f"{record.blob_ref}.bin"
        assert blob_path.exists()
        assert body not in blob_path.read_bytes()


def test_sqlcipher_rejects_wrong_data_key(tmp_path: Path) -> None:
    db_path = tmp_path / "vault.db"
    real_key = generate_key()
    conn = open_encrypted_db(db_path, real_key)
    conn.execute("CREATE TABLE t (x TEXT)")
    conn.execute("INSERT INTO t VALUES ('secret row')")
    conn.commit()
    conn.close()

    with pytest.raises(SqlCipherError):
        bad = open_encrypted_db(db_path, generate_key())
        bad.close()


def test_wal_sidecars_do_not_contain_plaintext_sentinel(
    tmp_path: Path,
    memory_keychain: MemoryKeychain,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    monkeypatch.setenv("ENIGMA_PRIVATE_STORAGE_ROOT", str(root))
    sentinel = "WAL_PLAINTEXT_SENTINEL_XYZ"
    vault = PrivateVault.open(root=root, keychain=memory_keychain)
    try:
        for i in range(40):
            vault.touch_structured_row(label=f"row-{i}", detail=sentinel)
        vault.store_raw_source(
            source="gmail",
            external_id=f"msg-{sentinel}",
            raw_content=sentinel.encode("utf-8"),
        )
        paths = VaultPaths(root=root)
        sidecars = [p for p in paths.sidecar_paths() if p.exists()]
        assert sidecars, "Expected WAL sidecar files while vault session is open"
        hits = search_directory_for_plaintext(root, (sentinel,))
        assert hits == [], f"Sentinel found in vault files: {hits}"
    finally:
        vault.close()


def test_delete_source_removes_blob(
    tmp_path: Path,
    memory_keychain: MemoryKeychain,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    monkeypatch.setenv("ENIGMA_PRIVATE_STORAGE_ROOT", str(root))
    with PrivateVault.open(root=root, keychain=memory_keychain) as vault:
        record = vault.store_raw_source(
            source="gmail",
            external_id="msg-del",
            raw_content=b"delete me",
            record_id="src-del",
        )
        blob_path = root / "blobs" / f"{record.blob_ref}.bin"
        assert blob_path.exists()
        vault.delete_source("src-del")
        assert not blob_path.exists()
        assert vault.get_source_record("src-del") is None

def test_restore_raw_source_deletes_prior_blob(
    tmp_path: Path,
    memory_keychain: MemoryKeychain,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    monkeypatch.setenv("ENIGMA_PRIVATE_STORAGE_ROOT", str(root))
    with PrivateVault.open(root=root, keychain=memory_keychain) as vault:
        first = vault.store_raw_source(
            source="gmail",
            external_id="msg-upsert",
            raw_content=b"version-one",
            record_id="src-upsert",
        )
        old_blob = root / "blobs" / f"{first.blob_ref}.bin"
        assert old_blob.exists()

        second = vault.store_raw_source(
            source="gmail",
            external_id="msg-upsert",
            raw_content=b"version-two",
            record_id="src-upsert",
        )
        assert second.blob_ref != first.blob_ref
        assert vault.read_raw_source("src-upsert") == b"version-two"
        assert not old_blob.exists()
        assert vault.blob_exists(second.blob_ref)

