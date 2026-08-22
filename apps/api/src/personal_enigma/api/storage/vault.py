"""Private vault orchestrator — encrypted DB, blobs, audit, and Keychain secrets."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import Connection as SqlCipherConnection
from uuid import uuid4

from personal_enigma.api.storage.audit import AuditStore
from personal_enigma.api.storage.blobs import BlobStore
from personal_enigma.api.storage.decay import decay_record
from personal_enigma.api.storage.derived import (
    count_orphaned_deps,
    get_derived_record,
    init_derived_schema,
    insert_derived_record,
    list_all_derived_records,
    list_forget_audit,
    make_derived_record,
)
from personal_enigma.api.storage.forget import (
    ForgetResult,
    forget_scope_by_source_ids,
    forget_source,
)
from personal_enigma.api.storage.gc import (
    GcResult,
    gc_expired_raw_blobs,
    gc_resolved_obligations,
    load_retention_config,
)
from personal_enigma.api.storage.keychain import KeychainBackend, get_keychain_backend
from personal_enigma.api.storage.keys import KeyMaterial, load_or_create_key_material
from personal_enigma.api.storage.oauth import OAuthTokenStore
from personal_enigma.api.storage.paths import VaultPaths, default_vault_paths, ensure_vault_layout
from personal_enigma.api.storage.sensitive import (
    assert_durable_write_allowed,
)
from personal_enigma.api.storage.source_record import (
    SourceRecord,
    assert_no_oauth_tokens_in_db,
    delete_source_record,
    get_source_record,
    init_source_record_schema,
    insert_source_record,
)
from personal_enigma.api.storage.sqlcipher import (
    SqlCipherError,
    checkpoint_and_close,
    open_encrypted_db,
)
from personal_enigma.domain.retention import DerivedRecord


class VaultError(Exception):
    """Raised when vault operations fail."""


@dataclass
class PrivateVault:
    """Encrypted Private storage root — keys in Keychain, ciphertext on disk."""

    paths: VaultPaths
    keys: KeyMaterial
    _conn: SqlCipherConnection
    _blobs: BlobStore
    _audit: AuditStore
    _oauth: OAuthTokenStore
    _keychain: KeychainBackend

    @classmethod
    def open(
        cls,
        *,
        root: Path | None = None,
        keychain: KeychainBackend | None = None,
    ) -> PrivateVault:
        """Open or initialise the Private vault at ``root``."""
        paths = default_vault_paths(root=root)
        ensure_vault_layout(paths)
        chain = keychain if keychain is not None else get_keychain_backend()
        keys = load_or_create_key_material(chain, wrapped_keys_path=paths.wrapped_keys)
        conn = open_encrypted_db(paths.vault_db, keys.data_key)
        init_source_record_schema(conn)
        init_derived_schema(conn)
        assert_no_oauth_tokens_in_db(conn)
        return cls(
            paths=paths,
            keys=keys,
            _conn=conn,
            _blobs=BlobStore(paths.blobs, blob_key=keys.blob_key),
            _audit=AuditStore(paths.audit, audit_key=keys.audit_key),
            _oauth=OAuthTokenStore(chain),
            _keychain=chain,
        )

    def close(self) -> None:
        """Checkpoint WAL and close the encrypted database."""
        checkpoint_and_close(self._conn)

    def __enter__(self) -> PrivateVault:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def oauth(self) -> OAuthTokenStore:
        return self._oauth

    @property
    def audit(self) -> AuditStore:
        return self._audit

    def store_raw_source(
        self,
        *,
        source: str,
        external_id: str,
        raw_content: bytes,
        received_at: datetime | None = None,
        record_id: str | None = None,
    ) -> SourceRecord:
        """Persist PRIVATE_RAW content as encrypted blob + SourceRecord metadata."""
        blob_ref = self._blobs.put(raw_content)
        content_hash = BlobStore.content_hash(raw_content)
        record = SourceRecord(
            id=record_id or uuid4().hex,
            source=source,
            external_id=external_id,
            received_at=received_at or datetime.now(tz=UTC),
            content_hash=content_hash,
            blob_ref=blob_ref,
        )
        insert_source_record(self._conn, record)
        return record

    def read_raw_source(self, record_id: str) -> bytes:
        """Load decrypted raw source bytes for ``record_id``."""
        record = get_source_record(self._conn, record_id)
        if record is None:
            raise VaultError(f"SourceRecord not found: {record_id}")
        return self._blobs.get(record.blob_ref)

    def get_source_record(self, record_id: str) -> SourceRecord | None:
        return get_source_record(self._conn, record_id)

    def delete_source(self, record_id: str) -> None:
        """Remove blob and SourceRecord row (legacy — prefer ``forget_source``)."""
        record = delete_source_record(self._conn, record_id)
        if record is not None:
            self._blobs.delete(record.blob_ref)

    def store_derived(self, record: DerivedRecord) -> DerivedRecord:
        """Persist lineage-bound PRIVATE_DERIVED row with sensitive-inference guard."""
        assert_durable_write_allowed(
            payload=record.payload,
            retention_class=record.lineage.retention_class,
        )
        insert_derived_record(self._conn, record)
        return record

    def store_derived_new(self, **kwargs: object) -> DerivedRecord:
        """Convenience factory + store for derived records."""
        record = make_derived_record(**kwargs)  # type: ignore[arg-type]
        return self.store_derived(record)

    def get_derived_record(self, record_id: str) -> DerivedRecord | None:
        return get_derived_record(self._conn, record_id)

    def list_derived_records(self) -> list[DerivedRecord]:
        return list_all_derived_records(self._conn)

    def count_source_records(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM source_records").fetchone()
        return int(row[0]) if row else 0

    def forget_source(self, source_id: str) -> ForgetResult:
        """Graph forget — cascade derivatives, remove blob + SourceRecord."""
        return forget_source(
            self._conn,
            source_id,
            delete_blob=self._blobs.delete,
        )

    def forget_sources(self, source_ids: list[str]) -> list[ForgetResult]:
        """Scoped forget over multiple sources."""
        return forget_scope_by_source_ids(
            self._conn,
            source_ids,
            delete_blob=self._blobs.delete,
        )

    def decay_derived(self, record_id: str) -> DerivedRecord:
        """Compress active private state → pseudonymous shadow."""
        return decay_record(self._conn, record_id)

    def run_gc(self) -> GcResult:
        """TTL sweep — expire raw blobs and resolved obligations."""
        import json

        config: dict[str, object] = {}
        if self.paths.config.exists():
            loaded = json.loads(self.paths.config.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                config = loaded
        retention = load_retention_config(config)
        gc_result = gc_expired_raw_blobs(
            self._conn,
            delete_blob=self._blobs.delete,
            raw_email_blob_days=retention["raw_email_blob_days"],
        )
        resolved_count = gc_resolved_obligations(
            self._conn,
            resolved_obligation_days=retention["resolved_obligation_days"],
        )
        return GcResult(
            expired_source_ids=gc_result.expired_source_ids,
            forget_results=gc_result.forget_results,
            resolved_obligations_expired=resolved_count,
        )

    def count_orphaned_derivatives(self) -> int:
        """Return orphaned dependency rows — must be zero after forget."""
        return count_orphaned_deps(self._conn)

    def list_forget_audit(self, *, limit: int = 50) -> list[dict[str, object]]:
        return list_forget_audit(self._conn, limit=limit)

    def blob_exists(self, blob_ref: str) -> bool:
        return (self.paths.blobs / f"{blob_ref}.bin").exists()

    def touch_structured_row(self, *, label: str, detail: str) -> None:
        """Write PRIVATE_DERIVED structured state inside encrypted vault.db."""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vault_derived (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                detail TEXT NOT NULL
            )
            """
        )
        row_id = uuid4().hex
        self._conn.execute(
            "INSERT INTO vault_derived (id, label, detail) VALUES (?, ?, ?)",
            (row_id, label, detail),
        )
        self._conn.commit()

    def assert_oauth_refresh_not_in_vault_db(self) -> None:
        """Runtime assertion for tests and startup guards."""
        assert_no_oauth_tokens_in_db(self._conn)


