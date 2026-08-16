"""Apple Contacts DataSource adapter — owned by ticket M10."""

from __future__ import annotations

from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor


class AppleContactsSource:
    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        raise NotImplementedError("Implemented in ticket M10")
