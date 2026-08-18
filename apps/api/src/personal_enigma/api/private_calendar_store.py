"""My Enigma calendar event store — read-only, private root only (P03).

Real adapters (M08/M12) sync into this store; conversation reads from here.
Demo / Alex Lab never uses this path.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from personal_enigma.domain import PrivateCalendarEvent


class CalendarReadAdapter(Protocol):
    """Read calendar events for My Enigma. Implementations must not mutate provider state."""

    def list_events(self) -> list[PrivateCalendarEvent]: ...


@dataclass
class CalendarEventStore:
    """JSON-backed calendar store under a world's storage root."""

    storage_root: Path
    _events: list[PrivateCalendarEvent] = field(default_factory=list, repr=False)

    @property
    def path(self) -> Path:
        return self.storage_root / "calendar" / "events.json"

    def load(self) -> list[PrivateCalendarEvent]:
        if not self.path.exists():
            self._events = []
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        rows = raw.get("events") if isinstance(raw, dict) else raw
        if not isinstance(rows, list):
            self._events = []
            return []
        events: list[PrivateCalendarEvent] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                events.append(PrivateCalendarEvent.model_validate(row))
            except ValidationError:
                continue
        self._events = events
        return list(events)

    def replace_all(self, events: list[PrivateCalendarEvent]) -> None:
        """Replace stored events (ingestion sync). Not exposed on conversation wire."""
        self._events = list(events)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"events": [event.model_dump(mode="json") for event in events]}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def events(self) -> list[PrivateCalendarEvent]:
        """Disk is source of truth — live M08/M12 sync must be visible without a session reset."""
        return self.load()

    def events_between(self, start: datetime, end: datetime) -> list[PrivateCalendarEvent]:
        rows: list[PrivateCalendarEvent] = []
        for event in self.events():
            when = event.start_at
            if when.tzinfo is None:
                when = when.replace(tzinfo=start.tzinfo)
            if start <= when.astimezone(start.tzinfo) <= end:
                rows.append(event)
        rows.sort(key=lambda row: row.start_at)
        return rows


@dataclass(frozen=True)
class StoreCalendarAdapter:
    """Default My Enigma adapter — reads from the private-world JSON store."""

    store: CalendarEventStore

    def list_events(self) -> list[PrivateCalendarEvent]:
        return self.store.events()


@dataclass(frozen=True)
class FixtureCalendarAdapter:
    """Deterministic fixture adapter for CI / local dev without bridge credentials."""

    events: tuple[PrivateCalendarEvent, ...]

    def list_events(self) -> list[PrivateCalendarEvent]:
        return list(self.events)


def load_fixture_events(path: Path) -> list[PrivateCalendarEvent]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("events") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        return []
    events: list[PrivateCalendarEvent] = []
    for row in rows:
        if isinstance(row, dict):
            events.append(PrivateCalendarEvent.model_validate(row))
    return events


def calendar_adapter_for_root(storage_root: Path) -> CalendarReadAdapter:
    """Resolve adapter: explicit fixture env wins; else on-disk private store."""
    fixture = os.environ.get("ENIGMA_CALENDAR_FIXTURE")
    if fixture:
        events = load_fixture_events(Path(fixture))
        return FixtureCalendarAdapter(events=tuple(events))
    return StoreCalendarAdapter(store=CalendarEventStore(storage_root=storage_root))


def reduced_calendar_fact(event: PrivateCalendarEvent) -> dict[str, Any]:
    """Request-relevant calendar row — no descriptions or attendee emails."""
    return {
        "id": event.id,
        "title": event.title,
        "start_at": event.start_at.isoformat(),
        "end_at": event.end_at.isoformat(),
        "all_day": event.all_day,
        "calendar_name": event.calendar_name,
    }


__all__ = [
    "CalendarEventStore",
    "CalendarReadAdapter",
    "FixtureCalendarAdapter",
    "StoreCalendarAdapter",
    "calendar_adapter_for_root",
    "load_fixture_events",
    "reduced_calendar_fact",
]
