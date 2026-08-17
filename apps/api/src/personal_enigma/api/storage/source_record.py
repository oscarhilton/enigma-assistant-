"""SourceRecord schema — structured metadata with blob reference only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from sqlite3 import Connection as SqlCipherConnection


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """Canonical ingest metadata; raw body lives in encrypted ``blobs/``."""

    id: str
    source: str
    external_id: str
    received_at: datetime
    content_hash: str
    blob_ref: str


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS source_records (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    received_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    blob_ref TEXT NOT NULL,
    UNIQUE(source, external_id)
);
CREATE INDEX IF NOT EXISTS ix_source_records_source ON source_records(source);
CREATE INDEX IF NOT EXISTS ix_source_records_blob_ref ON source_records(blob_ref);
"""


def init_source_record_schema(conn: SqlCipherConnection) -> None:
    """Create SourceRecord table if missing."""
    conn.executescript(_SCHEMA_SQL)
    conn.commit()


def insert_source_record(conn: SqlCipherConnection, record: SourceRecord) -> None:
    conn.execute(
        """
        INSERT INTO source_records
            (id, source, external_id, received_at, content_hash, blob_ref)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            source = excluded.source,
            external_id = excluded.external_id,
            received_at = excluded.received_at,
            content_hash = excluded.content_hash,
            blob_ref = excluded.blob_ref
        """,
        (
            record.id,
            record.source,
            record.external_id,
            record.received_at.isoformat(),
            record.content_hash,
            record.blob_ref,
        ),
    )
    conn.commit()


def get_source_record(conn: SqlCipherConnection, record_id: str) -> SourceRecord | None:
    row = conn.execute(
        "SELECT id, source, external_id, received_at, content_hash, blob_ref "
        "FROM source_records WHERE id = ?",
        (record_id,),
    ).fetchone()
    if row is None:
        return None
    return SourceRecord(
        id=row[0],
        source=row[1],
        external_id=row[2],
        received_at=datetime.fromisoformat(row[3]),
        content_hash=row[4],
        blob_ref=row[5],
    )


def delete_source_record(conn: SqlCipherConnection, record_id: str) -> SourceRecord | None:
    existing = get_source_record(conn, record_id)
    if existing is None:
        return None
    conn.execute("DELETE FROM source_records WHERE id = ?", (record_id,))
    conn.commit()
    return existing


def assert_no_oauth_tokens_in_db(conn: SqlCipherConnection) -> None:
    """Runtime guard — OAuth refresh tokens must never appear in vault.db."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'index')"
    ).fetchall()
    names = {row[0].lower() for row in rows}
    forbidden = {"oauth_tokens", "oauth_refresh_tokens", "secrets", "credentials"}
    leaked = names.intersection(forbidden)
    if leaked:
        raise RuntimeError(f"Forbidden OAuth storage tables present: {sorted(leaked)}")

    for table_name, in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall():
        columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        col_names = {col[1].lower() for col in columns}
        forbidden_cols = {
            "oauth_refresh_token",
            "refresh_token",
            "oauth_token",
            "access_token",
        }
        bad = col_names.intersection(forbidden_cols)
        if bad:
            raise RuntimeError(
                f"Forbidden OAuth column(s) on {table_name}: {sorted(bad)}"
            )
