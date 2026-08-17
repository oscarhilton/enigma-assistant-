"""PRIVATE_DERIVED storage with lineage metadata (SEC-06)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from sqlite3 import Connection as SqlCipherConnection
from uuid import uuid4

from personal_enigma.domain.retention import (
    DerivedRecord,
    DerivedRecordType,
    LineageMetadata,
    MemoryLayer,
    RetentionClass,
    RetentionPurpose,
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS derived_records (
    id TEXT PRIMARY KEY,
    record_type TEXT NOT NULL,
    memory_layer TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    purpose TEXT NOT NULL,
    retention_class TEXT NOT NULL,
    expires_after_resolution TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS derived_source_deps (
    derived_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    PRIMARY KEY (derived_id, source_id),
    FOREIGN KEY (derived_id) REFERENCES derived_records(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_derived_source_deps_source
    ON derived_source_deps(source_id);
CREATE TABLE IF NOT EXISTS forget_audit (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    deleted_derived_ids_json TEXT NOT NULL,
    surviving_derived_ids_json TEXT NOT NULL,
    blob_ref TEXT,
    forgotten_at TEXT NOT NULL
);
"""


def init_derived_schema(conn: SqlCipherConnection) -> None:
    """Create derived-record tables if missing."""
    conn.executescript(_SCHEMA_SQL)
    conn.commit()


def insert_derived_record(conn: SqlCipherConnection, record: DerivedRecord) -> None:
    """Persist a lineage-bound derived row and its source dependencies."""
    conn.execute(
        """
        INSERT INTO derived_records (
            id, record_type, memory_layer, payload_json,
            purpose, retention_class, expires_after_resolution,
            confidence, created_at, resolved_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            record_type = excluded.record_type,
            memory_layer = excluded.memory_layer,
            payload_json = excluded.payload_json,
            purpose = excluded.purpose,
            retention_class = excluded.retention_class,
            expires_after_resolution = excluded.expires_after_resolution,
            confidence = excluded.confidence,
            created_at = excluded.created_at,
            resolved_at = excluded.resolved_at
        """,
        (
            record.id,
            record.record_type.value,
            record.memory_layer.value,
            json.dumps(record.payload, sort_keys=True),
            record.lineage.purpose.value,
            record.lineage.retention_class.value,
            record.lineage.expires_after_resolution,
            record.confidence,
            record.created_at.isoformat(),
            record.resolved_at.isoformat() if record.resolved_at else None,
        ),
    )
    conn.execute(
        "DELETE FROM derived_source_deps WHERE derived_id = ?",
        (record.id,),
    )
    for source_id in record.lineage.derived_from:
        conn.execute(
            "INSERT INTO derived_source_deps (derived_id, source_id) VALUES (?, ?)",
            (record.id, source_id),
        )
    conn.commit()


def get_derived_record(conn: SqlCipherConnection, record_id: str) -> DerivedRecord | None:
    row = conn.execute(
        """
        SELECT id, record_type, memory_layer, payload_json,
               purpose, retention_class, expires_after_resolution,
               confidence, created_at, resolved_at
        FROM derived_records WHERE id = ?
        """,
        (record_id,),
    ).fetchone()
    if row is None:
        return None
    deps = _source_deps_for(conn, row[0])
    return _row_to_record(row, deps)


def list_derived_records_for_source(
    conn: SqlCipherConnection, source_id: str
) -> list[DerivedRecord]:
    rows = conn.execute(
        """
        SELECT dr.id, dr.record_type, dr.memory_layer, dr.payload_json,
               dr.purpose, dr.retention_class, dr.expires_after_resolution,
               dr.confidence, dr.created_at, dr.resolved_at
        FROM derived_records dr
        JOIN derived_source_deps dsd ON dsd.derived_id = dr.id
        WHERE dsd.source_id = ?
        ORDER BY dr.created_at
        """,
        (source_id,),
    ).fetchall()
    return [_row_to_record(row, _source_deps_for(conn, row[0])) for row in rows]


def list_all_derived_records(conn: SqlCipherConnection) -> list[DerivedRecord]:
    rows = conn.execute(
        """
        SELECT id, record_type, memory_layer, payload_json,
               purpose, retention_class, expires_after_resolution,
               confidence, created_at, resolved_at
        FROM derived_records ORDER BY created_at
        """
    ).fetchall()
    return [_row_to_record(row, _source_deps_for(conn, row[0])) for row in rows]


