"""Privacy ablation — full synthetic vs TransformedContext (Reasoning Value Gate / R06, R-L07)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from personal_enigma.evaluation.benchmark_budget import BenchmarkBudgetLedger
from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
from personal_enigma.evaluation.evaluation_truth import EvaluationTruth
from personal_enigma.evaluation.live_benchmark import (
    MAIN_REPS,
    build_live_transport,
    load_snapshot,
    run_live_benchmark,
)
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
    attention_delta: dict[str, float] = field(default_factory=dict)
    next_action_delta: dict[str, float] = field(default_factory=dict)
    transformed_passes_privacy_gate: bool = True
    checkpoint_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "transformed_aggregate": self.transformed_aggregate,
            "full_synthetic_aggregate": self.full_synthetic_aggregate,
            "delta": self.delta,
            "attention_delta": self.attention_delta,
            "next_action_delta": self.next_action_delta,
            "transformed_passes_privacy_gate": self.transformed_passes_privacy_gate,
            "checkpoint_ids": self.checkpoint_ids,
        }


def _metric_delta(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    keys = set(a) | set(b)
    return {k: b.get(k, 0.0) - a.get(k, 0.0) for k in keys}


def _attention_metrics(agg: dict[str, float]) -> dict[str, float]:
    return {
        "critical_recall": agg.get("critical_recall", agg.get("top3_critical_recall", 0.0)),
        "must_suppress_accuracy": agg.get("must_suppress_accuracy", 0.0),
        "top3_critical_recall": agg.get("top3_critical_recall", 0.0),
        "attention_accuracy": agg.get("attention_accuracy", 0.0),
    }


def _next_action_metrics(agg: dict[str, float]) -> dict[str, float]:
    return {
        "next_action_fit": agg.get("next_action_fit", 0.0),
        "actionability": agg.get("actionability", 0.0),
        "friction_reduction": agg.get("friction_reduction", 0.0),
    }


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
        attention_delta=_metric_delta(
            _attention_metrics(transformed_run.arm_b_aggregate),
            _attention_metrics(full_run.arm_b_aggregate),
        ),
        next_action_delta=_metric_delta(
            _next_action_metrics(transformed_run.arm_b_aggregate),
            _next_action_metrics(full_run.arm_b_aggregate),
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


def run_live_privacy_ablation(
    truth: EvaluationTruth,
    *,
    baseline_dir: str | Path,
    checkpoint_ids: list[str],
    live: bool,
    ledger: BenchmarkBudgetLedger,
    reps: int = MAIN_REPS,
) -> PrivacyAblationReport:
    """Live privacy ablation on hardest checkpoints (R-L07)."""
    transport_t = build_live_transport(live=live, ledger=ledger, phase="ablation-transformed")
    transformed = run_live_benchmark(
        truth,
        baseline_dir=baseline_dir,
        checkpoint_ids=checkpoint_ids,
        transport=transport_t,
        phase="ablation-transformed",
        reps=reps,
        context_mode="transformed",
        ledger=ledger,
    )
    transport_s = build_live_transport(live=live, ledger=ledger, phase="ablation-synthetic")
    full = run_live_benchmark(
        truth,
        baseline_dir=baseline_dir,
        checkpoint_ids=checkpoint_ids,
        transport=transport_s,
        phase="ablation-synthetic",
        reps=reps,
        context_mode="full_synthetic",
        ledger=ledger,
    )
    report = PrivacyAblationReport(
        transformed_aggregate=transformed.arm_b_aggregate,
        full_synthetic_aggregate=full.arm_b_aggregate,
        delta=_metric_delta(transformed.arm_b_aggregate, full.arm_b_aggregate),
        attention_delta=_metric_delta(
            _attention_metrics(transformed.arm_b_aggregate),
            _attention_metrics(full.arm_b_aggregate),
        ),
        next_action_delta=_metric_delta(
            _next_action_metrics(transformed.arm_b_aggregate),
            _next_action_metrics(full.arm_b_aggregate),
        ),
        checkpoint_ids=list(checkpoint_ids),
    )
    root = Path(baseline_dir)
    ids = checkpoint_ids or transformed.checkpoint_ids
    if ids:
        try:
            snap = load_snapshot(root, ids[0])
            assert_remote_safe(snapshot_to_transformed_context(snap))
        except Exception:
            report.transformed_passes_privacy_gate = False
    return report


__all__ = ["PrivacyAblationReport", "run_live_privacy_ablation", "run_privacy_ablation"]
