"""Smoke tests: builders construct valid domain models."""

from datetime import UTC, datetime
from uuid import UUID

from personal_enigma.domain import (
    PrivateCalendarEvent,
    PrivateMessage,
    PrivateNote,
    PrivatePerson,
    PrivateReminder,
)
from personal_enigma.fixtures import (
    SYNTHETIC_PERSON_ID,
    build_calendar_event,
    build_contact,
    build_message,
    build_note,
    build_reminder,
    sample_calendar_event,
)


def test_sample_calendar_event() -> None:
    event = sample_calendar_event()
    assert isinstance(event, PrivateCalendarEvent)
    assert event.provider == "apple_calendar"
    assert event.title == "Fixture meeting"


def test_build_calendar_event_valid_and_deterministic() -> None:
    a = build_calendar_event()
    b = build_calendar_event()
    assert a == b
    assert a.model_validate(a.model_dump()) == a


def test_build_reminder_valid() -> None:
    rem = build_reminder(title="Review proposal")
    assert isinstance(rem, PrivateReminder)
    assert rem.provider == "apple_reminders"
    assert rem.title == "Review proposal"
    assert rem == build_reminder(title="Review proposal")


def test_build_contact_valid_deterministic_uuid() -> None:
    person = build_contact()
    assert isinstance(person, PrivatePerson)
    assert person.id == SYNTHETIC_PERSON_ID
    assert isinstance(person.id, UUID)
    assert person.email_addresses == ["alex.chen@example.test"]
    assert person == build_contact()


def test_build_note_valid() -> None:
    note = build_note()
    assert isinstance(note, PrivateNote)
    assert note.provider == "apple_notes"
    assert note.body_text
    assert note == build_note()


def test_build_message_valid() -> None:
    msg = build_message()
    assert isinstance(msg, PrivateMessage)
    assert msg.provider == "gmail"
    assert msg.from_person is not None
    assert msg.from_person.email is not None
    assert msg.from_person.email.endswith("@example.test")
    assert msg == build_message()


def test_builder_overrides() -> None:
    start = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
    end = datetime(2026, 9, 1, 11, 0, tzinfo=UTC)
    event = build_calendar_event(
        id="evt_custom",
        title="Custom",
        start_at=start,
        end_at=end,
        provider="google_calendar",
        provider_event_id="gcal-1",
    )
    assert event.id == "evt_custom"
    assert event.provider == "google_calendar"
    assert event.start_at == start
