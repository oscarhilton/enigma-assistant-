"""Centrepiece stolen-directory test for SEC-01 (ADR-022)."""

from __future__ import annotations

from pathlib import Path

import pytest

from personal_enigma.api.storage.blobs import BlobStore, BlobStoreError
from personal_enigma.api.storage.crypto import generate_key
from personal_enigma.api.storage.keychain import MemoryKeychain
from personal_enigma.api.storage.sqlcipher import SqlCipherError, open_encrypted_db
from personal_enigma.api.storage.vault import (
    PrivateVault,
    attempt_decrypt_stolen_blob,
    attempt_open_stolen_vault,
    copy_vault_directory,
    search_directory_for_plaintext,
)
from personal_enigma.fixtures.alex_security_canaries import ALL_CANARY_SENTINELS

SENTINEL_SUBJECT = "SENTINEL_SUBJECT_ULTRA_SECRET_42"
SENTINEL_BODY = (
    "Dear Oscar, please wire funds immediately. "
    "Reply to oscar.hilts@example.com before Friday."
)
SENTINEL_NAME = "Oscar Hilts"
SENTINEL_EMAIL = "oscar.hilts@example.com"
OAUTH_SENTINEL = "ya29.SENTINEL_OAUTH_REFRESH_TOKEN_DO_NOT_LEAK"


@pytest.fixture
def memory_keychain(monkeypatch: pytest.MonkeyPatch) -> MemoryKeychain:
    monkeypatch.setenv("ENIGMA_KEYCHAIN_BACKEND", "memory")
    chain = MemoryKeychain()
    yield chain
    chain.clear()


@pytest.fixture
def vault_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "private"
    monkeypatch.setenv("ENIGMA_PRIVATE_STORAGE_ROOT", str(root))
    return root


def test_stolen_directory_reveals_no_plaintext(
    vault_root: Path,
    memory_keychain: MemoryKeychain,
) -> None:
    """Copying ``private/`` without Keychain must yield zero recoverable plaintext."""
    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        vault.oauth.set_refresh_token("gmail", OAUTH_SENTINEL)
        record = vault.store_raw_source(
            source="gmail",
            external_id="msg-sentinel-001",
            raw_content=SENTINEL_BODY.encode("utf-8"),
        )
        vault.touch_structured_row(label=SENTINEL_NAME, detail=SENTINEL_SUBJECT)
        vault.audit.append_record(
            event_type="egress_blocked",
            payload_hash="abc123",
            field_summary={"record_id": record.id, "reason": "disabled"},
        )
        vault.assert_oauth_refresh_not_in_vault_db()
        blob_ref = record.blob_ref

    stolen_root = vault_root.parent / "stolen-copy"
    copy_vault_directory(vault_root, stolen_root)

    needles = (
        SENTINEL_SUBJECT,
        SENTINEL_BODY,
        SENTINEL_NAME,
        SENTINEL_EMAIL,
        OAUTH_SENTINEL,
    )
    hits = search_directory_for_plaintext(stolen_root, needles)
    assert hits == [], f"Plaintext leaked in stolen copy: {hits}"

    wrong_data_key = generate_key()
    wrong_blob_key = generate_key()
    attempt_open_stolen_vault(stolen_root, wrong_data_key)
    attempt_decrypt_stolen_blob(stolen_root, blob_ref, wrong_blob_key)

    wal_shm = (
        stolen_root / "vault.db-wal",
        stolen_root / "vault.db-shm",
    )
    for sidecar in wal_shm:
        if sidecar.exists():
            sidecar_hits = search_directory_for_plaintext(sidecar.parent, needles)
            sidecar_specific = [hit for hit in sidecar_hits if hit[0] == sidecar]
            assert sidecar_specific == [], f"Plaintext in {sidecar.name}: {sidecar_specific}"


def test_stolen_directory_reveals_no_canary_sentinels(
    vault_root: Path,
    memory_keychain: MemoryKeychain,
) -> None:
    """SEC-07 / SEC-01 — canary sentinels must not appear in stolen private/ copy."""
    canary_body = "\n".join(ALL_CANARY_SENTINELS[:3])
    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        vault.store_raw_source(
            source="note",
            external_id="canary-sentinel-pack",
            raw_content=canary_body.encode("utf-8"),
        )

    stolen_root = vault_root.parent / "stolen-canary-copy"
    copy_vault_directory(vault_root, stolen_root)

    hits = search_directory_for_plaintext(stolen_root, ALL_CANARY_SENTINELS)
    assert hits == [], f"Canary sentinels leaked in stolen directory: {hits[:5]}"


def test_oauth_refresh_token_not_in_vault_files(
    vault_root: Path,
    memory_keychain: MemoryKeychain,
) -> None:
    token = "ya29.test_refresh_only_in_keychain"
    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        vault.oauth.set_refresh_token("gmail", token)
        vault.assert_oauth_refresh_not_in_vault_db()

    hits = search_directory_for_plaintext(vault_root, (token,))
    assert hits == []

    assert memory_keychain.get_secret("oauth:gmail:refresh") == token.encode("utf-8")


def test_key_classes_are_independent(
    vault_root: Path,
    memory_keychain: MemoryKeychain,
) -> None:
    """Possessing one wrapped key must not unlock every persistence tier."""
    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        record = vault.store_raw_source(
            source="gmail",
            external_id="msg-tier-test",
            raw_content=b"tier isolation body",
        )
        blob_ref = record.blob_ref
        data_key = vault.keys.data_key
        blob_key = vault.keys.blob_key

    stolen_root = vault_root.parent / "stolen-tier"
    copy_vault_directory(vault_root, stolen_root)

    # DATA KEY alone opens structured DB but cannot decrypt blobs without BLOB KEY.
    conn = open_encrypted_db(stolen_root / "vault.db", data_key)
    row = conn.execute("SELECT blob_ref FROM source_records LIMIT 1").fetchone()
    conn.close()
    assert row is not None
    with pytest.raises(BlobStoreError):
        BlobStore(stolen_root / "blobs", blob_key=generate_key()).get(blob_ref)

    # BLOB KEY alone cannot open SQLCipher DB.
    with pytest.raises(SqlCipherError):
        bad = open_encrypted_db(stolen_root / "vault.db", generate_key())
        bad.execute("SELECT count(*) FROM sqlite_master").fetchone()
        bad.close()

    # BLOB KEY alone still fails without the encrypted envelope bytes — wrong ref.
    with pytest.raises(BlobStoreError):
        BlobStore(stolen_root / "blobs", blob_key=blob_key).get("nonexistent-ref")
