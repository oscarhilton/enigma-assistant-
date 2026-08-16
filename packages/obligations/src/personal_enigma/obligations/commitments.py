"""Commitment tracking state machine (M16).

Tracks inferred commitments vs explicit reminders over time. Apple-only
evidence is enough for the MVP path — Gmail is optional.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from personal_enigma.attention import AttentionItem, AttentionKind
from personal_enigma.domain import (
    NoteEvidence,
    PrivateMessage,
    PrivateNote,
    PrivateReminder,
)


class CommitmentKind(StrEnum):
    INFERRED = "inferred"
    EXPLICIT_REMINDER = "explicit_reminder"


class CommitmentState(StrEnum):
    OPEN = "open"
    STALE = "stale"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Commitment(BaseModel):
    id: str
    description: str
    kind: CommitmentKind
    state: CommitmentState = CommitmentState.OPEN
    due_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    evidence_ids: list[str] = Field(default_factory=list)
    prerequisite_note_id: str | None = None
    prerequisite_met: bool = False


class CommitmentTracker:
    """In-memory commitment tracker — persist via M00a hooks later."""

    def __init__(self) -> None:
        self._items: dict[str, Commitment] = {}

    def upsert_from_reminder(
        self,
        reminder: PrivateReminder,
        *,
        now: datetime,
    ) -> Commitment:
        cid = f"rem:{reminder.id}"
        existing = self._items.get(cid)
        if reminder.is_completed:
            commitment = Commitment(
                id=cid,
                description=reminder.title,
                kind=CommitmentKind.EXPLICIT_REMINDER,
                state=CommitmentState.COMPLETED,
                due_at=reminder.due_at,
                created_at=existing.created_at if existing else now,
                updated_at=now,
                evidence_ids=[reminder.id],
            )
        else:
            commitment = Commitment(
                id=cid,
                description=reminder.title,
                kind=CommitmentKind.EXPLICIT_REMINDER,
                state=CommitmentState.OPEN,
                due_at=reminder.due_at,
                created_at=existing.created_at if existing else now,
                updated_at=now,
                evidence_ids=[reminder.id],
            )
        self._items[cid] = commitment
        return commitment

    def upsert_inferred_from_message(
        self,
        message: PrivateMessage,
        *,
        now: datetime,
        description: str | None = None,
    ) -> Commitment:
        cid = f"msg:{message.id}"
        text = description or message.subject or message.snippet or "Inferred commitment"
        existing = self._items.get(cid)
        commitment = Commitment(
            id=cid,
            description=text,
            kind=CommitmentKind.INFERRED,
            state=CommitmentState.OPEN,
            due_at=None,
            created_at=existing.created_at if existing else now,
            updated_at=now,
            evidence_ids=[message.id],
        )
        self._items[cid] = commitment
        return commitment

    def register_deferred_note(
        self,
        note: PrivateNote,
        *,
        description: str,
        now: datetime,
    ) -> Commitment:
        """Notes deferred-task pattern: wait until prerequisite is marked met."""
        cid = f"note:{note.id}"
        existing = self._items.get(cid)
        commitment = Commitment(
            id=cid,
            description=description,
            kind=CommitmentKind.INFERRED,
            state=CommitmentState.OPEN,
            due_at=None,
            created_at=existing.created_at if existing else now,
            updated_at=now,
            evidence_ids=[note.id],
            prerequisite_note_id=note.id,
            prerequisite_met=False,
        )
        self._items[cid] = commitment
        return commitment

    def mark_prerequisite_met(self, note_id: str, *, now: datetime) -> list[Commitment]:
        updated: list[Commitment] = []
        for commitment in self._items.values():
            if commitment.prerequisite_note_id == note_id and not commitment.prerequisite_met:
                commitment.prerequisite_met = True
                commitment.updated_at = now
                updated.append(commitment)
        return updated

    def apply_follow_up_email(
        self,
        message: PrivateMessage,
        commitment_id: str,
        *,
        now: datetime,
    ) -> Commitment | None:
        commitment = self._items.get(commitment_id)
        if commitment is None:
            return None
        if message.id not in commitment.evidence_ids:
            commitment.evidence_ids.append(message.id)
        commitment.updated_at = now
        return commitment

    def refresh_staleness(self, *, now: datetime) -> list[Commitment]:
        stale: list[Commitment] = []
        for commitment in self._items.values():
            if commitment.state != CommitmentState.OPEN:
                continue
            if commitment.prerequisite_note_id and not commitment.prerequisite_met:
                continue
            if commitment.due_at is not None and commitment.due_at < now:
                commitment.state = CommitmentState.STALE
                commitment.updated_at = now
                stale.append(commitment)
        return stale

    def open_and_stale(self) -> list[Commitment]:
        return [
            c
            for c in self._items.values()
            if c.state in (CommitmentState.OPEN, CommitmentState.STALE)
        ]

    def stale_attention_items(self) -> list[AttentionItem]:
        items: list[AttentionItem] = []
        for commitment in self._items.values():
            if commitment.state != CommitmentState.STALE:
                continue
            kind = (
                AttentionKind.EXPLICIT_REMINDER
                if commitment.kind == CommitmentKind.EXPLICIT_REMINDER
                else AttentionKind.INFERRED_COMMITMENT
            )
            items.append(
                AttentionItem(
                    title=f"Stale: {commitment.description}",
                    body="Due date passed; still open.",
                    kind=kind,
                    score=0.85 if commitment.kind == CommitmentKind.EXPLICIT_REMINDER else 0.7,
                    evidence_ids=list(commitment.evidence_ids),
                )
            )
        return items


def commitment_kind_label(kind: CommitmentKind) -> Literal["inferred", "explicit_reminder"]:
    return kind.value  # type: ignore[return-value]


# Re-export NoteEvidence for callers linking note prerequisites.
__all__ = [
    "Commitment",
    "CommitmentKind",
    "CommitmentState",
    "CommitmentTracker",
    "NoteEvidence",
    "commitment_kind_label",
]
