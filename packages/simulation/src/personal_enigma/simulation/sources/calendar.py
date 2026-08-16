"""Synthetic calendar DataSource — scenario events → PrivateCalendarEvent (D4)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from personal_enigma.domain import PrivateCalendarEvent
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


def event_from_scenario(event: ScenarioEvent) -> PrivateCalendarEvent | None:
    payload = event.payload
    raw_id = str(payload.get("id") or event.id)
    if event.type == "calendar.cancel":
        # Represent cancellation as a zero-length tombstone window for consumers.
        at = _aware(event.at)
        assert at is not None  # ScenarioEvent.at is required
        return PrivateCalendarEvent(
            id=stable_id("cal", raw_id),
            provider="apple_calendar",
            provider_event_id=raw_id,
            title=str(payload.get("title") or "Cancelled"),
            start_at=at,
            end_at=at,
            description="cancelled",
            updated_at=at,
        )
    start = _aware(payload.get("start_at") or event.at)
    end = _aware(payload.get("end_at")) or (start + timedelta(hours=1) if start else None)
    if start is None or end is None:
        return None
    return PrivateCalendarEvent(
        id=stable_id("cal", raw_id),
        provider="apple_calendar",
        provider_event_id=raw_id,
        calendar_name=payload.get("calendar_name"),
        title=str(payload.get("title") or "Untitled"),
        description=payload.get("description"),
        location=payload.get("location"),
        start_at=start,
        end_at=end,
        all_day=bool(payload.get("all_day", False)),
        updated_at=_aware(event.at),
    )


class SyntheticCalendarSource:
    source_name = "synthetic_calendar"

    def __init__(
        self,
        events: ScenarioPackage | Sequence[ScenarioEvent],
        *,
        until: datetime | None = None,
    ) -> None:
        self._events = events_for_source(
            package_events(events),
            source="calendar",
            until=until,
        )

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        items: list[dict] = []
        for event in self._events:
            if event.type not in {"calendar.upsert", "calendar.cancel"}:
                continue
            record = event_from_scenario(event)
            if record is not None:
                items.append(record.model_dump(mode="json"))
        return batch_from_items(items, source_name=self.source_name, start=cursor_index(cursor))
