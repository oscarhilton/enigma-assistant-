"""Build AttentionItems from domain records (fixture / ingestion inputs)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from personal_enigma.attention.classify import message_attention_kind
from personal_enigma.attention.kinds import AttentionKind
from personal_enigma.attention.protocol import AttentionItem
from personal_enigma.attention.surface import ui_priority_for_kind
from personal_enigma.domain import (
    Obligation,
    PrivateCalendarEvent,
    PrivateMessage,
    PrivateReminder,
)


class ClockLike(Protocol):
    def now(self) -> datetime: ...


def items_from_reminders(reminders: Sequence[PrivateReminder]) -> list[AttentionItem]:
    """Map Apple Reminders (and peers) to EXPLICIT_REMINDER attention."""
    items: list[AttentionItem] = []
    for reminder in reminders:
        if reminder.is_completed:
            continue
        body = reminder.notes or ""
        if reminder.due_at is not None:
            due = reminder.due_at.isoformat()
            body = f"{body}\nDue {due}".strip() if body else f"Due {due}"
        kind = AttentionKind.EXPLICIT_REMINDER
        items.append(
            AttentionItem(
                title=reminder.title,
                body=body,
                kind=kind,
                score=float(reminder.priority or 0),
                evidence_ids=[reminder.id],
                priority=ui_priority_for_kind(kind),
            )
        )
    return items


def items_from_messages(messages: Sequence[PrivateMessage]) -> list[AttentionItem]:
    """Map email/messages via classify — never machine noise as commitment."""
    items: list[AttentionItem] = []
    for message in messages:
        kind = message_attention_kind(message)
        if kind is None:
            continue
        title = message.subject or message.snippet or "Email follow-up"
        body = message.snippet or message.body_text or ""
        score = 0.35 if kind is AttentionKind.PENDING_REPLY else 0.0
        items.append(
            AttentionItem(
                title=title,
                body=body,
                kind=kind,
                score=score,
                evidence_ids=[message.id],
                priority=ui_priority_for_kind(kind),
            )
        )
    return items


def items_from_calendar_events(
    events: Sequence[PrivateCalendarEvent],
    *,
    clock: ClockLike | None = None,
    now: datetime | None = None,
    allow_bare_calendar: bool = False,
) -> list[AttentionItem]:
    """Map calendar events to attention only when explicitly allowed.

    Hard rule: scheduled existence is not an obligation. Bare calendar rows
    stay context/upcoming, not AttentionItems.
    """
    if not allow_bare_calendar:
        return []

    instant = now
    if instant is None and clock is not None:
        instant = clock.now()
    items: list[AttentionItem] = []
    for event in events:
        if instant is not None and event.end_at < instant:
            continue
        body = event.description or ""
        window = f"{event.start_at.isoformat()} – {event.end_at.isoformat()}"
        body = f"{body}\n{window}".strip() if body else window
        kind = AttentionKind.CALENDAR_OBLIGATION
        items.append(
            AttentionItem(
                title=event.title,
                body=body,
                kind=kind,
                score=0.0,
                evidence_ids=[event.id],
                priority=ui_priority_for_kind(kind),
            )
        )
    return items


def items_from_obligations(obligations: Sequence[Obligation]) -> list[AttentionItem]:
    """Map merged obligations to INFERRED_OBLIGATION (pre-M15 / no reminder)."""
    items: list[AttentionItem] = []
    for obligation in obligations:
        evidence_ids: list[str] = []
        for evidence in obligation.evidence:
            if evidence.kind == "reminder":
                evidence_ids.append(evidence.reminder_id)
            elif evidence.kind == "email":
                evidence_ids.append(evidence.message_id)
            elif evidence.kind == "calendar":
                evidence_ids.append(evidence.event_id)
            elif evidence.kind == "note":
                evidence_ids.append(evidence.note_id)
        body = ""
        if obligation.due_at is not None:
            body = f"Due {obligation.due_at.isoformat()}"
        kind = AttentionKind.INFERRED_OBLIGATION
        items.append(
            AttentionItem(
                title=obligation.description,
                body=body,
                kind=kind,
                score=obligation.confidence,
                evidence_ids=evidence_ids,
                priority=ui_priority_for_kind(kind),
            )
        )
    return items


def collect_attention_items(
    *,
    reminders: Sequence[PrivateReminder] = (),
    messages: Sequence[PrivateMessage] = (),
    calendar_events: Sequence[PrivateCalendarEvent] = (),
    obligations: Sequence[Obligation] = (),
    clock: ClockLike | None = None,
    now: datetime | None = None,
    allow_bare_calendar: bool = False,
) -> list[AttentionItem]:
    """Collect unranked attention items from domain sources."""
    return [
        *items_from_reminders(reminders),
        *items_from_messages(messages),
        *items_from_calendar_events(
            calendar_events,
            clock=clock,
            now=now,
            allow_bare_calendar=allow_bare_calendar,
        ),
        *items_from_obligations(obligations),
    ]
