"""Clock protocol and stubs ([ADR-006](../../../../docs/adr/006-clock-injection.md)).

Full SimulationClock controls and domain migration are D2; D1 ships stubs so
environment scaffolding can depend on a stable import path.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Injectable clock — domain logic must not call ``datetime.now()`` directly."""

    def now(self) -> datetime:
        """Return the current time for this environment."""
        ...


class SystemClock:
    """Wall-clock implementation for Private Mode."""

    def now(self) -> datetime:
        return datetime.now(tz=UTC)


class SimulationClock:
    """Controllable clock stub for Demo Mode (D2 completes semantics)."""

    def __init__(self, initial: datetime | None = None) -> None:
        self._current = initial if initial is not None else datetime(2026, 1, 1, tzinfo=UTC)
        self._paused = False

    def now(self) -> datetime:
        return self._current

    def set_time(self, when: datetime) -> None:
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        self._current = when

    def advance(self, delta: timedelta) -> None:
        if self._paused:
            return
        self._current = self._current + delta

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def reset(self, initial: datetime | None = None) -> None:
        self._paused = False
        self._current = initial if initial is not None else datetime(2026, 1, 1, tzinfo=UTC)
