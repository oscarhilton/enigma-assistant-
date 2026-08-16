"""Apple Notes DataSource adapter — owned by ticket M13."""

from __future__ import annotations

from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor


class AppleNotesSource:
    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        raise NotImplementedError("Implemented in ticket M13")
