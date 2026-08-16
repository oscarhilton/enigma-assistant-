"""Deadline / why-now phases using an injected clock (ADR-006)."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol


class ClockLike(Protocol):
    def now(self) -> datetime: ...


class DeadlinePhase(StrEnum):
    FUTURE = "future"
    APPROACHING = "approaching"
    DUE_SOON = "due_soon"
    DUE_TODAY = "due_today"
    OVERDUE = "overdue"
    STALE = "stale"


_GLANCE: dict[DeadlinePhase, str] = {
    DeadlinePhase.FUTURE: "Upcoming",
    DeadlinePhase.APPROACHING: "Deadline approaching",
    DeadlinePhase.DUE_SOON: "Due soon",
    DeadlinePhase.DUE_TODAY: "Due today",
    DeadlinePhase.OVERDUE: "Overdue",
    DeadlinePhase.STALE: "Stale — past due",
}


def classify_deadline(
    due_at: datetime,
    *,
    now: datetime,
    approaching_window: timedelta = timedelta(days=7),
    due_soon: timedelta = timedelta(hours=48),
    stale_after: timedelta = timedelta(days=14),
) -> DeadlinePhase:
    """Classify ``due_at`` relative to ``now``.

    Past events become OVERDUE then STALE — never keep reading as
    "Deadline approaching".
    """
    if due_at.tzinfo is None and now.tzinfo is not None:
        due_at = due_at.replace(tzinfo=now.tzinfo)
    if now.tzinfo is None and due_at.tzinfo is not None:
        now = now.replace(tzinfo=due_at.tzinfo)

    delta = due_at - now
    if delta < -stale_after:
        return DeadlinePhase.STALE
    if delta < timedelta(0):
        return DeadlinePhase.OVERDUE
    if due_at.date() == now.date():
        return DeadlinePhase.DUE_TODAY
    if delta <= due_soon:
        return DeadlinePhase.DUE_SOON
    if delta <= approaching_window:
        return DeadlinePhase.APPROACHING
    return DeadlinePhase.FUTURE


def deadline_why_now_glance(phase: DeadlinePhase) -> str:
    return _GLANCE[phase]


def why_now_glance_for_deadline(due_at: datetime | None, *, now: datetime) -> str | None:
    if due_at is None:
        return None
    return deadline_why_now_glance(classify_deadline(due_at, now=now))


def parse_due_from_body(body: str) -> datetime | None:
    """Extract ISO due stamp from obligation attention body (``Due …``)."""
    marker = "Due "
    idx = body.find(marker)
    if idx < 0:
        return None
    stamp = body[idx + len(marker) :].split(";", 1)[0].strip()
    if not stamp:
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def timing_warrants_surface(
    due_at: datetime | None,
    *,
    now: datetime,
) -> bool:
    """True when a medium-priority item should interrupt because of timing."""
    if due_at is None:
        return False
    phase = classify_deadline(due_at, now=now)
    return phase in {
        DeadlinePhase.DUE_TODAY,
        DeadlinePhase.DUE_SOON,
        DeadlinePhase.OVERDUE,
        DeadlinePhase.APPROACHING,
    }
