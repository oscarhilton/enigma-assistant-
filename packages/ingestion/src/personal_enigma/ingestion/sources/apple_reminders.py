"""Apple Reminders DataSource adapter — owned by ticket M09."""

from __future__ import annotations

from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor


class AppleReminderSource:
    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        raise NotImplementedError("Implemented in ticket M09")
