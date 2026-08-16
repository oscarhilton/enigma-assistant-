"""Passages and corpus helpers for configurable local indexing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from personal_enigma.embeddings.chunking import chunk_text

SourceKind = Literal["email", "note", "reminder", "calendar"]


@dataclass(frozen=True)
class Passage:
    """A chunk of private corpus text ready for local embedding."""

    id: str
    text: str
    source_type: SourceKind
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class IndexConfig:
    """Which corpora to index. Non-Notes sources work independently of Notes (M13)."""

    include_email: bool = True
    include_notes: bool = True
    include_reminders: bool = True
    include_calendar: bool = True


def _chunks_for(
    *,
    prefix: str,
    text: str,
    source_type: SourceKind,
    metadata: dict[str, str],
    max_chars: int,
    overlap: int,
) -> list[Passage]:
    pieces = chunk_text(text, max_chars=max_chars, overlap=overlap)
    return [
        Passage(
            id=f"{prefix}:{idx}",
            text=piece,
            source_type=source_type,
            metadata=dict(metadata),
        )
        for idx, piece in enumerate(pieces)
    ]


def passages_from_email(
    *,
    message_id: str,
    subject: str | None = None,
    body_text: str | None = None,
    snippet: str | None = None,
    max_chars: int = 500,
    overlap: int = 50,
) -> list[Passage]:
    parts = [p for p in (subject, body_text or snippet) if p]
    text = "\n".join(parts).strip()
    if not text:
        return []
    return _chunks_for(
        prefix=f"email:{message_id}",
        text=text,
        source_type="email",
        metadata={"message_id": message_id},
        max_chars=max_chars,
        overlap=overlap,
    )


def passages_from_note(
    *,
    note_id: str,
    title: str,
    body_text: str,
    max_chars: int = 500,
    overlap: int = 50,
) -> list[Passage]:
    text = f"{title}\n{body_text}".strip()
    if not text:
        return []
    return _chunks_for(
        prefix=f"note:{note_id}",
        text=text,
        source_type="note",
        metadata={"note_id": note_id},
        max_chars=max_chars,
        overlap=overlap,
    )


def passages_from_reminder(
    *,
    reminder_id: str,
    title: str,
    notes: str | None = None,
    max_chars: int = 500,
    overlap: int = 50,
) -> list[Passage]:
    text = f"{title}\n{notes or ''}".strip()
    if not text:
        return []
    return _chunks_for(
        prefix=f"reminder:{reminder_id}",
        text=text,
        source_type="reminder",
        metadata={"reminder_id": reminder_id},
        max_chars=max_chars,
        overlap=overlap,
    )


def passages_from_calendar(
    *,
    event_id: str,
    title: str,
    description: str | None = None,
    max_chars: int = 500,
    overlap: int = 50,
) -> list[Passage]:
    text = f"{title}\n{description or ''}".strip()
    if not text:
        return []
    return _chunks_for(
        prefix=f"calendar:{event_id}",
        text=text,
        source_type="calendar",
        metadata={"event_id": event_id},
        max_chars=max_chars,
        overlap=overlap,
    )


def filter_passages(passages: list[Passage], config: IndexConfig) -> list[Passage]:
    allowed: set[SourceKind] = set()
    if config.include_email:
        allowed.add("email")
    if config.include_notes:
        allowed.add("note")
    if config.include_reminders:
        allowed.add("reminder")
    if config.include_calendar:
        allowed.add("calendar")
    return [p for p in passages if p.source_type in allowed]
