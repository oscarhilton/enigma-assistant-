"""Merge reminders, email follow-ups, and calendar meetings into Obligations.

Calendar lists are passed through ``dedupe_calendar_events`` (M12) before
clustering so Google/Apple duplicates do not surface as separate attention
items. Evidence refs stay local (ids + short titles only).

Surface-policy rules (attention wind tunnel):
- Scheduled existence alone is not an obligation (calendar-only clusters drop).
- Past calendar events resolve (injected ``now``).
- Machine noise / newsletters never become INFERRED_COMMITMENT.
- Merge requires ≥2 distinctive token overlap (no ``with``-style glue).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from personal_enigma.attention import AttentionItem, AttentionKind, ui_priority_for_kind
from personal_enigma.attention.classify import message_attention_kind
from personal_enigma.attention.noise import looks_like_machine_noise
from personal_enigma.dedupe import dedupe_calendar_events
from personal_enigma.domain import (
    CalendarEvidence,
    EmailEvidence,
    Obligation,
    ObligationEvidence,
    PrivateCalendarEvent,
    PrivateMessage,
    PrivateReminder,
    ReminderEvidence,
)


class _ClockLike(Protocol):
    def now(self) -> datetime: ...

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "re",
        "fw",
        "fwd",
        "can",
        "you",
        "your",
        "before",
        "after",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "meeting",
        "please",
        "thanks",
        "hi",
        "hello",
        "with",
        "for",
        "from",
        "next",
        "week",
        "to",
        "of",
        "on",
        "in",
        "at",
        "and",
        "or",
        "is",
        "are",
        "be",
        "me",
        "my",
        "we",
        "us",
        "our",
        "this",
        "that",
        "slot",
        "sync",
        "quick",
        "claim",
        "congrats",
        "reward",
        "finished",
        "hold",
        "calendar",
        "package",
        "delivery",
        "security",
        "notice",
        "off",
        "forever",
        "really",
        "only",
        "confirmed",
        "login",
        "build",
        "weekly",
        "new",
        "sign",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str | None) -> frozenset[str]:
    if not text:
        return frozenset()
    raw = _TOKEN_RE.findall(text.casefold())
    return frozenset(t for t in raw if len(t) > 1 and t not in _STOPWORDS)


def _related(a: frozenset[str], b: frozenset[str]) -> bool:
    """Require ≥2 shared distinctive tokens — no single-token glue merges."""
    if not a or not b:
        return False
    return len(a & b) >= 2


@dataclass
class _Signal:
    tokens: frozenset[str]
    reminder: PrivateReminder | None = None
    message: PrivateMessage | None = None
    event: PrivateCalendarEvent | None = None
    mail_kind: AttentionKind | None = None


@dataclass
class _Cluster:
    signals: list[_Signal] = field(default_factory=list)

    @property
    def tokens(self) -> frozenset[str]:
        merged: set[str] = set()
        for signal in self.signals:
            merged |= signal.tokens
        return frozenset(merged)


def _confidence(
    *,
    has_reminder: bool,
    has_email: bool,
    has_calendar: bool,
    pending_reply: bool = False,
) -> float:
    if pending_reply and not has_reminder:
        return 0.4
    kinds = sum((has_reminder, has_email, has_calendar))
    if kinds >= 3:
        return 0.98
    if kinds == 2:
        if has_reminder:
            return 0.9
        return 0.8
    if has_reminder:
        return 0.7
    if has_calendar:
        return 0.6
    return 0.55


def _pick_description(
    reminders: list[PrivateReminder],
    messages: list[PrivateMessage],
    events: list[PrivateCalendarEvent],
) -> str:
    # Prefer actionable sources over bare calendar titles.
    if reminders:
        return reminders[0].title
    if messages:
        return messages[0].subject or messages[0].snippet or "Follow-up"
    if events:
        return events[0].title
    return "Obligation"


def _pick_due_at(
    reminders: list[PrivateReminder],
    events: list[PrivateCalendarEvent],
) -> datetime | None:
    due_dates = [r.due_at for r in reminders if r.due_at is not None]
    if due_dates:
        return min(due_dates)
    if events:
        return min(e.start_at for e in events)
    return None


def _calendar_fingerprint(event: PrivateCalendarEvent) -> tuple[str, datetime]:
    return (event.title.casefold().strip(), event.start_at)


def _build_obligation(cluster: _Cluster) -> Obligation | None:
    reminders = [s.reminder for s in cluster.signals if s.reminder is not None]
    messages = [s.message for s in cluster.signals if s.message is not None]
    events = [s.event for s in cluster.signals if s.event is not None]
    mail_kinds = [s.mail_kind for s in cluster.signals if s.mail_kind is not None]

    # Hard rule: scheduled existence alone is not an obligation.
    if events and not reminders and not messages:
        return None

    unique_events: list[PrivateCalendarEvent] = []
    seen_fps: set[tuple[str, datetime]] = set()
    for event in events:
        fp = _calendar_fingerprint(event)
        if fp in seen_fps:
            continue
        seen_fps.add(fp)
        unique_events.append(event)

    evidence: list[ObligationEvidence] = []
    for reminder in reminders:
        evidence.append(
            ReminderEvidence(reminder_id=reminder.id, title=reminder.title),
        )
    for message in messages:
        evidence.append(
            EmailEvidence(message_id=message.id, subject=message.subject),
        )
    for event in unique_events:
        evidence.append(
            CalendarEvidence(event_id=event.id, title=event.title),
        )

    pending_reply = (
        bool(mail_kinds)
        and all(k is AttentionKind.PENDING_REPLY for k in mail_kinds)
        and not reminders
    )

    return Obligation(
        description=_pick_description(reminders, messages, unique_events),
        due_at=_pick_due_at(reminders, unique_events),
        evidence=evidence,
        confidence=_confidence(
            has_reminder=bool(reminders),
            has_email=bool(messages),
            has_calendar=bool(unique_events),
            pending_reply=pending_reply,
        ),
    )


def _cluster_signals(signals: list[_Signal]) -> list[_Cluster]:
    clusters: list[_Cluster] = []
    for signal in signals:
        placed = False
        for cluster in clusters:
            if _related(signal.tokens, cluster.tokens):
                cluster.signals.append(signal)
                placed = True
                break
        if not placed:
            clusters.append(_Cluster(signals=[signal]))
    return clusters


def merge_sources(
    *,
    reminders: Sequence[PrivateReminder] = (),
    messages: Sequence[PrivateMessage] = (),
    calendar_events: Sequence[PrivateCalendarEvent] = (),
    now: datetime | None = None,
    clock: _ClockLike | None = None,
) -> list[Obligation]:
    """Merge cross-source signals into Obligations with typed evidence.

    Calendar events are deduped via M12 ``dedupe_calendar_events`` first.
    When ``now`` / ``clock`` is set, past calendar events (``end_at < now``)
    are dropped.
    """
    effective_now = now if now is not None else (clock.now() if clock is not None else None)
    events = dedupe_calendar_events(list(calendar_events))
    if effective_now is not None:
        events = [e for e in events if e.end_at >= effective_now]

    signals: list[_Signal] = []
    for reminder in reminders:
        if reminder.is_completed:
            continue
        signals.append(
            _Signal(
                tokens=_tokens(reminder.title) | _tokens(reminder.notes),
                reminder=reminder,
            )
        )
    for message in messages:
        if looks_like_machine_noise(message):
            continue
        mail_kind = message_attention_kind(message)
        if mail_kind is None:
            continue
        signals.append(
            _Signal(
                tokens=_tokens(message.subject)
                | _tokens(message.snippet)
                | _tokens(message.body_text),
                message=message,
                mail_kind=mail_kind,
            )
        )
    for event in events:
        signals.append(
            _Signal(
                tokens=_tokens(event.title) | _tokens(event.description),
                event=event,
            )
        )

    clusters = _cluster_signals(signals)
    obligations: list[Obligation] = []
    for cluster in clusters:
        obligation = _build_obligation(cluster)
        if obligation is not None:
            obligations.append(obligation)
    obligations.sort(key=lambda o: (-o.confidence, o.description.casefold()))
    return obligations


def obligation_attention_item(obligation: Obligation) -> AttentionItem:
    """Build a single attention item with a combined evidence narrative."""
    parts: list[str] = []
    evidence_ids: list[str] = []
    has_reminder = False
    has_email = False
    has_calendar = False

    for evidence in obligation.evidence:
        if evidence.kind == "reminder":
            has_reminder = True
            evidence_ids.append(evidence.reminder_id)
            label = evidence.title or evidence.reminder_id
            parts.append(f"Reminder: {label}")
        elif evidence.kind == "email":
            has_email = True
            evidence_ids.append(evidence.message_id)
            label = evidence.subject or evidence.message_id
            parts.append(f"Email: {label}")
        elif evidence.kind == "calendar":
            has_calendar = True
            evidence_ids.append(evidence.event_id)
            label = evidence.title or evidence.event_id
            parts.append(f"Calendar: {label}")
        elif evidence.kind == "note":
            evidence_ids.append(evidence.note_id)
            label = evidence.title or evidence.note_id
            parts.append(f"Note: {label}")

    if obligation.due_at is not None:
        parts.append(f"Due {obligation.due_at.isoformat()}")

    if has_reminder:
        kind = AttentionKind.EXPLICIT_REMINDER
    elif has_calendar and has_email:
        kind = AttentionKind.INFERRED_OBLIGATION
    elif has_calendar:
        kind = AttentionKind.CALENDAR_OBLIGATION
    elif has_email and obligation.confidence <= 0.45:
        kind = AttentionKind.PENDING_REPLY
    elif has_email:
        kind = AttentionKind.INFERRED_COMMITMENT
    else:
        kind = AttentionKind.INFERRED_OBLIGATION

    score = obligation.confidence
    if kind is AttentionKind.PENDING_REPLY:
        score = min(score, 0.35)

    return AttentionItem(
        title=obligation.description,
        body="; ".join(parts),
        kind=kind,
        score=score,
        evidence_ids=evidence_ids,
        priority=ui_priority_for_kind(kind),
    )


def merge_sources_to_attention(
    *,
    reminders: Sequence[PrivateReminder] = (),
    messages: Sequence[PrivateMessage] = (),
    calendar_events: Sequence[PrivateCalendarEvent] = (),
    now: datetime | None = None,
    clock: _ClockLike | None = None,
) -> list[AttentionItem]:
    """Merge sources and emit one attention item per resulting Obligation."""
    obligations = merge_sources(
        reminders=reminders,
        messages=messages,
        calendar_events=calendar_events,
        now=now,
        clock=clock,
    )
    return [obligation_attention_item(o) for o in obligations]
