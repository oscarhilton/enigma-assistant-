"""High-level repository for sync cursors, ingested records, and obligations."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from personal_enigma.api.db.config import DatabaseSettings
from personal_enigma.api.db.engine import create_db_engine, make_session_factory, session_scope
from personal_enigma.api.db.models import Base, IngestedRecordRow, ObligationRow, SyncCursorRow
from personal_enigma.domain import Obligation
from personal_enigma.ingestion import SyncCursor


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PrivateStore:
    """Read/write access to the local private SQLite database."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def upsert_sync_cursor(self, cursor: SyncCursor) -> SyncCursor:
        """Persist a sync cursor keyed by ``cursor.source`` (required)."""
        if not cursor.source:
            raise ValueError("SyncCursor.source is required for persistence")
        now = _utcnow()
        with session_scope(self._session_factory) as session:
            row = session.get(SyncCursorRow, cursor.source)
            if row is None:
                row = SyncCursorRow(source=cursor.source, value=cursor.value, updated_at=now)
                session.add(row)
            else:
                row.value = cursor.value
                row.updated_at = now
        return SyncCursor(value=cursor.value, source=cursor.source)

    def get_sync_cursor(self, source: str) -> SyncCursor | None:
        """Return the stored cursor for ``source``, if any."""
        with session_scope(self._session_factory) as session:
            row = session.get(SyncCursorRow, source)
            if row is None:
                return None
            return SyncCursor(value=row.value, source=row.source)

    def upsert_ingested_record(
        self,
        *,
        record_id: str,
        source_type: str,
        provider: str,
        provider_record_id: str,
        payload: dict[str, Any],
    ) -> str:
        """Insert or update a canonical ingested record; returns ``record_id``."""
        now = _utcnow()
        payload_json = json.dumps(payload, default=str, sort_keys=True)
        with session_scope(self._session_factory) as session:
            row = session.get(IngestedRecordRow, record_id)
            if row is None:
                session.add(
                    IngestedRecordRow(
                        id=record_id,
                        source_type=source_type,
                        provider=provider,
                        provider_record_id=provider_record_id,
                        payload_json=payload_json,
                        ingested_at=now,
                        updated_at=now,
                    )
                )
            else:
                row.source_type = source_type
                row.provider = provider
                row.provider_record_id = provider_record_id
                row.payload_json = payload_json
                row.updated_at = now
        return record_id

    def get_ingested_record(self, record_id: str) -> dict[str, Any] | None:
        """Return the stored payload dict for ``record_id``, if any."""
        with session_scope(self._session_factory) as session:
            row = session.get(IngestedRecordRow, record_id)
            if row is None:
                return None
            return json.loads(row.payload_json)

    def upsert_obligation(self, obligation: Obligation, *, obligation_id: str | None = None) -> str:
        """Insert or update an obligation; returns the row id."""
        now = _utcnow()
        oid = obligation_id or str(uuid4())
        evidence_json = json.dumps(
            [item.model_dump(mode="json") for item in obligation.evidence],
            default=str,
            sort_keys=True,
        )
        with session_scope(self._session_factory) as session:
            row = session.get(ObligationRow, oid)
            if row is None:
                session.add(
                    ObligationRow(
                        id=oid,
                        description=obligation.description,
                        due_at=obligation.due_at,
                        confidence=obligation.confidence,
                        evidence_json=evidence_json,
                        created_at=now,
                        updated_at=now,
                    )
                )
            else:
                row.description = obligation.description
                row.due_at = obligation.due_at
                row.confidence = obligation.confidence
                row.evidence_json = evidence_json
                row.updated_at = now
        return oid

    def get_obligation(self, obligation_id: str) -> Obligation | None:
        """Load an obligation by id."""
        with session_scope(self._session_factory) as session:
            row = session.get(ObligationRow, obligation_id)
            if row is None:
                return None
            evidence = json.loads(row.evidence_json)
            return Obligation.model_validate(
                {
                    "description": row.description,
                    "due_at": row.due_at,
                    "confidence": row.confidence,
                    "evidence": evidence,
                }
            )

    def list_obligation_ids(self) -> list[str]:
        """Return all stored obligation ids (stable order)."""
        with session_scope(self._session_factory) as session:
            rows = session.scalars(select(ObligationRow.id).order_by(ObligationRow.id)).all()
            return list(rows)


def open_store(
    settings: DatabaseSettings | None = None,
    *,
    url: str | None = None,
    create_schema: bool = False,
) -> PrivateStore:
    """Open a ``PrivateStore`` against the configured local SQLite database.

    When ``create_schema`` is True, create ORM tables if missing (tests / bootstrap).
    Production paths should prefer Alembic migrations — see ``migrations/``.
    """
    engine = create_db_engine(settings, url=url)
    if create_schema:
        Base.metadata.create_all(engine)
    return PrivateStore(make_session_factory(engine))
