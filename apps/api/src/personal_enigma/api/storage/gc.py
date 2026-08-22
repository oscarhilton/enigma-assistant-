"""Retention TTL garbage collection (SEC-06 pilot defaults)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from sqlite3 import Connection as SqlCipherConnection

from personal_enigma.api.storage.forget import ForgetResult, forget_source
from personal_enigma.api.storage.paths import DEFAULT_CONFIG
from personal_enigma.api.storage.source_record import get_source_record


@dataclass(frozen=True, slots=True)
class GcResult:
    """Summary of a GC sweep — ids and counts only."""

    expired_source_ids: tuple[str, ...]
    forget_results: tuple[ForgetResult, ...]
    resolved_obligations_expired: int


def load_retention_config(config: dict[str, object] | None = None) -> dict[str, int]:
    """Return retention TTL days from config or pilot defaults."""
    defaults = DEFAULT_CONFIG.get("retention")
    base: dict[str, int] = {
        "raw_email_blob_days": 7,
        "resolved_obligation_days": 90,
    }
    if isinstance(defaults, dict):
        for key, value in defaults.items():
            if isinstance(key, str) and isinstance(value, int):
                base[key] = value
    if config is not None:
        retention = config.get("retention")
        if isinstance(retention, dict):
            for key, value in retention.items():
                if isinstance(key, str) and isinstance(value, int):
                    base[key] = value
    return base


def find_expired_raw_sources(
    conn: SqlCipherConnection,
    *,
    now: datetime | None = None,
    raw_email_blob_days: int = 7,
) -> list[str]:
    """Return source record ids whose raw blob TTL has elapsed."""
    cutoff = (now or datetime.now(tz=UTC)) - timedelta(days=raw_email_blob_days)
    rows = conn.execute(
        """
        SELECT id, received_at FROM source_records
        WHERE source = 'gmail' AND received_at < ?
        ORDER BY received_at
        """,
        (cutoff.isoformat(),),
    ).fetchall()
    return [str(row[0]) for row in rows]


def gc_expired_raw_blobs(
    conn: SqlCipherConnection,
    *,
    delete_blob: Callable[[str], None],
    now: datetime | None = None,
    raw_email_blob_days: int = 7,
) -> GcResult:
    """Expire raw email blobs past TTL — full derivative cascade via forget."""
    expired = find_expired_raw_sources(
        conn, now=now, raw_email_blob_days=raw_email_blob_days
    )
    results: list[ForgetResult] = []
    for source_id in expired:
        if get_source_record(conn, source_id) is None:
            continue
        results.append(
            forget_source(conn, source_id, delete_blob=delete_blob)
        )
    return GcResult(
        expired_source_ids=tuple(expired),
        forget_results=tuple(results),
        resolved_obligations_expired=0,
    )


def gc_resolved_obligations(
    conn: SqlCipherConnection,
    *,
    now: datetime | None = None,
    resolved_obligation_days: int = 90,
) -> int:
    """Remove resolved active obligations past post-resolution TTL."""
    cutoff = (now or datetime.now(tz=UTC)) - timedelta(days=resolved_obligation_days)
    rows = conn.execute(
        """
        SELECT id FROM derived_records
        WHERE record_type = 'fact'
          AND resolved_at IS NOT NULL
          AND resolved_at < ?
          AND memory_layer = 'active'
        """,
        (cutoff.isoformat(),),
    ).fetchall()
    count = 0
    for (record_id,) in rows:
        conn.execute("DELETE FROM derived_records WHERE id = ?", (record_id,))
        count += 1
    if count:
        conn.commit()
    return count