def delete_derived_record(conn: SqlCipherConnection, record_id: str) -> bool:
    existing = conn.execute(
        "SELECT id FROM derived_records WHERE id = ?", (record_id,)
    ).fetchone()
    if existing is None:
        return False
    conn.execute("DELETE FROM derived_records WHERE id = ?", (record_id,))
    conn.commit()
    return True


def count_orphaned_deps(conn: SqlCipherConnection) -> int:
    """Return derived_source_deps rows whose derived_id no longer exists."""
    row = conn.execute(
        """
        SELECT COUNT(*) FROM derived_source_deps dsd
        LEFT JOIN derived_records dr ON dr.id = dsd.derived_id
        WHERE dr.id IS NULL
        """
    ).fetchone()
    return int(row[0]) if row else 0


def append_forget_audit(
    conn: SqlCipherConnection,
    *,
    source_id: str,
    deleted_derived_ids: list[str],
    surviving_derived_ids: list[str],
    blob_ref: str | None,
) -> str:
    audit_id = uuid4().hex
    conn.execute(
        """
        INSERT INTO forget_audit
            (id, source_id, deleted_derived_ids_json,
             surviving_derived_ids_json, blob_ref, forgotten_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            audit_id,
            source_id,
            json.dumps(sorted(deleted_derived_ids)),
            json.dumps(sorted(surviving_derived_ids)),
            blob_ref,
            datetime.now(tz=UTC).isoformat(),
        ),
    )
    conn.commit()
    return audit_id


def list_forget_audit(conn: SqlCipherConnection, *, limit: int = 50) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT id, source_id, deleted_derived_ids_json,
               surviving_derived_ids_json, blob_ref, forgotten_at
        FROM forget_audit ORDER BY forgotten_at DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    result: list[dict[str, object]] = []
    for row in rows:
        result.append(
            {
                "id": row[0],
                "source_id": row[1],
                "deleted_derived_ids": json.loads(row[2]),
                "surviving_derived_ids": json.loads(row[3]),
                "blob_ref": row[4],
                "forgotten_at": row[5],
            }
        )
    return result


def make_derived_record(
    *,
    record_id: str | None = None,
    record_type: DerivedRecordType,
    memory_layer: MemoryLayer = MemoryLayer.ACTIVE,
    payload: dict[str, object] | None = None,
    derived_from: list[str],
    purpose: RetentionPurpose,
    retention_class: RetentionClass = RetentionClass.EXPIRE_WITH_SOURCE,
    expires_after_resolution: str | None = None,
    confidence: float = 1.0,
) -> DerivedRecord:
    """Factory for lineage-bound derived rows."""
    return DerivedRecord(
        id=record_id or uuid4().hex,
        record_type=record_type,
        memory_layer=memory_layer,
        payload=dict(payload or {}),
        lineage=LineageMetadata(
            derived_from=list(derived_from),
            purpose=purpose,
            retention_class=retention_class,
            expires_after_resolution=expires_after_resolution,
        ),
        confidence=confidence,
        created_at=datetime.now(tz=UTC),
    )


def _source_deps_for(conn: SqlCipherConnection, derived_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT source_id FROM derived_source_deps WHERE derived_id = ? ORDER BY source_id",
        (derived_id,),
    ).fetchall()
    return [row[0] for row in rows]


def _row_to_record(row: tuple[object, ...], deps: list[str]) -> DerivedRecord:
    payload_raw = json.loads(str(row[3]))
    if not isinstance(payload_raw, dict):
        payload_raw = {}
    return DerivedRecord(
        id=str(row[0]),
        record_type=DerivedRecordType(str(row[1])),
        memory_layer=MemoryLayer(str(row[2])),
        payload=payload_raw,
        lineage=LineageMetadata(
            derived_from=deps,
            purpose=RetentionPurpose(str(row[4])),
            retention_class=RetentionClass(str(row[5])),
            expires_after_resolution=str(row[6]) if row[6] is not None else None,
        ),
        confidence=float(str(row[7])),
        created_at=datetime.fromisoformat(str(row[8])),
        resolved_at=datetime.fromisoformat(str(row[9])) if row[9] else None,
    )
