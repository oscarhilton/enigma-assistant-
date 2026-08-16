"""Canonical private domain models (scaffold stubs for M01)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RecurrenceInfo(BaseModel):
    """Recurrence metadata for calendar events."""

    rule: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class PrivatePersonRef(BaseModel):
    """Lightweight reference to a person used on events."""

    display_name: str | None = None
    email: str | None = None
    provider_id: str | None = None


class PrivateCalendarEvent(BaseModel):
    id: str
    provider: Literal["apple_calendar", "google_calendar"]
    provider_event_id: str
    calendar_id: str | None = None
    title: str
    description: str | None = None
    location: str | None = None
    start_at: datetime
    end_at: datetime
    all_day: bool = False
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


class Obligation(BaseModel):
    """Cross-source obligation merged from reminders, email, and calendar evidence."""

    description: str
    due_at: datetime | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
