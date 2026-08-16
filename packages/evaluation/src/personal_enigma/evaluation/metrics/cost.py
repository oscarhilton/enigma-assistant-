"""Cost metrics stubs with daily/weekly/monthly/annual extrapolation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from personal_enigma.evaluation.observations import CostEvent


@dataclass(frozen=True, slots=True)
class CostMetrics:
    total_usd: float
    input_tokens: int
    output_tokens: int
    by_category: dict[str, float] = field(default_factory=dict)
    daily_usd: float = 0.0
    weekly_usd: float = 0.0
    monthly_usd: float = 0.0
    annual_usd: float = 0.0

    def as_dict(self) -> dict[str, float | int | dict[str, float]]:
        return {
            "total_usd": self.total_usd,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "by_category": dict(self.by_category),
            "daily_usd": self.daily_usd,
            "weekly_usd": self.weekly_usd,
            "monthly_usd": self.monthly_usd,
            # Corpus plan §48 — stub monthly cost of a simulated user.
            "cost_per_simulated_month": self.monthly_usd,
            "annual_usd": self.annual_usd,
        }


def total_usd(*, amount: float) -> float:
    """Stub total inference cost in USD."""
    return amount


def compute_cost_metrics(
    events: list[CostEvent],
    *,
    scenario_days: float = 1.0,
) -> CostMetrics:
    """Aggregate cost events and extrapolate usage (stub-friendly)."""
    by_category: dict[str, float] = defaultdict(float)
    total = 0.0
    inp = 0
    out = 0
    for event in events:
        total += event.estimated_usd
        inp += event.input_tokens
        out += event.output_tokens
        by_category[event.category] += event.estimated_usd

    days = max(scenario_days, 1e-9)
    daily = total / days
    return CostMetrics(
        total_usd=total_usd(amount=total),
        input_tokens=inp,
        output_tokens=out,
        by_category=dict(by_category),
        daily_usd=daily,
        weekly_usd=daily * 7,
        monthly_usd=daily * 30,
        annual_usd=daily * 365,
    )


__all__ = [
    "CostMetrics",
    "compute_cost_metrics",
    "total_usd",
]