def copy_vault_directory(source: Path, destination: Path) -> None:
    """Simulate copying only the on-disk vault tree (stolen-dir test helper)."""
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def search_directory_for_plaintext(root: Path, needles: tuple[str, ...]) -> list[tuple[Path, str]]:
    """Return (path, needle) pairs found as UTF-8 substrings in any file under ``root``."""
    hits: list[tuple[Path, str]] = []
    if not root.exists():
        return hits
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1")
        for needle in needles:
            if needle in text:
                hits.append((path, needle))
    return hits


def attempt_open_stolen_vault(copy_root: Path, data_key: bytes) -> None:
    """Try opening a copied vault.db — must fail without the correct Keychain MK."""
    db_path = copy_root / "vault.db"
    try:
        conn = open_encrypted_db(db_path, data_key)
    except SqlCipherError:
        return
    try:
        conn.execute("SELECT id FROM source_records LIMIT 1").fetchone()
        raise VaultError("Stolen vault.db opened without Keychain-derived DATA KEY")
    except SqlCipherError:
        return
    finally:
        conn.close()


def attempt_decrypt_stolen_blob(copy_root: Path, blob_ref: str, blob_key: bytes) -> None:
    """Try decrypting a copied blob — must fail without the BLOB KEY."""
    from personal_enigma.api.storage.blobs import BlobStore

    store = BlobStore(copy_root / "blobs", blob_key=blob_key)
    try:
        store.get(blob_ref)
    except Exception:
        return
    raise VaultError("Stolen blob decrypted without Keychain-derived BLOB KEY")
