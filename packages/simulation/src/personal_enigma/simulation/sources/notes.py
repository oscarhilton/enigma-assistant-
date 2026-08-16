"""Synthetic notes DataSource — scenario events → PrivateNote (D4)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from personal_enigma.domain import PrivateNote
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor
from personal_enigma.simulation.scenario import ScenarioEvent, ScenarioPackage
from personal_enigma.simulation.sources._base import (
    _aware,
    batch_from_items,
    cursor_index,
    events_for_source,
    package_events,
    stable_id,
)


def note_from_event(event: ScenarioEvent) -> PrivateNote:
    payload = event.payload
    raw_id = str(payload.get("id") or event.id)
    return PrivateNote(
        id=stable_id("note", raw_id),
        provider="apple_notes",
        provider_note_id=raw_id,
        folder=payload.get("folder"),
        title=str(payload.get("title") or "Note"),
        body_text=str(payload.get("body_text") or payload.get("body") or ""),
        created_at=_aware(payload.get("created_at") or event.at),
        updated_at=_aware(event.at),
        metadata={str(k): str(v) for k, v in (payload.get("metadata") or {}).items()},
    )


class SyntheticNotesSource:
    source_name = "synthetic_notes"

    def __init__(
        self,
        events: ScenarioPackage | Sequence[ScenarioEvent],
        *,
        until: datetime | None = None,
    ) -> None:
        self._events = events_for_source(
            package_events(events),
            source="notes",
            until=until,
        )

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        items = [
            note_from_event(event).model_dump(mode="json")
            for event in self._events
            if event.type == "note.upsert"
        ]
        return batch_from_items(items, source_name=self.source_name, start=cursor_index(cursor))
