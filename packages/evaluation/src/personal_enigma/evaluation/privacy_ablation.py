"""Privacy ablation — full synthetic vs TransformedContext (Reasoning Value Gate / R06)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
from personal_enigma.evaluation.evaluation_truth import EvaluationTruth
from personal_enigma.evaluation.llm_benchmark import (
    run_llm_benchmark,
    snapshot_to_transformed_context,
)
from personal_enigma.reasoning.privacy_gate import assert_remote_safe


@dataclass
class PrivacyAblationReport:
    transformed_aggregate: dict[str, float] = field(default_factory=dict)
    full_synthetic_aggregate: dict[str, float] = field(default_factory=dict)
    delta: dict[str, float] = field(default_factory=dict)
    transformed_passes_privacy_gate: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "transformed_aggregate": self.transformed_aggregate,
            "full_synthetic_aggregate": self.full_synthetic_aggregate,
            "delta": self.delta,
            "transformed_passes_privacy_gate": self.transformed_passes_privacy_gate,
        }


def _metric_delta(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    keys = set(a) | set(b)
    return {k: b.get(k, 0.0) - a.get(k, 0.0) for k in keys}


def run_privacy_ablation(
    truth: EvaluationTruth,
    *,
    baseline_dir: str | Path,
    replay_fixture: str | Path,
    checkpoint_ids: list[str] | None = None,
) -> PrivacyAblationReport:
    transformed_run = run_llm_benchmark(
        truth,
        baseline_dir=baseline_dir,
        replay_fixture=replay_fixture,
        checkpoint_ids=checkpoint_ids,
        context_mode="transformed",
    )
    full_run = run_llm_benchmark(
        truth,
        baseline_dir=baseline_dir,
        replay_fixture=replay_fixture,
        checkpoint_ids=checkpoint_ids,
        context_mode="full_synthetic",
    )
    report = PrivacyAblationReport(
        transformed_aggregate=transformed_run.arm_b_aggregate,
        full_synthetic_aggregate=full_run.arm_b_aggregate,
        delta=_metric_delta(
            transformed_run.arm_b_aggregate, full_run.arm_b_aggregate
        ),
    )
    root = Path(baseline_dir)
    ids = checkpoint_ids or [r.checkpoint_id for r in transformed_run.arm_b]
    try:
        snap = load_checkpoint_snapshot(root / f"{ids[0]}.json")
        assert_remote_safe(snapshot_to_transformed_context(snap))
    except Exception:
        report.transformed_passes_privacy_gate = False
    return report


__all__ = ["PrivacyAblationReport", "run_privacy_ablation"]
