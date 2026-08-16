"""Assign synthetic timestamps to sanitised conversations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from personal_enigma.simulation.corpus.models import CorpusConversation
from personal_enigma.simulation.scenario import ScenarioEvent


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _working_hour_start(rng: Random, day: datetime) -> datetime:
    """Prefer weekday working hours; occasional evening / weekend mail."""
    # 0=Mon … 6=Sun
    weekday = day.weekday()
    roll = rng.random()
    if weekday >= 5:  # weekend — lighter / later
        hour = rng.choice([10, 11, 14, 16, 19])
        minute = rng.randrange(0, 60)
    elif roll < 0.12:  # evening weekday
        hour = rng.choice([18, 19, 20, 21])
        minute = rng.randrange(0, 60)
    else:
        hour = rng.choice([8, 9, 10, 11, 13, 14, 15, 16])
        minute = rng.randrange(0, 60)
    return day.replace(hour=hour, minute=minute, second=rng.randrange(0, 60), microsecond=0)


def place_conversation_on_timeline(
    conversation: CorpusConversation,
    *,
    window_start: datetime,
    window_end: datetime,
    seed: str,
    self_email: str | None = None,
) -> list[ScenarioEvent]:
    """Map conversation messages into scenario mail events inside ``[start, end]``.

    Relative reply gaps are preserved (deterministic 1–5h spacing). When the
    natural schedule would exceed ``window_end``, timestamps stay strictly
    increasing so merge sort by ``(at, id)`` cannot reorder replies.

    Messages from ``self_email`` (when set) are emitted as ``email.send``.
    """
    if not conversation.messages:
        return []
    window_start = _aware(window_start)
    window_end = _aware(window_end)
    if window_end <= window_start:
        raise ValueError("window_end must be after window_start")

    rng = Random(f"{seed}:{conversation.id}")
    span_days = max(1, (window_end.date() - window_start.date()).days)
    day_offset = rng.randrange(span_days)
    day = datetime(
        window_start.year,
        window_start.month,
        window_start.day,
        tzinfo=UTC,
    ) + timedelta(days=day_offset)
    start = _working_hour_start(rng, day)
    if start < window_start:
        start = window_start + timedelta(minutes=rng.randrange(0, 60))
    if start > window_end:
        start = window_end - timedelta(minutes=max(1, len(conversation.messages)))

    self_key = self_email.lower() if self_email else None
    events: list[ScenarioEvent] = []
    cursor: datetime | None = None
    for index, msg in enumerate(conversation.messages):
        if index == 0:
            at = start
        else:
            gap_hours = 1 + rng.randrange(0, 5)
            at = (cursor or start) + timedelta(hours=gap_hours)
        if at > window_end:
            at = window_end
        if cursor is not None and at <= cursor:
            at = cursor + timedelta(seconds=1)
        cursor = at
        is_send = self_key is not None and msg.sender_email.strip().lower() == self_key
        event_type = "email.send" if is_send else "email.receive"
        payload: dict = {
            "id": f"{conversation.id}-{index}",
            "thread_id": conversation.id,
            "subject": msg.subject,
            "body_text": msg.body_text,
            "from": msg.sender_email,
            "from_name": msg.sender_name,
            "to": msg.recipient_emails,
        }
        if is_send:
            payload["sent_at"] = at.isoformat()
        else:
            payload["received_at"] = at.isoformat()
        events.append(
            ScenarioEvent(
                id=f"corpus:{conversation.id}:{index}",
                at=at,
                source="mail",
                type=event_type,
                payload=payload,
            )
        )
    return events


def place_conversations_on_timeline(
    conversations: list[CorpusConversation],
    *,
    window_start: datetime,
    window_end: datetime,
    seed: str,
    self_email: str | None = None,
) -> list[ScenarioEvent]:
    """Place many conversations and return a chronologically sorted event list."""
    events: list[ScenarioEvent] = []
    for conv in conversations:
        events.extend(
            place_conversation_on_timeline(
                conv,
                window_start=window_start,
                window_end=window_end,
                seed=seed,
                self_email=self_email,
            )
        )
    return sorted(events, key=lambda e: (e.at, e.id))
