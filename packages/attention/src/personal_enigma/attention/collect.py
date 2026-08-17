"""Build AttentionItems from domain records (fixture / ingestion inputs)."""

from __future__ import annotations

from collections.abc import Sequence

from personal_enigma.attention.kinds import AttentionKind
from personal_enigma.attention.protocol import AttentionItem
from personal_enigma.domain import (
    Obligation,
    PrivateCalendarEvent,
    PrivateMessage,
    PrivateReminder,
)


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
        items.append(
            AttentionItem(
                title=reminder.title,
                body=body,
                kind=AttentionKind.EXPLICIT_REMINDER,
                score=float(reminder.priority or 0),
                evidence_ids=[reminder.id],
            )
        )
    return items


def items_from_messages(messages: Sequence[PrivateMessage]) -> list[AttentionItem]:
    """Map email/messages to weak INFERRED_COMMITMENT attention."""
    items: list[AttentionItem] = []
    for message in messages:
        title = message.subject or message.snippet or "Email follow-up"
        body = message.snippet or message.body_text or ""
        items.append(
            AttentionItem(
                title=title,
                body=body,
                kind=AttentionKind.INFERRED_COMMITMENT,
                score=0.0,
                evidence_ids=[message.id],
            )
        )
    return items


def items_from_calendar_events(
    events: Sequence[PrivateCalendarEvent],
) -> list[AttentionItem]:
    """Map calendar events to CALENDAR_OBLIGATION attention."""
    items: list[AttentionItem] = []
    for event in events:
        body = event.description or ""
        window = f"{event.start_at.isoformat()} – {event.end_at.isoformat()}"
        body = f"{body}\n{window}".strip() if body else window
        items.append(
            AttentionItem(
                title=event.title,
                body=body,
                kind=AttentionKind.CALENDAR_OBLIGATION,
                score=0.0,
                evidence_ids=[event.id],
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
            elif evidence.kind == "chat":
                evidence_ids.append(evidence.message_id)
        body = ""
        if obligation.due_at is not None:
            body = f"Due {obligation.due_at.isoformat()}"
        items.append(
            AttentionItem(
                title=obligation.description,
                body=body,
                kind=AttentionKind.INFERRED_OBLIGATION,
                score=obligation.confidence,
                evidence_ids=evidence_ids,
            )
        )
    return items


def collect_attention_items(
    *,
    reminders: Sequence[PrivateReminder] = (),
    messages: Sequence[PrivateMessage] = (),
    calendar_events: Sequence[PrivateCalendarEvent] = (),
    obligations: Sequence[Obligation] = (),
) -> list[AttentionItem]:
    """Collect unranked attention items from domain sources."""
    return [
        *items_from_reminders(reminders),
        *items_from_messages(messages),
        *items_from_calendar_events(calendar_events),
        *items_from_obligations(obligations),
    ]
