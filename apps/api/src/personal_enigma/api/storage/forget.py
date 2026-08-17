"""Deterministic forget graph operation (SEC-06).

``forget(source_id)`` answers:
1. What depends exclusively on this source?
2. What has independent evidence?
3. What must disappear?
4. What can remain but lose confidence?
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from sqlite3 import Connection as SqlCipherConnection

from personal_enigma.api.storage.derived import (
    append_forget_audit,
    delete_derived_record,
    list_derived_records_for_source,
)
from personal_enigma.api.storage.source_record import delete_source_record, get_source_record


@dataclass(frozen=True, slots=True)
class ForgetResult:
    """Outcome of a graph forget operation — ids only, never content."""

    source_id: str
    deleted_derived_ids: tuple[str, ...]
    surviving_derived_ids: tuple[str, ...]
    blob_ref: str | None
    audit_id: str
    source_deleted: bool


def _existing_source_ids(conn: SqlCipherConnection) -> set[str]:
    rows = conn.execute("SELECT id FROM source_records").fetchall()
    return {str(row[0]) for row in rows}


def resolve_forget_plan(
    conn: SqlCipherConnection,
    source_id: str,
) -> tuple[set[str], set[str]]:
    """Compute which derived records must be deleted vs survive.

    Returns ``(to_delete, to_survive)`` derived record id sets.
    """
    candidates = list_derived_records_for_source(conn, source_id)
    to_delete: set[str] = set()
    to_survive: set[str] = set()
    existing_sources = _existing_source_ids(conn)

    for record in candidates:
        remaining = [
            sid
            for sid in record.lineage.derived_from
            if sid != source_id and sid in existing_sources
        ]
        if not remaining:
            to_delete.add(record.id)
        else:
            to_survive.add(record.id)

    return to_delete, to_survive


def forget_source(
    conn: SqlCipherConnection,
    source_id: str,
    *,
    delete_blob: Callable[[str], None] | None = None,
) -> ForgetResult:
    """Graph forget for ``source_id`` — cascade derivatives, remove blob + SourceRecord."""
    existing = get_source_record(conn, source_id)
    blob_ref = existing.blob_ref if existing is not None else None

    to_delete, to_survive = resolve_forget_plan(conn, source_id)

    for derived_id in sorted(to_delete):
        delete_derived_record(conn, derived_id)

    if delete_blob is not None and blob_ref is not None:
        delete_blob(blob_ref)

    source_deleted = False
    if existing is not None:
        delete_source_record(conn, source_id)
        source_deleted = True

    audit_id = append_forget_audit(
        conn,
        source_id=source_id,
        deleted_derived_ids=sorted(to_delete),
        surviving_derived_ids=sorted(to_survive),
        blob_ref=blob_ref,
    )

    return ForgetResult(
        source_id=source_id,
        deleted_derived_ids=tuple(sorted(to_delete)),
        surviving_derived_ids=tuple(sorted(to_survive)),
        blob_ref=blob_ref,
        audit_id=audit_id,
        source_deleted=source_deleted,
    )


def forget_scope_by_source_ids(
    conn: SqlCipherConnection,
    source_ids: list[str],
    *,
    delete_blob: Callable[[str], None] | None = None,
) -> list[ForgetResult]:
    """Scoped forget — graph operation over multiple sources."""
    results: list[ForgetResult] = []
    for source_id in source_ids:
        results.append(
            forget_source(conn, source_id, delete_blob=delete_blob)
        )
    return results
