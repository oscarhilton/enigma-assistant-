"""Apple Calendar DataSource adapter — owned by ticket M08."""

from __future__ import annotations

from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor


class AppleCalendarSource:
    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        raise NotImplementedError("Implemented in ticket M08")
