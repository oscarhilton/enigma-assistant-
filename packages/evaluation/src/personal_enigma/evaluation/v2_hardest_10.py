"""R-L09 step 5 — live hardest-10 triple-column ablation + decision rules."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from personal_enigma.evaluation.benchmark_budget import BenchmarkBudgetLedger
from personal_enigma.evaluation.evaluation_truth import EvaluationTruth
from personal_enigma.evaluation.live_benchmark import (
    MAIN_REPS,
    LiveBenchmarkReport,
    build_live_transport,
    run_live_benchmark,
)
from personal_enigma.evaluation.llm_benchmark import JudgeArm

V2ReportDir = Path("reports/reasoning-gate-live")
HARDEST_10_CHECKPOINTS = [
    "cp-2026-01-20T11:00",
    "cp-2026-01-19T10:00",
    "cp-2026-01-11T11:00",
    "cp-2026-01-10T14:00",
    "cp-2026-01-15T13:00",
    "cp-2026-01-25T17:00",
    "cp-2026-01-25T10:00",
    "cp-2026-01-24T15:00",
    "cp-2026-01-24T09:00",
    "cp-2026-01-23T12:00",
]
REGRESSION_INSPECTION_CPS = ["cp-2026-01-19T10:00", "cp-2026-01-20T11:00"]
V1_BASELINE_RECALL = 0.85
FULL_SYNTHETIC_RECALL = 1.0
V2_REGATE_BUDGET_CAP = 0.45

V2RegateDecision = Literal["strong", "promising", "no_movement", "blocked"]


@dataclass
class TripleColumnAblationReport:
    checkpoint_ids: list[str]
    evaluation_transformed_v1: dict[str, float] = field(default_factory=dict)
    evaluation_transformed_v2: dict[str, float] = field(default_factory=dict)
    full_synthetic: dict[str, float] = field(default_factory=dict)
    v1_privacy_gate_passed: bool = False
    v2_privacy_gate_passed: bool = True
    privacy_failure_rate_v2: float = 0.0
    total_cost_usd: float = 0.0
    regression_semantics: dict[str, Any] = field(default_factory=dict)
    invalid_experiments: dict[str, bool] = field(default_factory=dict)
    decision: V2RegateDecision = "blocked"
    decision_rationale: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_ids": self.checkpoint_ids,
            "columns": {
                "evaluation_transformed_v1": self.evaluation_transformed_v1,
                "evaluation_transformed_v2": self.evaluation_transformed_v2,
                "full_synthetic": self.full_synthetic,
            },
            "v1_privacy_gate_passed": self.v1_privacy_gate_passed,
            "v2_privacy_gate_passed": self.v2_privacy_gate_passed,
            "privacy_failure_rate_v2": self.privacy_failure_rate_v2,
            "total_cost_usd": self.total_cost_usd,
            "regression_semantics": self.regression_semantics,
            "invalid_experiments": self.invalid_experiments,
            "decision": self.decision,
            "decision_rationale": self.decision_rationale,
            "decision_rules": {
                "strong": "critical_recall >= 0.95 AND must_suppress >= 0.95",
                "promising": "critical_recall materially > 0.85 AND must_suppress >= 0.95 "
                "AND privacy_failures=0 AND no new v2 regressions",
                "no_movement": "~0.85 recall → falsify hypothesis for this model/benchmark",
            },
        }


def _token_audit_semantics(report: LiveBenchmarkReport, cp_id: str) -> dict[str, Any]:
    reps = report.arm_b_reps.get(cp_id, [])
    if not reps:
        return {"checkpoint_id": cp_id, "error": "no reps"}
    rep = reps[0]
    arm = rep.arm_result
    out: dict[str, Any] = {"checkpoint_id": cp_id, "candidates": []}
    for judgement in arm.candidate_judgements:
        if judgement.candidate_id != "item-obligation_token_audit":
            continue
        sem = judgement.semantic_output
        if sem is None:
            out["candidates"].append(
                {
                    "candidate_id": judgement.candidate_id,
                    "parse_error": judgement.parse_error,
                }
            )
            continue
        out["candidates"].append(
            {
                "candidate_id": judgement.candidate_id,
                "time_sensitivity": sem.time_sensitivity,
                "actionability_now": sem.actionability_now,
                "obligation_strength": sem.obligation_strength,
                "importance": sem.importance,
                "reason_codes": list(sem.reason_codes),
                "policy_decision": None,
            }
        )
    return out


def extract_regression_semantics(
    v1_report: LiveBenchmarkReport,
    v2_report: LiveBenchmarkReport,
) -> dict[str, Any]:
    """Jan 19/20 token-audit semantic judge features — v1 vs v2 side by side."""
    return {
        cp_id: {
            "evaluation_transformed_v1": _token_audit_semantics(v1_report, cp_id),
            "evaluation_transformed_v2": _token_audit_semantics(v2_report, cp_id),
        }
        for cp_id in REGRESSION_INSPECTION_CPS
    }


def evaluate_v2_regate_decision(
    *,
    v2_aggregate: dict[str, float],
    privacy_failure_rate: float,
    new_v2_regressions: int = 0,
) -> tuple[V2RegateDecision, str]:
    recall = float(v2_aggregate.get("critical_recall", 0.0))
    suppress = float(v2_aggregate.get("must_suppress_accuracy", 0.0))

    if privacy_failure_rate > 0.0:
        return (
            "blocked",
            f"Privacy failures={privacy_failure_rate:.1%} — do not proceed to main.",
        )

    if suppress < 0.95:
        return (
            "blocked",
            f"MUST_SUPPRESS={suppress:.3f} < 0.95 guardrail — do not proceed.",
        )

    if new_v2_regressions > 0:
        return (
            "blocked",
            f"{new_v2_regressions} new critical regressions vs Arm A — inspect before main.",
        )

    if recall >= 0.95:
        return (
            "strong",
            f"STRONG: recall={recall:.3f}, suppress={suppress:.3f} — gap largely closed vs "
            f"full_synthetic={FULL_SYNTHETIC_RECALL:.2f}.",
        )

    if recall > V1_BASELINE_RECALL + 0.02:
        return (
            "promising",
            f"PROMISING: recall={recall:.3f} > v1 baseline {V1_BASELINE_RECALL:.2f}, "
            f"suppress={suppress:.3f}. Eligible for main-only rerun consideration.",
        )

    return (
        "no_movement",
        f"NO MOVEMENT: recall={recall:.3f} ≈ v1 {V1_BASELINE_RECALL:.2f} — "
        "falsify semantic-preservation hypothesis for this model/benchmark; stop.",
    )


def _column_invalid(report: LiveBenchmarkReport) -> bool:
    """True when every rep for every checkpoint is experiment_invalid."""
    all_reps = [r for reps in report.arm_b_reps.values() for r in reps]
    if not all_reps:
        return False
    return all(r.experiment_invalid for r in all_reps)


def _aggregate_excluding_invalid(report: LiveBenchmarkReport) -> dict[str, float]:
    from personal_enigma.evaluation.live_benchmark import aggregate_b_reps

    return aggregate_b_reps(report.arm_b_reps)


def run_live_triple_column_hardest_10(
    truth: EvaluationTruth,
    *,
    baseline_dir: str | Path,
    checkpoint_ids: list[str] | None = None,
    live: bool,
    ledger: BenchmarkBudgetLedger | None = None,
    judge_arm: JudgeArm = "b2",
    reps: int = MAIN_REPS,
    output_dir: Path | None = None,
) -> TripleColumnAblationReport:
    """Live hardest-10: v1 (frozen) vs v2 (production) vs full_synthetic."""
    cp_ids = list(checkpoint_ids or HARDEST_10_CHECKPOINTS)
    out_dir = output_dir or V2ReportDir
    out_dir.mkdir(parents=True, exist_ok=True)

    ledger = ledger or BenchmarkBudgetLedger(
        hard_cap_usd=V2_REGATE_BUDGET_CAP,
        audit_dir=out_dir,
    )

    reports: dict[str, LiveBenchmarkReport] = {}
    for mode in (
        "evaluation_transformed_v1",
        "evaluation_transformed_v2",
        "full_synthetic",
    ):
        transport = build_live_transport(
            live=live,
            ledger=ledger,
            phase=f"hardest-10-{mode}",
            judge_arm=judge_arm,
        )
        reports[mode] = run_live_benchmark(
            truth,
            baseline_dir=baseline_dir,
            checkpoint_ids=cp_ids,
            transport=transport,
            phase=f"hardest-10-{mode}",
            reps=reps,
            context_mode=mode,  # type: ignore[arg-type]
            ledger=ledger,
            judge_arm=judge_arm,
            prompt_privacy="legacy_v1" if mode == "evaluation_transformed_v1" else "remote_safe",
        )
        _write_json(out_dir / f"hardest-10-{mode}.json", reports[mode].as_dict())

    v1, v2, full = (
        reports["evaluation_transformed_v1"],
        reports["evaluation_transformed_v2"],
        reports["full_synthetic"],
    )

    invalid_experiments = {
        "evaluation_transformed_v1": _column_invalid(v1),
        "evaluation_transformed_v2": _column_invalid(v2),
        "full_synthetic": _column_invalid(full),
    }

    v2_privacy_failures = sum(
        1
        for reps_list in v2.arm_b_reps.values()
        for rep in reps_list
        if rep.parse_error and "privacy" in (rep.parse_error or "").lower()
    )
    total_reps = sum(len(r) for r in v2.arm_b_reps.values()) or 1
    privacy_rate = v2_privacy_failures / total_reps

    new_regressions = max(0, v2.outcome_counts.regressions - v1.outcome_counts.regressions)

    if invalid_experiments["evaluation_transformed_v1"]:
        decision: V2RegateDecision = "blocked"
        rationale = (
            "INVALID: evaluation_transformed_v1 column — prompt build or parse failures; "
            "excluded from aggregate recall (no Arm A fallback)."
        )
    elif invalid_experiments["evaluation_transformed_v2"]:
        decision = "blocked"
        rationale = "INVALID: evaluation_transformed_v2 column — all reps experiment_invalid."
    else:
        decision, rationale = evaluate_v2_regate_decision(
            v2_aggregate=v2.arm_b_aggregate,
            privacy_failure_rate=privacy_rate,
            new_v2_regressions=new_regressions,
        )

    result = TripleColumnAblationReport(
        checkpoint_ids=cp_ids,
        evaluation_transformed_v1=_aggregate_excluding_invalid(v1),
        evaluation_transformed_v2=_aggregate_excluding_invalid(v2),
        full_synthetic=_aggregate_excluding_invalid(full),
        v1_privacy_gate_passed=False,
        v2_privacy_gate_passed=privacy_rate == 0.0,
        privacy_failure_rate_v2=privacy_rate,
        total_cost_usd=ledger.cumulative_usd,
        regression_semantics=extract_regression_semantics(v1, v2),
        invalid_experiments=invalid_experiments,
        decision=decision,
        decision_rationale=rationale,
    )
    _write_json(out_dir / "hardest-10-triple-column.json", result.as_dict())
    return result


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


__all__ = [
    "HARDEST_10_CHECKPOINTS",
    "REGRESSION_INSPECTION_CPS",
    "TripleColumnAblationReport",
    "evaluate_v2_regate_decision",
    "extract_regression_semantics",
    "run_live_triple_column_hardest_10",
]
