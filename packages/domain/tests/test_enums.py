from datetime import UTC, datetime
from uuid import uuid4

from personal_enigma.domain import (
    ActionCategory,
    ActionContext,
    CalendarEvidence,
    ChatEvidence,
    Effort,
    NextAction,
    Obligation,
    PrivateCalendarEvent,
    PrivateChatMessage,
    PrivateMessage,
    PrivatePersonRef,
    ReminderEvidence,
    SourceType,
    Urgency,
)


def test_source_type_values() -> None:
    assert SourceType.CALENDAR_EVENT == "calendar_event"
    assert SourceType.REMINDER == "reminder"
    assert SourceType.NOTE == "note"
    assert SourceType.CONTACT == "contact"
    assert SourceType.EMAIL == "email"
    assert SourceType.CHAT_MESSAGE == "chat_message"


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


def test_private_chat_message_roundtrip() -> None:
    message = PrivateChatMessage(
        id="chat_1",
        provider="whatsapp",
        provider_message_id="wa-1",
        chat_id="chat-elena",
        from_person=PrivatePersonRef(
            display_name="Elena Vargas",
            phone="+447700900011",
        ),
        body_text="Mum and Dad are definitely coming Saturday btw",
        kind="text",
        sent_at=datetime(2026, 1, 19, 18, 30, tzinfo=UTC),
    )
    restored = PrivateChatMessage.model_validate(message.model_dump())
    assert restored.provider == "whatsapp"
    assert restored.from_person is not None
    assert restored.from_person.phone == "+447700900011"
    assert restored.kind == "text"


def test_chat_evidence_discriminator() -> None:
    obligation = Obligation(
        description="Book Saturday brunch",
        evidence=[
            ChatEvidence(message_id="wa-1", chat_id="chat-elena", snippet="I'll sort brunch"),
        ],
    )
    restored = Obligation.model_validate(obligation.model_dump())
    assert restored.evidence[0].kind == "chat"
    assert isinstance(restored.evidence[0], ChatEvidence)


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


def test_action_category_values() -> None:
    assert ActionCategory.MOVEMENT == "movement"
    assert ActionCategory.NOTHING == "nothing"
    assert ActionCategory.REST == "rest"
    assert Effort.LOW == "low"
    assert Urgency.NONE == "none"
    assert ActionContext.HIGH_LOAD == "high_load"


def test_next_action_roundtrip_defaults_optional() -> None:
    action = NextAction(
        title="Go for a short walk",
        reason="Clear hour before next commitment; load is high.",
        category=ActionCategory.MOVEMENT,
        estimated_minutes=15,
        effort=Effort.LOW,
        context=[ActionContext.SHORT_WINDOW, ActionContext.HIGH_LOAD],
        source_ids=["cal:next-meeting"],
        value=0.7,
        confidence=0.6,
    )
    restored = NextAction.model_validate(action.model_dump())
    assert restored.optional is True
    assert restored.urgency == Urgency.NONE
    assert restored.category == ActionCategory.MOVEMENT
    assert restored.context == [ActionContext.SHORT_WINDOW, ActionContext.HIGH_LOAD]
