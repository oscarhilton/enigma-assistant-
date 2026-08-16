"""Overdue / recency helpers that require an injected clock (ADR-006)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from personal_enigma.attention.kinds import AttentionKind
from personal_enigma.attention.protocol import AttentionItem
from personal_enigma.domain import PrivateReminder


class ClockLike(Protocol):
    def now(self) -> datetime: ...


def overdue_reminders(
    reminders: Sequence[PrivateReminder],
    *,
    clock: ClockLike,
) -> list[AttentionItem]:
    """Surface incomplete reminders whose due_at is before ``clock.now()``."""
    now = clock.now()
    items: list[AttentionItem] = []
    for reminder in reminders:
        if reminder.is_completed or reminder.due_at is None:
            continue
        if reminder.due_at >= now:
            continue
        items.append(
            AttentionItem(
                title=f"Overdue: {reminder.title}",
                body=f"Due {reminder.due_at.isoformat()}",
                kind=AttentionKind.EXPLICIT_REMINDER,
                score=1.0,
                evidence_ids=[reminder.id],
            )
        )
    return items
