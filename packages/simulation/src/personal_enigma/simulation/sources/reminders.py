"""Synthetic reminders DataSource — scenario events → PrivateReminder (D4)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from personal_enigma.domain import PrivateReminder
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor
from personal_enigma.simulation.scenario import ScenarioEvent, ScenarioPackage
from personal_enigma.simulation.sources import (
    _aware,
    batch_from_items,
    cursor_index,
    events_for_source,
    package_events,
    stable_id,
)


def reminder_from_event(event: ScenarioEvent) -> PrivateReminder:
    payload = event.payload
    raw_id = str(payload.get("id") or event.id)
    completed = bool(payload.get("is_completed") or event.type == "reminder.complete")
    return PrivateReminder(
        id=stable_id("rem", raw_id),
        provider="apple_reminders",
        provider_id=raw_id,
        title=str(payload.get("title") or "Reminder"),
        notes=payload.get("notes"),
        due_at=_aware(payload.get("due_at")),
        completed_at=_aware(payload.get("completed_at") or (event.at if completed else None)),
        is_completed=completed,
        priority=payload.get("priority"),
        created_at=_aware(payload.get("created_at") or event.at),
        updated_at=_aware(event.at),
    )


class SyntheticReminderSource:
    """Demo-only reminders adapter — never reads Private storage or credentials."""

    source_name = "synthetic_reminders"

    def __init__(
        self,
        events: ScenarioPackage | Sequence[ScenarioEvent],
        *,
        until: datetime | None = None,
    ) -> None:
        self._events = events_for_source(
            package_events(events),
            source="reminders",
            until=until,
        )

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        items = [
            reminder_from_event(event).model_dump(mode="json")
            for event in self._events
            if event.type in {"reminder.upsert", "reminder.complete"}
        ]
        return batch_from_items(items, source_name=self.source_name, start=cursor_index(cursor))
