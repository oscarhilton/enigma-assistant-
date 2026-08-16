"""Dedupe PrivateCalendarEvent lists across providers (implemented in M12)."""

from __future__ import annotations

from personal_enigma.domain import PrivateCalendarEvent


def dedupe_calendar_events(events: list[PrivateCalendarEvent]) -> list[PrivateCalendarEvent]:
    """Return a single canonical event per real-world meeting.

    Scaffold identity stub — real logic lands in ticket M12.
    """
    return list(events)
