"""A/B storyline recall under background noise (D08c / D07 amendment)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from personal_enigma.evaluation.regression import DEFAULT_THRESHOLDS, RegressionResult


@dataclass(frozen=True, slots=True)
class StorylineRecallAB:
    """Critical-recall comparison: spine-only (A) vs spine+background (B)."""

    spine_critical_recall: float
    with_background_critical_recall: float
    drop: float
    max_drop: float
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "spine_critical_recall": self.spine_critical_recall,
            "with_background_critical_recall": self.with_background_critical_recall,
            "drop": self.drop,
            "max_drop": self.max_drop,
            "passed": self.passed,
        }


def storyline_recall_under_noise(
    spine_metrics: dict[str, Any],
    with_background_metrics: dict[str, Any],
    *,
    max_critical_recall_drop: float | None = None,
) -> StorylineRecallAB:
    """Compare critical recall with vs without background (≤1 pp default)."""
    limit = (
        DEFAULT_THRESHOLDS["critical_recall_drop"]
        if max_critical_recall_drop is None
        else max_critical_recall_drop
    )
    spine_att = spine_metrics.get("attention", spine_metrics)
    bg_att = with_background_metrics.get("attention", with_background_metrics)
    spine_recall = float(spine_att.get("critical_recall", 1.0))
    bg_recall = float(bg_att.get("critical_recall", 1.0))
    drop = max(0.0, spine_recall - bg_recall)
    return StorylineRecallAB(
        spine_critical_recall=spine_recall,
        with_background_critical_recall=bg_recall,
        drop=drop,
        max_drop=limit,
        passed=drop <= limit + 1e-9,
    )


def compare_storyline_ab(
    spine_metrics: dict[str, Any],
    with_background_metrics: dict[str, Any],
    *,
    max_critical_recall_drop: float | None = None,
) -> RegressionResult:
    """Regression-shaped wrapper around :func:`storyline_recall_under_noise`."""
    result = storyline_recall_under_noise(
        spine_metrics,
        with_background_metrics,
        max_critical_recall_drop=max_critical_recall_drop,
    )
    violations: list[str] = []
    if not result.passed:
        violations.append(
            "storyline critical_recall dropped "
            f"{result.spine_critical_recall:.3f} → "
            f"{result.with_background_critical_recall:.3f} "
            f"(drop {result.drop:.3f} > {result.max_drop:.3f})"
        )
    return RegressionResult(passed=result.passed, violations=violations)


__all__ = [
    "StorylineRecallAB",
    "compare_storyline_ab",
    "storyline_recall_under_noise",
]
