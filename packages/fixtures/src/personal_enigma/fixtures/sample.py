"""Minimal sample fixtures for smoke tests."""

from datetime import UTC, datetime

from personal_enigma.domain import PrivateCalendarEvent


def sample_calendar_event() -> PrivateCalendarEvent:
    return PrivateCalendarEvent(
        id="evt_fixture_1",
        provider="apple_calendar",
        provider_event_id="EK-1",
        calendar_id="cal_personal",
        title="Fixture meeting",
        start_at=datetime(2026, 8, 16, 14, 0, tzinfo=UTC),
        end_at=datetime(2026, 8, 16, 15, 0, tzinfo=UTC),
        all_day=False,
    )
