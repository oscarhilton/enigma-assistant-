"""Canonical private domain models (scaffold stubs for M01)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from personal_enigma.domain.enums import (
    ActionCategory,
    ActionContext,
    Effort,
    Urgency,
)


class RecurrenceInfo(BaseModel):
    """Recurrence metadata for calendar events."""

    rule: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class PrivatePersonRef(BaseModel):
    """Lightweight reference to a person used on events."""

    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    provider_id: str | None = None


class PrivateCalendarEvent(BaseModel):
    id: str
    provider: Literal["apple_calendar", "google_calendar"]
    provider_event_id: str
    calendar_id: str | None = None
    calendar_name: str | None = None
    title: str
    description: str | None = None
    location: str | None = None
    url: str | None = None
    start_at: datetime
    end_at: datetime
    all_day: bool = False
    availability: Literal["busy", "free", "tentative", "unavailable"] | None = None
    organiser: PrivatePersonRef | None = None
    attendees: list[PrivatePersonRef] = Field(default_factory=list)
    recurrence: RecurrenceInfo | None = None
    updated_at: datetime | None = None


class PrivateReminder(BaseModel):
    id: str
    provider: Literal["apple_reminders"]
    provider_id: str
    list_id: str | None = None
    title: str
    notes: str | None = None
    due_at: datetime | None = None
    completed_at: datetime | None = None
    is_completed: bool = False
    priority: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PrivatePerson(BaseModel):
    id: UUID
    display_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    email_addresses: list[str] = Field(default_factory=list)
    phone_numbers: list[str] = Field(default_factory=list)
    organisations: list[str] = Field(default_factory=list)
    provider_ids: dict[str, str] = Field(default_factory=dict)


class PrivateNote(BaseModel):
    id: str
    provider: Literal["apple_notes"]
    provider_note_id: str
    folder: str | None = None
    title: str
    body_text: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class PrivateMessage(BaseModel):
    """Canonical private email/message — provider-agnostic after ingestion."""

    id: str
    provider: Literal["gmail"]
    provider_message_id: str
    thread_id: str | None = None
    subject: str | None = None
    snippet: str | None = None
    body_text: str | None = None
    from_person: PrivatePersonRef | None = None
    to: list[PrivatePersonRef] = Field(default_factory=list)
    cc: list[PrivatePersonRef] = Field(default_factory=list)
    sent_at: datetime | None = None
    received_at: datetime | None = None
    labels: list[str] = Field(default_factory=list)


class PrivateChatMessage(BaseModel):
    """Canonical private chat message — provider-agnostic after ingestion.

    WhatsApp-shaped evidence, not the world model. Reactions and group noise
    stay on this record; obligations are derived downstream.
    """

    id: str
    provider: Literal["whatsapp"]
    provider_message_id: str
    chat_id: str
    thread_id: str | None = None
    from_person: PrivatePersonRef | None = None
    to: list[PrivatePersonRef] = Field(default_factory=list)
    body_text: str | None = None
    sent_at: datetime | None = None
    is_group: bool = False
    chat_title: str | None = None
    kind: Literal["text", "reaction", "system"] = "text"
    reaction_emoji: str | None = None
    reply_to_id: str | None = None


class ReminderEvidence(BaseModel):
    kind: Literal["reminder"] = "reminder"
    reminder_id: str
    title: str | None = None


class EmailEvidence(BaseModel):
    kind: Literal["email"] = "email"
    message_id: str
    subject: str | None = None


class CalendarEvidence(BaseModel):
    kind: Literal["calendar"] = "calendar"
    event_id: str
    title: str | None = None


class NoteEvidence(BaseModel):
    kind: Literal["note"] = "note"
    note_id: str
    title: str | None = None


class ChatEvidence(BaseModel):
    kind: Literal["chat"] = "chat"
    message_id: str
    chat_id: str | None = None
    snippet: str | None = None


ObligationEvidence = Annotated[
    ReminderEvidence | EmailEvidence | CalendarEvidence | NoteEvidence | ChatEvidence,
    Field(discriminator="kind"),
]


class Obligation(BaseModel):
    """Cross-source obligation merged from reminders, email, and calendar evidence."""

    description: str
    due_at: datetime | None = None
    evidence: list[ObligationEvidence] = Field(default_factory=list)
    confidence: float = 0.0


class NextAction(BaseModel):
    """Optional useful next step — not an Attention interrupt.

    Product contract: may be suggested when Attention is empty; never implies
    urgency unless ``urgency`` is set. See docs/architecture/next-action.md.
    """

    title: str
    reason: str
    category: ActionCategory
    estimated_minutes: int | None = None
    effort: Effort = Effort.MEDIUM
    context: list[ActionContext] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    urgency: Urgency = Urgency.NONE
    value: float = 0.0
    confidence: float = 0.0
    optional: bool = True
