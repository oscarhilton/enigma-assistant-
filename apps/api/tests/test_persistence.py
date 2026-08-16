from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import inspect

from personal_enigma.api.db import (
    PrivateStore,
    assert_local_sqlite_url,
    create_db_engine,
    open_store,
)
from personal_enigma.api.db.migrate import downgrade_base, upgrade_head
from personal_enigma.domain import Obligation, ReminderEvidence
from personal_enigma.ingestion import SyncCursor


def test_assert_local_sqlite_rejects_non_sqlite() -> None:
    with pytest.raises(ValueError, match="Only local sqlite"):
        assert_local_sqlite_url("postgresql://localhost/enigma")


def test_assert_local_sqlite_rejects_host_qualified() -> None:
    with pytest.raises(ValueError, match="host-qualified"):
        assert_local_sqlite_url("sqlite://db.example.com/private.db")


def test_assert_local_sqlite_rejects_missing_slashes() -> None:
    with pytest.raises(ValueError, match="sqlite:///"):
        assert_local_sqlite_url("sqlite:relative.db")


def test_migration_up_down_smoke(tmp_path: Path) -> None:
    db_path = tmp_path / "private.db"
    url = f"sqlite:///{db_path}"

    upgrade_head(url)
    assert db_path.exists()

    engine = create_db_engine(url=url)
    tables_up = set(inspect(engine).get_table_names())
    assert {"sync_cursors", "ingested_records", "obligations", "alembic_version"} <= tables_up

    downgrade_base(url)
    tables_down = set(inspect(engine).get_table_names())
    assert "sync_cursors" not in tables_down
    assert "ingested_records" not in tables_down
    assert "obligations" not in tables_down


def test_sync_cursor_and_obligation_roundtrip(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'roundtrip.db'}"
    upgrade_head(url)
    store: PrivateStore = open_store(url=url)

    cursor = SyncCursor(value="tok-1", source="apple_calendar")
    store.upsert_sync_cursor(cursor)
    restored_cursor = store.get_sync_cursor("apple_calendar")
    assert restored_cursor is not None
    assert restored_cursor.value == "tok-1"
    assert restored_cursor.source == "apple_calendar"

    obligation = Obligation(
        description="Review proposal",
        confidence=0.85,
        evidence=[ReminderEvidence(reminder_id="rem_1", title="Review proposal")],
    )
    oid = store.upsert_obligation(obligation, obligation_id="obl-test-1")
    restored = store.get_obligation(oid)
    assert restored is not None
    assert restored.description == "Review proposal"
    assert restored.confidence == 0.85
    assert restored.evidence[0].kind == "reminder"

    store.upsert_ingested_record(
        record_id="evt_1",
        source_type="calendar_event",
        provider="apple",
        provider_record_id="EK-1",
        payload={"id": "evt_1", "title": "Review"},
    )
    payload = store.get_ingested_record("evt_1")
    assert payload == {"id": "evt_1", "title": "Review"}
