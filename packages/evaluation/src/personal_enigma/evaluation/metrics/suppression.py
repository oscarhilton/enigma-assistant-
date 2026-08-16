"""Background / noise suppression metrics (corpus plan §38–39 / D07 amendment)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from personal_enigma.evaluation.ground_truth import (
    GroundTruthCorpus,
    ScenarioSignalClass,
)
from personal_enigma.evaluation.metrics.scale import (
    attention_compression_ratio,
    background_suppression_rate,
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


@dataclass(frozen=True, slots=True)
class NoiseSuppressionMetrics:
    """Plan §38–40 headline fields for enigma-eval ``metrics.json``."""

    background_count: int
    background_correctly_ignored: int
    background_suppression_rate: float
    noise_count: int
    noise_correctly_ignored: int
    noise_suppression_rate: float
    background_false_alerts: int
    noise_false_alerts: int
    message_count: int
    background_false_alerts_per_1000: float
    false_alert_ids: tuple[str, ...]
    signals_considered: int
    items_surfaced: int
    attention_compression_ratio: float
    max_per_1000: float
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "background_count": self.background_count,
            "background_correctly_ignored": self.background_correctly_ignored,
            "background_suppression_rate": self.background_suppression_rate,
            "noise_count": self.noise_count,
            "noise_correctly_ignored": self.noise_correctly_ignored,
            "noise_suppression_rate": self.noise_suppression_rate,
            "background_false_alerts": self.background_false_alerts,
            "noise_false_alerts": self.noise_false_alerts,
            "message_count": self.message_count,
            "background_false_alerts_per_1000": self.background_false_alerts_per_1000,
            "false_alert_ids": list(self.false_alert_ids),
            "signals_considered": self.signals_considered,
            "items_surfaced": self.items_surfaced,
            "attention_compression_ratio": self.attention_compression_ratio,
            "max_per_1000": self.max_per_1000,
            "passed": self.passed,
        }


def _non_attention_evidence_ids(
    truth: GroundTruthCorpus,
    *,
    signal_class: ScenarioSignalClass | None = None,
) -> set[str]:
    """Evidence that must never surface (expected_attention=false)."""
    ids: set[str] = set()
    for signal in truth.signals:
        if signal.expected_attention:
            continue
        if signal_class is not None and signal.signal_class != signal_class:
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


def _false_alert_ids_for(
    alerts: Sequence[SurfacedAlert], suppressed: set[str]
) -> list[str]:
    return [
        alert.id for alert in alerts if _alert_hits_suppressed(alert, suppressed)
    ]


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
    false_ids = _false_alert_ids_for(alerts, suppressed)
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


def compute_noise_suppression_metrics(
    truth: GroundTruthCorpus,
    alerts: Sequence[SurfacedAlert],
    *,
    message_count: int | None = None,
    background_count: int | None = None,
    noise_count: int | None = None,
    signals_considered: int | None = None,
    max_per_1000: float = MAX_BACKGROUND_FALSE_ALERTS_PER_1000,
) -> NoiseSuppressionMetrics:
    """Derive Background Suppression Rate, false alerts / 1k, and compression."""
    bg_ids = _non_attention_evidence_ids(
        truth, signal_class=ScenarioSignalClass.BACKGROUND
    )
    noise_ids = _non_attention_evidence_ids(
        truth, signal_class=ScenarioSignalClass.NOISE
    )
    bg_total = len(bg_ids) if background_count is None else background_count
    noise_total = len(noise_ids) if noise_count is None else noise_count
    combined = bg_ids | noise_ids
    msg_count = (
        (bg_total + noise_total) if message_count is None else message_count
    )
    if msg_count < 0:
        raise ValueError("message_count must be >= 0")

    bg_false_ids = _false_alert_ids_for(alerts, bg_ids)
    noise_false_ids = _false_alert_ids_for(alerts, noise_ids)
    # An alert citing both classes counts once in the combined headline rate.
    combined_false_ids = _false_alert_ids_for(alerts, combined)

    bg_false = len(bg_false_ids)
    noise_false = len(noise_false_ids)
    bg_ignored = max(0, bg_total - bg_false)
    noise_ignored = max(0, noise_total - noise_false)
    items = len(alerts)
    considered = msg_count if signals_considered is None else signals_considered
    per_1000 = (
        (len(combined_false_ids) / msg_count * 1000.0) if msg_count else 0.0
    )
    return NoiseSuppressionMetrics(
        background_count=bg_total,
        background_correctly_ignored=bg_ignored,
        background_suppression_rate=background_suppression_rate(
            background_total=bg_total, correctly_ignored=bg_ignored
        ),
        noise_count=noise_total,
        noise_correctly_ignored=noise_ignored,
        noise_suppression_rate=background_suppression_rate(
            background_total=noise_total, correctly_ignored=noise_ignored
        ),
        background_false_alerts=bg_false,
        noise_false_alerts=noise_false,
        message_count=msg_count,
        background_false_alerts_per_1000=per_1000,
        false_alert_ids=tuple(combined_false_ids),
        signals_considered=considered,
        items_surfaced=items,
        attention_compression_ratio=attention_compression_ratio(
            signals_considered=considered, items_surfaced=items
        ),
        max_per_1000=max_per_1000,
        passed=per_1000 <= max_per_1000 + 1e-9,
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
    "NoiseSuppressionMetrics",
    "background_false_alerts_per_1000",
    "compute_noise_suppression_metrics",
    "quiet_day_attention_empty",
]
