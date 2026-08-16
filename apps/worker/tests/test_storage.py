from __future__ import annotations

from pathlib import Path

from personal_enigma.ingestion import SyncCursor
from personal_enigma.worker.storage import migrate_worker_db, open_worker_store


def test_worker_store_roundtrip_after_migrate(tmp_path: Path) -> None:
    db_path = tmp_path / "worker-private.db"
    url = migrate_worker_db(path=db_path)
    assert "sqlite:" in url

    store = open_worker_store(path=db_path)
    store.upsert_sync_cursor(SyncCursor(value="w-1", source="gmail"))
    cursor = store.get_sync_cursor("gmail")
    assert cursor is not None
    assert cursor.value == "w-1"
