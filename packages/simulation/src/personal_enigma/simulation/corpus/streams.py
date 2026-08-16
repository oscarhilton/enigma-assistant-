"""Multi-stream mail inputs for SyntheticMailSource (D04 amendment / D08b)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from personal_enigma.simulation.scenario import ScenarioEvent, ScenarioPackage
from personal_enigma.simulation.sources import events_for_source, package_events


@dataclass
class CanonicalScenarioStream:
    """Authored scenario mail events (canonical story)."""

    events: ScenarioPackage | Sequence[ScenarioEvent]
    until: datetime | None = None

    def scenario_events(self) -> list[ScenarioEvent]:
        return events_for_source(
            package_events(self.events),
            source="mail",
            until=self.until,
        )


@dataclass
class CorpusBackgroundStream:
    """Sanitised corpus background — evaluator class stays outside payloads."""

    events: Sequence[ScenarioEvent] = field(default_factory=list)
    # Evaluator-only hint; never copied onto PrivateMessage / ChangeBatch items.
    signal_class: str = "background"

    def scenario_events(self) -> list[ScenarioEvent]:
        return list(self.events)


@dataclass
class GeneratedNoiseStream:
    """Locally generated noise templates (D08d scaffold)."""

    events: Sequence[ScenarioEvent] = field(default_factory=list)
    signal_class: str = "noise"

    def scenario_events(self) -> list[ScenarioEvent]:
        return list(self.events)


MailStream = CanonicalScenarioStream | CorpusBackgroundStream | GeneratedNoiseStream


def merge_stream_events(streams: Sequence[MailStream]) -> list[ScenarioEvent]:
    """Merge streams chronologically. Does not attach signal_class to payloads."""
    merged: list[ScenarioEvent] = []
    for stream in streams:
        merged.extend(stream.scenario_events())
    return sorted(merged, key=lambda e: (e.at, e.id))


def strip_evaluator_keys(payload: dict[str, Any]) -> dict[str, Any]:
    """Ensure evaluator-only keys never leak into source payloads."""
    forbidden = {
        "signal_class",
        "source_class",
        "expected_attention",
        "scenario_source",
        "is_important",
    }
    return {k: v for k, v in payload.items() if k not in forbidden}
