"""SQLCipher connection helpers for encrypted ``vault.db``."""

from __future__ import annotations

from pathlib import Path
from sqlite3 import Connection as SqlCipherConnection

import sqlcipher3.dbapi2 as sqlcipher


class SqlCipherError(Exception):
    """Raised when the encrypted database cannot be opened."""


def open_encrypted_db(path: Path, data_key: bytes) -> SqlCipherConnection:
    """Open ``vault.db`` with the DATA KEY (SQLCipher page encryption)."""
    if len(data_key) != 32:
        raise SqlCipherError("DATA KEY must be 32 bytes")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlcipher.connect(str(path))  # type: ignore[attr-defined]
    try:
        hex_key = data_key.hex()
        conn.execute(f"PRAGMA key = \"x'{hex_key}'\"")
        conn.execute("PRAGMA cipher_page_size = 4096")
        conn.execute("PRAGMA kdf_iter = 256000")
        _verify_key(conn)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
    except sqlcipher.DatabaseError as exc:  # type: ignore[attr-defined]
        conn.close()
        raise SqlCipherError("Incorrect DATA KEY or corrupt vault.db") from exc
    return conn


def _verify_key(conn: SqlCipherConnection) -> None:
    """Fail fast when the DATA KEY does not decrypt the database."""
    conn.execute("SELECT count(*) FROM sqlite_master").fetchone()


def open_encrypted_db_readonly(path: Path, data_key: bytes) -> SqlCipherConnection:
    """Open an existing encrypted database (used by stolen-dir negative tests)."""
    if not path.exists():
        raise SqlCipherError(f"vault.db not found: {path}")
    return open_encrypted_db(path, data_key)


def checkpoint_and_close(conn: SqlCipherConnection) -> None:
    """Checkpoint WAL pages into the main DB file, then close."""
    try:
        conn.execute("PRAGMA wal_checkpoint(FULL)")
    finally:
        conn.close()
