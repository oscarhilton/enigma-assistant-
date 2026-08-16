"""Merge reminders, email follow-ups, and calendar meetings into Obligations.

Calendar lists are passed through ``dedupe_calendar_events`` (M12) before
clustering so Google/Apple duplicates do not surface as separate attention
items. Evidence refs stay local (ids + short titles only).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from personal_enigma.attention import AttentionItem, AttentionKind
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
    }
)

# Shared machine-sludge tokens must not glue PrizeVault/BuildCloud/… into one
# INFERRED_COMMITMENT. Distinctive topical tokens still allow human merges.
_MACHINE_GENERIC_TOKENS = frozenset(
    {
        "account",
        "notification",
        "notifications",
        "unsubscribe",
        "update",
        "updates",
        "newsletter",
        "digest",
        "promo",
        "promotion",
        "claim",
        "reward",
        "weekly",
        "security",
        "notice",
        "build",
        "pipeline",
        "succeeded",
        "finished",
        "receipt",
        "order",
        "delivery",
        "shipped",
        "confirm",
        "confirmed",
        "action",
        "needed",
        "view",
        "logs",
        "offer",
        "off",
        "percent",
        "free",
        "win",
        "winner",
        "click",
        "now",
        "today",
        "this",
        "week",
        "from",
        "with",
        "for",
        "and",
        "any",
        "time",
        "anytime",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str | None) -> frozenset[str]:
    if not text:
        return frozenset()
    raw = _TOKEN_RE.findall(text.casefold())
    return frozenset(t for t in raw if len(t) > 1 and t not in _STOPWORDS)


def _related(a: frozenset[str], b: frozenset[str]) -> bool:
    if not a or not b:
        return False
    overlap = a & b
    if len(overlap) >= 2:
        return True
    # Single shared distinctive token is enough when both sides are short.
    if len(overlap) == 1 and min(len(a), len(b)) <= 3:
        return True
    return False


def _related_email_pair(a: frozenset[str], b: frozenset[str]) -> bool:
    """Email↔email relatedness ignores shared machine-sludge tokens."""
    if not a or not b:
        return False
    distinctive = (a & b) - _MACHINE_GENERIC_TOKENS
    if len(distinctive) >= 2:
        return True
    if len(distinctive) == 1 and min(len(a), len(b)) <= 3:
        return True
    return False


def _message_thread_id(message: PrivateMessage) -> str | None:
    thread = message.thread_id
    if thread is None:
        return None
    cleaned = str(thread).strip()
    return cleaned or None


@dataclass
class _Signal:
    tokens: frozenset[str]
    reminder: PrivateReminder | None = None
    message: PrivateMessage | None = None
    event: PrivateCalendarEvent | None = None


@dataclass
class _Cluster:
    signals: list[_Signal] = field(default_factory=list)

    @property
    def tokens(self) -> frozenset[str]:
        merged: set[str] = set()
        for signal in self.signals:
            merged |= signal.tokens
        return frozenset(merged)


def _confidence(*, has_reminder: bool, has_email: bool, has_calendar: bool) -> float:
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
    if reminders:
        return reminders[0].title
    if events:
        return events[0].title
    if messages:
        return messages[0].subject or messages[0].snippet or "Follow-up"
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


def _build_obligation(cluster: _Cluster) -> Obligation:
    reminders = [s.reminder for s in cluster.signals if s.reminder is not None]
    messages = [s.message for s in cluster.signals if s.message is not None]
    events = [s.event for s in cluster.signals if s.event is not None]

    # Collapse residual provider duplicates inside a cluster (M12 stub-safe).
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

    return Obligation(
        description=_pick_description(reminders, messages, unique_events),
        due_at=_pick_due_at(reminders, unique_events),
        evidence=evidence,
        confidence=_confidence(
            has_reminder=bool(reminders),
            has_email=bool(messages),
            has_calendar=bool(unique_events),
        ),
    )


def _signals_related(left: _Signal, right: _Signal) -> bool:
    """Decide whether two email signals belong together."""
    left_thread = _message_thread_id(left.message) if left.message else None
    right_thread = _message_thread_id(right.message) if right.message else None
    if left_thread and right_thread and left_thread == right_thread:
        return True
    return _related_email_pair(left.tokens, right.tokens)


def _should_join(signal: _Signal, cluster: _Cluster) -> bool:
    """Join when related to any member; email↔email uses sludge-aware tokens."""
    for member in cluster.signals:
        if signal.message is not None and member.message is not None:
            if _signals_related(signal, member):
                return True
        elif _related(signal.tokens, member.tokens):
            return True
    return False


def _cluster_signals(signals: list[_Signal]) -> list[_Cluster]:
    clusters: list[_Cluster] = []
    for signal in signals:
        placed = False
        for cluster in clusters:
            if _should_join(signal, cluster):
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
) -> list[Obligation]:
    """Merge cross-source signals into Obligations with typed evidence.

    Calendar events are deduped via M12 ``dedupe_calendar_events`` first.
    """
    events = dedupe_calendar_events(list(calendar_events))
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
        signals.append(
            _Signal(
                tokens=_tokens(message.subject)
                | _tokens(message.snippet)
                | _tokens(message.body_text),
                message=message,
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
    obligations = [_build_obligation(cluster) for cluster in clusters]
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
    elif has_calendar:
        kind = AttentionKind.CALENDAR_OBLIGATION
    elif has_email:
        kind = AttentionKind.INFERRED_COMMITMENT
    else:
        kind = AttentionKind.INFERRED_OBLIGATION

    return AttentionItem(
        title=obligation.description,
        body="; ".join(parts),
        kind=kind,
        score=obligation.confidence,
        evidence_ids=evidence_ids,
    )


def merge_sources_to_attention(
    *,
    reminders: Sequence[PrivateReminder] = (),
    messages: Sequence[PrivateMessage] = (),
    calendar_events: Sequence[PrivateCalendarEvent] = (),
) -> list[AttentionItem]:
    """Merge sources and emit one attention item per resulting Obligation."""
    obligations = merge_sources(
        reminders=reminders,
        messages=messages,
        calendar_events=calendar_events,
    )
    return [obligation_attention_item(o) for o in obligations]
