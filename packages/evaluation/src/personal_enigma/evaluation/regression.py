"""Regression helpers — compare a run against a baseline snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RegressionResult:
    passed: bool
    violations: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "violations": list(self.violations)}


DEFAULT_THRESHOLDS = {
    "critical_recall_drop": 0.01,
    "duplicate_rate_rise": 0.02,
    "cost_increase_ratio": 0.25,
    "background_false_alerts_per_1000": 1.0,
}


def compare_to_baseline(
    metrics: dict[str, Any],
    baseline: dict[str, Any],
    *,
    thresholds: dict[str, float] | None = None,
) -> RegressionResult:
    """Detect attention/privacy/cost regressions against a stored baseline."""
    limits = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    violations: list[str] = []

    attention = metrics.get("attention", metrics)
    base_att = baseline.get("attention", baseline)

    recall = float(attention.get("critical_recall", 1.0))
    base_recall = float(base_att.get("critical_recall", recall))
    if recall + 1e-9 < base_recall - limits["critical_recall_drop"]:
        violations.append(
            f"critical_recall fell from {base_recall:.3f} to {recall:.3f}"
        )

    dup = float(attention.get("duplicate_rate", 0.0))
    base_dup = float(base_att.get("duplicate_rate", dup))
    if dup > base_dup + limits["duplicate_rate_rise"]:
        violations.append(
            f"duplicate_rate rose from {base_dup:.3f} to {dup:.3f}"
        )

    privacy = metrics.get("privacy", {})
    leaks = int(privacy.get("direct_identifier_leaks", 0))
    if leaks != 0:
        violations.append(f"direct_identifier_leaks must be 0, got {leaks}")

    cost = metrics.get("cost", {})
    total = float(cost.get("total_usd", 0.0))
    base_cost = float(baseline.get("cost", {}).get("total_usd", total))
    if base_cost > 0 and total > base_cost * (1.0 + limits["cost_increase_ratio"]):
        violations.append(
            f"cost increased from {base_cost:.4f} to {total:.4f} "
            f"(>{limits['cost_increase_ratio']:.0%} threshold)"
        )

    suppression = metrics.get("suppression", {})
    if suppression:
        rate = float(suppression.get("background_false_alerts_per_1000", 0.0))
        ceiling = float(limits["background_false_alerts_per_1000"])
        if rate > ceiling + 1e-9:
            violations.append(
                "background_false_alerts_per_1000 "
                f"{rate:.3f} exceeds ceiling {ceiling:.3f}"
            )

    return RegressionResult(passed=not violations, violations=violations)


__all__ = [
    "DEFAULT_THRESHOLDS",
    "RegressionResult",
    "compare_to_baseline",
]
