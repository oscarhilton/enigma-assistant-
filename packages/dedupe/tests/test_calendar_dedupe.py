from datetime import UTC, datetime

from personal_enigma.dedupe import dedupe_calendar_events
from personal_enigma.domain import PrivateCalendarEvent


def test_dedupe_scaffold_passthrough() -> None:
    event = PrivateCalendarEvent(
        id="evt_1",
        provider="apple_calendar",
        provider_event_id="EK-1",
        title="Meeting",
        start_at=datetime(2026, 8, 16, 14, 0, tzinfo=UTC),
        end_at=datetime(2026, 8, 16, 15, 0, tzinfo=UTC),
    )
    assert dedupe_calendar_events([event]) == [event]
