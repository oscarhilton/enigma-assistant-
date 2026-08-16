"""Local embedding index job stubs (no hosted embedding APIs)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from personal_enigma.embeddings import (
    FakeEmbeddingModel,
    IndexConfig,
    InMemoryVectorIndex,
    Passage,
    RetrievalPipeline,
    filter_passages,
    passages_from_calendar,
    passages_from_email,
    passages_from_note,
    passages_from_reminder,
)


@dataclass(frozen=True)
class EmbeddingIndexJobResult:
    indexed: int
    by_source: dict[str, int] = field(default_factory=dict)


def build_default_pipeline() -> RetrievalPipeline:
    """CI / offline default: deterministic fake embedder + in-memory index."""
    return RetrievalPipeline(model=FakeEmbeddingModel(), index=InMemoryVectorIndex())


def _passages_from_records(
    *,
    emails: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    reminders: list[dict[str, Any]],
    calendar_events: list[dict[str, Any]],
) -> list[Passage]:
    passages: list[Passage] = []
    for email in emails:
        passages.extend(
            passages_from_email(
                message_id=str(email["id"]),
                subject=email.get("subject"),
                body_text=email.get("body_text"),
                snippet=email.get("snippet"),
            )
        )
    for note in notes:
        passages.extend(
            passages_from_note(
                note_id=str(note["id"]),
                title=str(note.get("title") or ""),
                body_text=str(note.get("body_text") or ""),
            )
        )
    for reminder in reminders:
        passages.extend(
            passages_from_reminder(
                reminder_id=str(reminder["id"]),
                title=str(reminder.get("title") or ""),
                notes=reminder.get("notes"),
            )
        )
    for event in calendar_events:
        passages.extend(
            passages_from_calendar(
                event_id=str(event["id"]),
                title=str(event.get("title") or ""),
                description=event.get("description"),
            )
        )
    return passages


def run_embedding_index_job(
    *,
    emails: list[dict[str, Any]] | None = None,
    notes: list[dict[str, Any]] | None = None,
    reminders: list[dict[str, Any]] | None = None,
    calendar_events: list[dict[str, Any]] | None = None,
    config: IndexConfig | None = None,
    pipeline: RetrievalPipeline | None = None,
) -> tuple[RetrievalPipeline, EmbeddingIndexJobResult]:
    """Index configured corpora into a local vector index.

    Accepts plain record dicts so email/reminders/calendar can be indexed even
    when Notes (M13) is incomplete. Always uses local embeddings only.
    """
    cfg = config or IndexConfig()
    pipe = pipeline or build_default_pipeline()
    passages = filter_passages(
        _passages_from_records(
            emails=list(emails or []),
            notes=list(notes or []),
            reminders=list(reminders or []),
            calendar_events=list(calendar_events or []),
        ),
        cfg,
    )
    indexed = pipe.index_passages(passages)
    by_source: dict[str, int] = {}
    for passage in passages:
        by_source[passage.source_type] = by_source.get(passage.source_type, 0) + 1
    return pipe, EmbeddingIndexJobResult(indexed=indexed, by_source=by_source)
