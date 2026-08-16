"""Gmail DataSource adapter — owned by ticket M11."""

from __future__ import annotations

from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor


class GmailSource:
    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        raise NotImplementedError("Implemented in ticket M11")
