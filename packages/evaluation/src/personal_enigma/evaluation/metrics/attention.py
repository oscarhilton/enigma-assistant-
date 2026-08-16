"""Attention metrics for Demo Mode evaluation."""

from __future__ import annotations

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

from personal_enigma.evaluation.ground_truth import (
    CRITICAL_IMPORTANCE,
    GroundTruthCorpus,
    MissedObligation,
    detect_missed_obligations,
)
from personal_enigma.evaluation.observations import SurfacedAlert


@dataclass(frozen=True, slots=True)
class AttentionMetrics:
    critical_recall: float
    precision: float
    duplicate_rate: float
    stale_alert_rate: float
    early_noise_rate: float
    late_alert_rate: float
    expected_critical: int
    surfaced_critical: int
    useful_alerts: int
    total_alerts: int
    duplicate_alerts: int
    stale_alerts: int
    missed: list[MissedObligation]

    def as_dict(self) -> dict[str, float | int]:
        return {
            "critical_recall": self.critical_recall,
            "precision": self.precision,
            "duplicate_rate": self.duplicate_rate,
            "stale_alert_rate": self.stale_alert_rate,
            "early_noise_rate": self.early_noise_rate,
            "late_alert_rate": self.late_alert_rate,
            "expected_critical": self.expected_critical,
            "surfaced_critical": self.surfaced_critical,
            "useful_alerts": self.useful_alerts,
            "total_alerts": self.total_alerts,
            "duplicate_alerts": self.duplicate_alerts,
            "stale_alerts": self.stale_alerts,
            "missed_count": len(self.missed),
        }


def critical_recall(*, predicted: int, expected: int) -> float:
    """Important obligations surfaced / important obligations total."""
    if expected <= 0:
        return 1.0
    return min(1.0, predicted / expected)


def precision(*, useful: int, total: int) -> float:
    """Useful alerts / all alerts."""
    if total <= 0:
        return 1.0
    return useful / total


def duplicate_rate(*, duplicates: int, total: int) -> float:
    """Duplicate attention items / total attention items."""
    if total <= 0:
        return 0.0
    return duplicates / total


def stale_alert_rate(*, stale: int, total: int) -> float:
    """Alerts remaining after the underlying issue is resolved."""
    if total <= 0:
        return 0.0
    return stale / total


def _surfaced_obligation_ids(alerts: Sequence[SurfacedAlert]) -> set[str]:
    ids: set[str] = set()
    for alert in alerts:
        ids.update(alert.obligation_ids)
        # Allow alert id to match an obligation id directly
        ids.add(alert.id)
    return ids


def _expected_critical_ids(truth: GroundTruthCorpus, *, at: datetime) -> list[str]:
    expected: list[str] = []
    for obligation in truth.obligations:
        if obligation.importance not in CRITICAL_IMPORTANCE:
            continue
        if not obligation.is_open_at(at):
            continue
        window = truth.window_for(obligation.id)
        if window is not None:
            if not window.is_active_at(at):
                continue
        elif at < obligation.created_at:
            continue
        expected.append(obligation.id)
    return expected


def _is_useful(alert: SurfacedAlert, expected: Collection[str]) -> bool:
    if alert.duplicate_of:
        return False
    if alert.resolved_underlying:
        return False
    if any(oid in expected for oid in alert.obligation_ids):
        return True
    return alert.id in expected


def compute_attention_metrics(
    truth: GroundTruthCorpus,
    alerts: Sequence[SurfacedAlert],
    *,
    at: datetime,
) -> AttentionMetrics:
    """Wire ground-truth missed-obligation detection into attention metrics."""
    surfaced = _surfaced_obligation_ids(alerts)
    expected_ids = _expected_critical_ids(truth, at=at)
    expected_set = set(expected_ids)
    missed = detect_missed_obligations(
        truth,
        surfaced_obligation_ids=surfaced,
        at=at,
    )
    surfaced_critical = len(expected_set & surfaced)

    total = len(alerts)
    duplicates = sum(1 for a in alerts if a.duplicate_of)
    stale = sum(1 for a in alerts if a.resolved_underlying)
    useful = sum(1 for a in alerts if _is_useful(a, expected_set))

    # Early noise: surfaced before window earliest (when a window exists)
    early = 0
    late = 0
    for alert in alerts:
        for oid in alert.obligation_ids or ([alert.id] if alert.id in expected_set else []):
            window = truth.window_for(oid)
            if window is None or alert.surfaced_at is None:
                continue
            if alert.surfaced_at < window.earliest:
                early += 1
            elif alert.surfaced_at > window.latest:
                late += 1

    return AttentionMetrics(
        critical_recall=critical_recall(
            predicted=surfaced_critical,
            expected=len(expected_ids),
        ),
        precision=precision(useful=useful, total=total),
        duplicate_rate=duplicate_rate(duplicates=duplicates, total=total),
        stale_alert_rate=stale_alert_rate(stale=stale, total=total),
        early_noise_rate=(early / total) if total else 0.0,
        late_alert_rate=(late / len(expected_ids)) if expected_ids else 0.0,
        expected_critical=len(expected_ids),
        surfaced_critical=surfaced_critical,
        useful_alerts=useful,
        total_alerts=total,
        duplicate_alerts=duplicates,
        stale_alerts=stale,
        missed=missed,
    )


def rank_with_attention_engine(
    items: Iterable[object],
) -> list[object]:
    """Optional hook: rank AttentionItem-like objects via the real engine."""
    from personal_enigma.attention import AttentionItem, HeuristicAttentionEngine

    engine = HeuristicAttentionEngine()
    typed: list[AttentionItem] = []
    for item in items:
        if isinstance(item, AttentionItem):
            typed.append(item)
            continue
        dump = getattr(item, "model_dump", None)
        if callable(dump):
            typed.append(AttentionItem.model_validate(dump()))
            continue
        raise TypeError(f"Cannot rank non-AttentionItem: {type(item)!r}")
    return list(engine.rank(typed))


__all__ = [
    "AttentionMetrics",
    "compute_attention_metrics",
    "critical_recall",
    "duplicate_rate",
    "precision",
    "rank_with_attention_engine",
    "stale_alert_rate",
]
