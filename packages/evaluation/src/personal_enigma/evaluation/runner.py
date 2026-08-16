"""Evaluation runner stub (D7 owns full metrics wiring)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Placeholder report shape for Demo Mode evaluation."""

    scenario: str
    status: str = "stub"
    metrics: dict[str, float] = field(default_factory=dict)


class EvaluationRunner:
    """Smoke stub — D7 implements real metric aggregation."""

    def run(self, scenario: str) -> EvaluationReport:
        return EvaluationReport(scenario=scenario, status="not_implemented")
