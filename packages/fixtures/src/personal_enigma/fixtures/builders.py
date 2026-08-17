"""Deterministic builders for synthetic private-world domain models.

All defaults use fixed IDs, timestamps, and `@example.test` addresses so
tests are reproducible and never contain real personal data. Override any
field via keyword arguments.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from personal_enigma.domain import (
    PrivateCalendarEvent,
    PrivateChatMessage,
    PrivateMessage,
    PrivateNote,
    PrivatePerson,
    PrivatePersonRef,
    PrivateReminder,
    RecurrenceInfo,
)

# Stable anchors shared across builders and scenario packs.
FIXTURE_EPOCH = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
SYNTHETIC_PERSON_ID = UUID("00000000-0000-4000-8000-000000000001")


def _as_person_ref(value: PrivatePersonRef | dict[str, Any] | None) -> PrivatePersonRef | None:
    if value is None:
        return None
    if isinstance(value, PrivatePersonRef):
        return value
    return build_person_ref(**value)


def _as_person_refs(values: list[PrivatePersonRef | dict[str, Any]]) -> list[PrivatePersonRef]:
    return [
        item if isinstance(item, PrivatePersonRef) else build_person_ref(**item)
        for item in values
    ]


def build_person_ref(**overrides: Any) -> PrivatePersonRef:
    """Build a lightweight person reference (attendee / sender)."""
    data: dict[str, Any] = {
        "display_name": "Alex Chen",
        "email": "alex.chen@example.test",
        "provider_id": "person_ref_alex",
    }
    data.update(overrides)
    return PrivatePersonRef.model_validate(data)


def build_calendar_event(**overrides: Any) -> PrivateCalendarEvent:
    """Build a synthetic calendar event (Apple Calendar by default)."""
    data: dict[str, Any] = {
        "id": "evt_fixture_1",
        "provider": "apple_calendar",
        "provider_event_id": "EK-fixture-1",
        "calendar_id": "cal_personal",
        "calendar_name": "Personal",
        "title": "Fixture meeting",
        "description": None,
        "location": None,
        "url": None,
        "start_at": datetime(2026, 8, 16, 14, 0, tzinfo=UTC),
        "end_at": datetime(2026, 8, 16, 15, 0, tzinfo=UTC),
        "all_day": False,
        "availability": "busy",
        "organiser": None,
        "attendees": [],
        "recurrence": None,
        "updated_at": FIXTURE_EPOCH,
    }
    data.update(overrides)
    if "organiser" in overrides:
        data["organiser"] = _as_person_ref(overrides["organiser"])
    if "attendees" in overrides:
        data["attendees"] = _as_person_refs(overrides["attendees"])
    if "recurrence" in overrides and isinstance(overrides["recurrence"], dict):
        data["recurrence"] = RecurrenceInfo.model_validate(overrides["recurrence"])
    return PrivateCalendarEvent.model_validate(data)


def build_reminder(**overrides: Any) -> PrivateReminder:
    """Build a synthetic Apple Reminder."""
    data: dict[str, Any] = {
        "id": "rem_fixture_1",
        "provider": "apple_reminders",
        "provider_id": "REM-fixture-1",
        "list_id": "list_inbox",
        "title": "Fixture reminder",
        "notes": None,
        "due_at": datetime(2026, 8, 17, 17, 0, tzinfo=UTC),
        "completed_at": None,
        "is_completed": False,
        "priority": None,
        "created_at": FIXTURE_EPOCH,
        "updated_at": FIXTURE_EPOCH,
    }
    data.update(overrides)
    return PrivateReminder.model_validate(data)


def build_contact(**overrides: Any) -> PrivatePerson:
    """Build a synthetic PrivatePerson contact (deterministic UUID by default)."""
    data: dict[str, Any] = {
        "id": SYNTHETIC_PERSON_ID,
        "display_name": "Alex Chen",
        "aliases": ["A. Chen"],
        "email_addresses": ["alex.chen@example.test"],
        "phone_numbers": ["+1-555-0100"],
        "organisations": ["Example Corp"],
        "provider_ids": {"apple_contacts": "AB-fixture-1"},
    }
    data.update(overrides)
    return PrivatePerson.model_validate(data)


def build_note(**overrides: Any) -> PrivateNote:
    """Build a synthetic Apple Note."""
    data: dict[str, Any] = {
        "id": "note_fixture_1",
        "provider": "apple_notes",
        "provider_note_id": "NOTE-fixture-1",
        "folder": "Notes",
        "title": "Fixture note",
        "body_text": "Synthetic note body for tests.",
        "created_at": FIXTURE_EPOCH,
        "updated_at": FIXTURE_EPOCH,
        "metadata": {},
    }
    data.update(overrides)
    return PrivateNote.model_validate(data)


def build_message(**overrides: Any) -> PrivateMessage:
    """Build a synthetic Gmail PrivateMessage."""
    data: dict[str, Any] = {
        "id": "msg_fixture_1",
        "provider": "gmail",
        "provider_message_id": "gmail-fixture-1",
        "thread_id": "thread_fixture_1",
        "subject": "Fixture subject",
        "snippet": "Synthetic email snippet.",
        "body_text": "Synthetic email body for tests.",
        "from_person": build_person_ref(),
        "to": [
            build_person_ref(
                display_name="Sam Rivera",
                email="sam.rivera@example.test",
                provider_id="person_ref_sam",
            )
        ],
        "cc": [],
        "sent_at": FIXTURE_EPOCH,
        "received_at": FIXTURE_EPOCH,
        "labels": ["INBOX"],
    }
    data.update(overrides)
    if "from_person" in overrides:
        data["from_person"] = _as_person_ref(overrides["from_person"])
    if "to" in overrides:
        data["to"] = _as_person_refs(overrides["to"])
    if "cc" in overrides:
        data["cc"] = _as_person_refs(overrides["cc"])
    return PrivateMessage.model_validate(data)


def build_chat_message(**overrides: Any) -> PrivateChatMessage:
    """Build a synthetic WhatsApp PrivateChatMessage."""
    data: dict[str, Any] = {
        "id": "wa_fixture_1",
        "provider": "whatsapp",
        "provider_message_id": "wa-fixture-1",
        "chat_id": "chat_fixture_1",
        "thread_id": "chat_fixture_1",
        "from_person": build_person_ref(
            display_name="Elena Vargas",
            email=None,
            phone="+447700900011",
            provider_id="elena",
        ),
        "to": [
            build_person_ref(
                display_name="Alex Morgan",
                email=None,
                phone="+447700900001",
                provider_id="alex",
            )
        ],
        "body_text": "See you Saturday",
        "sent_at": FIXTURE_EPOCH,
        "is_group": False,
        "chat_title": None,
        "kind": "text",
        "reaction_emoji": None,
        "reply_to_id": None,
    }
    data.update(overrides)
    if "from_person" in overrides:
        data["from_person"] = _as_person_ref(overrides["from_person"])
    if "to" in overrides:
        data["to"] = _as_person_refs(overrides["to"])
    return PrivateChatMessage.model_validate(data)


def sample_calendar_event() -> PrivateCalendarEvent:
    """Return the default synthetic calendar event (M01 scaffold alias)."""
    return build_calendar_event()
