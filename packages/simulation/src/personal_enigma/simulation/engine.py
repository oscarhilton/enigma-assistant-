"""Event simulation engine (D5).

Loads a scenario timeline and emits events with ``at <= simulated now``.
Bound exclusively to a Demo storage root (ADR-005).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

from personal_enigma.simulation.checkpoints import (
    ensure_demo_layout,
    read_engine_state,
    reset_demo_storage,
    write_engine_state,
)
from personal_enigma.simulation.clock import SimulationClock
from personal_enigma.simulation.environment import (
    DemoEnvironment,
    EnvironmentMode,
    storage_root_for,
)
from personal_enigma.simulation.events import EmittedEvent, SimulationEvent
from personal_enigma.simulation.scenario import ScenarioPackage, load_scenario


@dataclass
class SimulationEngine:
    """Deterministic timeline driver for Demo Mode."""

    package: ScenarioPackage
    clock: SimulationClock
    storage_root: Path
    emitted: list[EmittedEvent] = field(default_factory=list)
    _pending: list[SimulationEvent] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if "private" in self.storage_root.parts and "demo" not in self.storage_root.parts:
            raise ValueError(
                "SimulationEngine must bind to a Demo storage root, not Private"
            )
        ensure_demo_layout(self.storage_root)
        self._pending = [
            SimulationEvent(
                id=e.id,
                at=e.at,
                type=e.type,
                source=e.source,
                payload=dict(e.payload),
            )
            for e in sorted(self.package.events, key=lambda ev: (ev.at, ev.id))
        ]
        self._persist()

    @classmethod
    def from_scenario(
        cls,
        path: Path | str,
        *,
        home: Path | None = None,
        clock: SimulationClock | None = None,
    ) -> SimulationEngine:
        package = load_scenario(path)
        root = storage_root_for(
            EnvironmentMode.DEMO,
            scenario=package.manifest.id,
            home=home,
        )
        initial = package.manifest.start_at
        sim_clock = clock if clock is not None else SimulationClock(initial=initial)
        if initial is not None and clock is None:
            sim_clock.set_time(initial)
        return cls(package=package, clock=sim_clock, storage_root=root)

    @classmethod
    def from_environment(
        cls,
        env: DemoEnvironment,
        package: ScenarioPackage,
    ) -> SimulationEngine:
        clock = env.clock if isinstance(env.clock, SimulationClock) else SimulationClock()
        return cls(package=package, clock=clock, storage_root=env.storage_root)

    @property
    def pending(self) -> tuple[SimulationEvent, ...]:
        return tuple(self._pending)

    def due_events(self) -> list[SimulationEvent]:
        now = self.clock.now()
        return [e for e in self._pending if e.at <= now]

    def emit_due(self) -> list[EmittedEvent]:
        """Emit all events with ``at <= now`` in stable order."""
        due = self.due_events()
        out: list[EmittedEvent] = []
        for event in due:
            self._pending.remove(event)
            record = EmittedEvent(
                id=event.id,
                at=event.at,
                type=event.type,
                source=event.source,
                payload=dict(event.payload),
                emitted_at=self.clock.now(),
            )
            self.emitted.append(record)
            out.append(record)
        self._persist()
        return out

    def advance_one_event(self) -> EmittedEvent | None:
        """Advance clock to the next pending event and emit it."""
        if not self._pending:
            return None
        nxt = self._pending[0]
        if nxt.at > self.clock.now():
            self.clock.advance_to(nxt.at)
        emitted = self.emit_due()
        return emitted[0] if emitted else None

    def advance_day(self) -> list[EmittedEvent]:
        """Advance one calendar day and emit newly due events."""
        self.clock.advance(timedelta(days=1))
        return self.emit_due()

    def run_batch(self, *, until_exhausted: bool = True) -> list[EmittedEvent]:
        """Emit all currently due events; optionally drain the full timeline."""
        collected: list[EmittedEvent] = []
        collected.extend(self.emit_due())
        if until_exhausted:
            while self._pending:
                step = self.advance_one_event()
                if step is None:
                    break
                collected.append(step)
            return list(self.emitted)
        return collected

    def reset(self) -> None:
        """Reset clock, pending queue, and demo storage under this root only."""
        initial = self.package.manifest.start_at
        self.clock.reset(initial)
        if initial is not None:
            self.clock.set_time(initial)
        self.emitted.clear()
        self._pending = [
            SimulationEvent(
                id=e.id,
                at=e.at,
                type=e.type,
                source=e.source,
                payload=dict(e.payload),
            )
            for e in sorted(self.package.events, key=lambda ev: (ev.at, ev.id))
        ]
        reset_demo_storage(self.storage_root)
        self._persist()

    def fingerprint(self) -> list[tuple[str, str]]:
        """Stable (id, at-iso) pairs for determinism checks."""
        return [(e.id, e.at.isoformat()) for e in self.emitted]

    def _persist(self) -> None:
        state: dict[str, Any] = {
            "scenario": self.package.manifest.id,
            "now": self.clock.now().isoformat(),
            "emitted_ids": [e.id for e in self.emitted],
            "pending_ids": [e.id for e in self._pending],
        }
        write_engine_state(self.storage_root, state)
        _ = read_engine_state(self.storage_root)
