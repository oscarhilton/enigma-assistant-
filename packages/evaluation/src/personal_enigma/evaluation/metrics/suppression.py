"""Background / noise false-alert headline metrics (D08d / D07 amendment)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from personal_enigma.evaluation.ground_truth import (
    GroundTruthCorpus,
    ScenarioSignalClass,
)
from personal_enigma.evaluation.observations import SurfacedAlert

# Agreed Demo Mode ceiling for mini / demo profiles (quiet-day hard-gates at 0).
MAX_BACKGROUND_FALSE_ALERTS_PER_1000 = 1.0


@dataclass(frozen=True, slots=True)
class BackgroundFalseAlertRate:
    """Incorrect attention caused by background/noise per 1,000 messages."""

    false_alerts: int
    message_count: int
    per_1000: float
    max_per_1000: float
    passed: bool
    false_alert_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "false_alerts": self.false_alerts,
            "message_count": self.message_count,
            "background_false_alerts_per_1000": self.per_1000,
            "max_per_1000": self.max_per_1000,
            "passed": self.passed,
            "false_alert_ids": list(self.false_alert_ids),
        }


def _non_attention_evidence_ids(truth: GroundTruthCorpus) -> set[str]:
    """Evidence that must never surface (background + noise, expected_attention=false)."""
    ids: set[str] = set()
    for signal in truth.signals:
        if signal.expected_attention:
            continue
        if signal.signal_class in {
            ScenarioSignalClass.BACKGROUND,
            ScenarioSignalClass.NOISE,
        }:
            ids.add(signal.evidence_id)
    return ids


def _alert_hits_suppressed(
    alert: SurfacedAlert, suppressed: set[str]
) -> bool:
    if alert.id in suppressed:
        return True
    return any(eid in suppressed for eid in alert.evidence_ids)


def background_false_alerts_per_1000(
    truth: GroundTruthCorpus,
    alerts: Sequence[SurfacedAlert],
    *,
    message_count: int,
    max_per_1000: float = MAX_BACKGROUND_FALSE_ALERTS_PER_1000,
) -> BackgroundFalseAlertRate:
    """Count alerts that cite background/noise evidence; normalise per 1k messages.

    Quiet-day / no-obligation days must pass with ``false_alerts == 0`` (and thus
    ``per_1000 == 0``). Inventing attention because the inbox is full is a
    product-level failure.
    """
    if message_count < 0:
        raise ValueError("message_count must be >= 0")
    suppressed = _non_attention_evidence_ids(truth)
    false_ids: list[str] = []
    for alert in alerts:
        if _alert_hits_suppressed(alert, suppressed):
            false_ids.append(alert.id)
    count = len(false_ids)
    per_1000 = (count / message_count * 1000.0) if message_count else 0.0
    return BackgroundFalseAlertRate(
        false_alerts=count,
        message_count=message_count,
        per_1000=per_1000,
        max_per_1000=max_per_1000,
        passed=per_1000 <= max_per_1000 + 1e-9,
        false_alert_ids=tuple(false_ids),
    )


def quiet_day_attention_empty(
    *,
    attention_items: Sequence[object],
    obligation_count: int,
) -> bool:
    """Hard gate: zero genuine obligations ⇒ attention surface must be empty."""
    if obligation_count != 0:
        raise ValueError("quiet_day_attention_empty requires obligation_count == 0")
    return len(attention_items) == 0


__all__ = [
    "MAX_BACKGROUND_FALSE_ALERTS_PER_1000",
    "BackgroundFalseAlertRate",
    "background_false_alerts_per_1000",
    "quiet_day_attention_empty",
]
