from personal_enigma.ingestion import ChangeBatch, SyncCursor


def test_change_batch_defaults() -> None:
    batch = ChangeBatch()
    assert batch.items == []
    assert batch.next_cursor is None
    assert batch.exhausted is False


def test_sync_cursor_roundtrip() -> None:
    cursor = SyncCursor(value="abc", source="apple_calendar")
    assert cursor.model_dump() == {"value": "abc", "source": "apple_calendar"}
