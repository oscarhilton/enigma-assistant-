from datetime import UTC, datetime
from uuid import uuid4

from personal_enigma.domain import (
    CalendarEvidence,
    Obligation,
    PrivateCalendarEvent,
    PrivateMessage,
    ReminderEvidence,
    SourceType,
)


def test_source_type_values() -> None:
    assert SourceType.CALENDAR_EVENT == "calendar_event"
    assert SourceType.REMINDER == "reminder"
    assert SourceType.NOTE == "note"
    assert SourceType.CONTACT == "contact"
    assert SourceType.EMAIL == "email"


def test_calendar_event_extended_fields_roundtrip() -> None:
    event = PrivateCalendarEvent(
        id="evt_1",
        provider="apple_calendar",
        provider_event_id="EK-1",
        calendar_id="cal_1",
        calendar_name="Personal",
        title="Review",
        url="https://example.com/event",
        start_at=datetime(2026, 8, 16, 14, 0, tzinfo=UTC),
        end_at=datetime(2026, 8, 16, 15, 0, tzinfo=UTC),
        availability="busy",
    )
    restored = PrivateCalendarEvent.model_validate(event.model_dump())
    assert restored.calendar_name == "Personal"
    assert restored.url == "https://example.com/event"
    assert restored.availability == "busy"


def test_private_message_roundtrip() -> None:
    message = PrivateMessage(
        id="msg_1",
        provider="gmail",
        provider_message_id="g-1",
        subject="Checking in",
        body_text="Have you reviewed the proposal?",
    )
    restored = PrivateMessage.model_validate(message.model_dump())
    assert restored.provider == "gmail"
    assert restored.subject == "Checking in"


def test_obligation_evidence_discriminator() -> None:
    obligation = Obligation(
        description="Review proposal",
        confidence=0.9,
        evidence=[
            ReminderEvidence(reminder_id="rem_1", title="Review proposal"),
            CalendarEvidence(event_id="evt_1", title="Proposal review"),
        ],
    )
    dumped = obligation.model_dump()
    restored = Obligation.model_validate(dumped)
    assert restored.evidence[0].kind == "reminder"
    assert restored.evidence[1].kind == "calendar"


def test_person_id_is_uuid() -> None:
    from personal_enigma.domain import PrivatePerson

    person = PrivatePerson(id=uuid4(), display_name="Test")
    assert person.display_name == "Test"
