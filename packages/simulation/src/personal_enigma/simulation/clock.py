"""Clock protocol and implementations ([ADR-006](../../../../docs/adr/006-clock-injection.md)).

Domain decisions that affect deadlines, commitments, overdue status, snoozing,
memory decay, event recency, attention escalation, retrieval recency, or
notification timing must obtain “now” from an injected ``Clock`` — never via
naked ``datetime.now()`` / ``utcnow()`` / ``date.today()`` / ``time.time()``.

Logging and telemetry may still use wall-clock.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Injectable clock — domain logic must not call ``datetime.now()`` directly."""

    def now(self) -> datetime:
        """Return the current timezone-aware instant for this environment."""
        ...


class SystemClock:
    """Wall-clock implementation for Private Mode."""

    def now(self) -> datetime:
        return datetime.now(tz=UTC)


class SimulationClock:
    """Controllable clock for Demo Mode.

    Advances only when callers invoke ``advance`` / ``advance_to`` / ``set_time``.
    Pause freezes further advances until ``resume``.
    """

    def __init__(self, initial: datetime | None = None) -> None:
        self._current = _ensure_aware(initial) if initial is not None else datetime(2026, 1, 1, tzinfo=UTC)
        self._paused = False
        self._initial = self._current

    def now(self) -> datetime:
        return self._current

    def set_time(self, when: datetime) -> None:
        """Jump to an absolute instant (always timezone-aware)."""
        self._current = _ensure_aware(when)

    def advance(self, delta: timedelta) -> datetime:
        """Advance by ``delta`` unless paused. Returns the new ``now()``."""
        if not self._paused:
            self._current = self._current + delta
        return self._current

    def advance_days(self, days: float) -> datetime:
        """Convenience: advance by whole or fractional days."""
        return self.advance(timedelta(days=days))

    def advance_to(self, when: datetime) -> datetime:
        """Advance forward to ``when``; never move backwards."""
        target = _ensure_aware(when)
        if target < self._current:
            raise ValueError(
                f"SimulationClock.advance_to cannot move backwards "
                f"(current={self._current.isoformat()}, target={target.isoformat()})"
            )
        if not self._paused:
            self._current = target
        return self._current

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    @property
    def paused(self) -> bool:
        return self._paused

    def reset(self, initial: datetime | None = None) -> None:
        """Reset to ``initial`` or the clock’s construction-time epoch."""
        self._paused = False
        self._current = _ensure_aware(initial) if initial is not None else self._initial


def _ensure_aware(when: datetime) -> datetime:
    if when.tzinfo is None:
        return when.replace(tzinfo=UTC)
    return when
