"""Assign synthetic timestamps to sanitised conversations (stub)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from personal_enigma.simulation.corpus.models import CorpusConversation
from personal_enigma.simulation.scenario import ScenarioEvent


def place_conversation_on_timeline(
    conversation: CorpusConversation,
    *,
    window_start: datetime,
    window_end: datetime,
    seed: str,
) -> list[ScenarioEvent]:
    """Map conversation messages into scenario mail events inside ``[start, end]``.

    Relative reply gaps are preserved (1h stub spacing) and clamped into the window.
    """
    if not conversation.messages:
        return []
    if window_start.tzinfo is None:
        window_start = window_start.replace(tzinfo=UTC)
    if window_end.tzinfo is None:
        window_end = window_end.replace(tzinfo=UTC)

    rng = Random(f"{seed}:{conversation.id}")
    span_seconds = max(1, int((window_end - window_start).total_seconds()))
    offset = rng.randrange(span_seconds)
    start = window_start + timedelta(seconds=offset)

    events: list[ScenarioEvent] = []
    for index, msg in enumerate(conversation.messages):
        at = start + timedelta(hours=index)
        if at > window_end:
            at = window_end
        events.append(
            ScenarioEvent(
                id=f"corpus:{conversation.id}:{index}",
                at=at,
                source="mail",
                type="email.receive",
                payload={
                    "id": f"{conversation.id}-{index}",
                    "thread_id": conversation.id,
                    "subject": msg.subject,
                    "body_text": msg.body_text,
                    "from": msg.sender_email,
                    "from_name": msg.sender_name,
                    "to": msg.recipient_emails,
                    "received_at": at.isoformat(),
                },
            )
        )
    return events
