"""Reasoning Value Gate exit report and architecture decision (R07)."""

from __future__ import annotations

import statistics
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from personal_enigma.evaluation.checkpoint_runner import (
    load_checkpoint_snapshot,
    verify_arm_a_integrity,
)
from personal_enigma.evaluation.evaluation_truth import EvaluationTruth, load_evaluation_truth
from personal_enigma.evaluation.failure_attribution import (
    attribute_benchmark,
    enrich_failures_json,
)
from personal_enigma.evaluation.llm_benchmark import (
    benchmark_cost_events,
    run_llm_benchmark,
)
from personal_enigma.evaluation.metrics.cost import compute_cost_metrics
from personal_enigma.evaluation.privacy_ablation import run_privacy_ablation

ArchitectureDecision = Literal["adopt", "hybrid", "keep_deterministic"]
REPORT_PATH = Path("docs/reports/reasoning-value-gate-report.md")
ADR_PATH = Path("docs/adr/012-reasoning-value-gate-decision.md")
ADOPT_MIN_DELTA = 0.05
HYBRID_MIN_DELTA = 0.02


@dataclass
class ReasoningValueGateEvidence:
    git_commit: str
    scenario: str
    scenario_version: str
    generated_at: str
    arm_a: dict[str, float]
    arm_b: dict[str, float]
    ablation_delta: dict[str, float]
    median_latency_ms_arm_a: float
    median_latency_ms_arm_b: float
    cost_per_simulated_month_usd: float
    architecture_decision: ArchitectureDecision
    architecture_rationale: str
    attributions: list[dict[str, Any]] = field(default_factory=list)
    failures: dict[str, Any] = field(default_factory=dict)
    benchmark: dict[str, Any] = field(default_factory=dict)
    ablation: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "git_commit": self.git_commit,
            "scenario": self.scenario,
            "scenario_version": self.scenario_version,
            "generated_at": self.generated_at,
            "arm_a": self.arm_a,
            "arm_b": self.arm_b,
            "ablation_delta": self.ablation_delta,
            "median_latency_ms_arm_a": self.median_latency_ms_arm_a,
            "median_latency_ms_arm_b": self.median_latency_ms_arm_b,
            "cost_per_simulated_month_usd": self.cost_per_simulated_month_usd,
            "architecture_decision": self.architecture_decision,
            "architecture_rationale": self.architecture_rationale,
            "attributions": self.attributions,
            "failures": self.failures,
            "benchmark": self.benchmark,
            "ablation": self.ablation,
        }


def _git_commit(repo: Path) -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=repo,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def decide_architecture(
    arm_a: dict[str, float],
    arm_b: dict[str, float],
    *,
    ablation_delta: dict[str, float],
) -> tuple[ArchitectureDecision, str]:
    keys = ("critical_recall", "top3_critical_recall", "next_action_fit")
    mean_delta = sum(arm_b.get(k, 0.0) - arm_a.get(k, 0.0) for k in keys) / len(keys)
    ablation_penalty = max((abs(v) for v in ablation_delta.values()), default=0.0)
    if mean_delta >= ADOPT_MIN_DELTA and ablation_penalty <= 0.10:
        return (
            "adopt",
            f"LLM materially improves headline metrics (mean Δ={mean_delta:.3f}).",
        )
    if mean_delta >= HYBRID_MIN_DELTA:
        return (
            "hybrid",
            f"Modest LLM gains — hybrid routing (mean Δ={mean_delta:.3f}).",
        )
    return (
        "keep_deterministic",
        f"Heuristic matches or beats LLM (mean Δ={mean_delta:.3f}).",
    )


def collect_reasoning_value_gate_evidence(
    truth: EvaluationTruth,
    *,
    baseline_dir: str | Path,
    replay_fixture: str | Path,
    checkpoint_ids: list[str] | None = None,
    repo: Path | None = None,
) -> ReasoningValueGateEvidence:
    repo = repo or Path.cwd()
    benchmark = run_llm_benchmark(
        truth,
        baseline_dir=baseline_dir,
        replay_fixture=replay_fixture,
        checkpoint_ids=checkpoint_ids,
    )
    ablation = run_privacy_ablation(
        truth,
        baseline_dir=baseline_dir,
        replay_fixture=replay_fixture,
        checkpoint_ids=checkpoint_ids,
    )
    root = Path(baseline_dir)
    ids = checkpoint_ids or [r.checkpoint_id for r in benchmark.arm_a]
    snapshots = {
        cp_id: load_checkpoint_snapshot(root / f"{cp_id}.json") for cp_id in ids
    }
    attributions = attribute_benchmark(
        snapshots, truth, arm_a_results=benchmark.arm_a, arm_b_results=benchmark.arm_b
    )
    lat_a = [r.latency_ms for r in benchmark.arm_a]
    lat_b = [r.latency_ms for r in benchmark.arm_b]
    cost_m = compute_cost_metrics(benchmark_cost_events(benchmark.arm_b), scenario_days=30.0)
    failures = enrich_failures_json(
        {
            "baseline_integrity": verify_arm_a_integrity(root),
            "arm_a_attention_misses": [
                r.checkpoint_id
                for r in benchmark.arm_a
                if r.metrics.attention_accuracy < 1.0
            ],
            "arm_b_attention_misses": [
                r.checkpoint_id
                for r in benchmark.arm_b
                if r.metrics.attention_accuracy < 1.0
            ],
        },
        attributions,
    )
    decision, rationale = decide_architecture(
        benchmark.arm_a_aggregate,
        benchmark.arm_b_aggregate,
        ablation_delta=ablation.delta,
    )
    return ReasoningValueGateEvidence(
        git_commit=_git_commit(repo),
        scenario=benchmark.scenario,
        scenario_version=truth.scenario_version,
        generated_at=datetime.now(tz=UTC).isoformat(),
        arm_a=benchmark.arm_a_aggregate,
        arm_b=benchmark.arm_b_aggregate,
        ablation_delta=ablation.delta,
        median_latency_ms_arm_a=statistics.median(lat_a) if lat_a else 0.0,
        median_latency_ms_arm_b=statistics.median(lat_b) if lat_b else 0.0,
        cost_per_simulated_month_usd=cost_m.monthly_usd,
        architecture_decision=decision,
        architecture_rationale=rationale,
        attributions=[a.as_dict() for a in attributions],
        failures=failures,
        benchmark=benchmark.as_dict(),
        ablation=ablation.as_dict(),
    )


def render_gate_report_markdown(evidence: ReasoningValueGateEvidence) -> str:
    a, b, ab = evidence.arm_a, evidence.arm_b, evidence.ablation_delta

    def row(metric: str, key: str, *, fmt: str = ".3f") -> str:
        av = a.get(key, 0)
        bv = b.get(key, 0)
        dv = ab.get(key, 0)
        return f"| {metric} | {av:{fmt}} | {bv:{fmt}} | {dv:+.3f} |"

    lines = [
        "# Reasoning Value Gate Report",
        "",
        f"- Generated: {evidence.generated_at}",
        f"- Git: `{evidence.git_commit}`",
        f"- Scenario: `{evidence.scenario}` v{evidence.scenario_version}",
        "",
        "## Exit gate metrics",
        "",
        "| Metric | Arm A (heuristic) | Arm B (LLM) | Ablation Δ |",
        "| --- | --- | --- | --- |",
        row("Critical recall", "critical_recall"),
        row("Must-suppress accuracy", "must_suppress_accuracy"),
        row("Top-3 critical recall", "top3_critical_recall"),
        row("Next-action fit", "next_action_fit"),
        (
            f"| Median latency | {evidence.median_latency_ms_arm_a:.1f} ms | "
            f"{evidence.median_latency_ms_arm_b:.1f} ms | — |"
        ),
        (
            f"| Cost / simulated month | ~$0 | "
            f"${evidence.cost_per_simulated_month_usd:.4f} | — |"
        ),
        "",
        "## Architecture decision",
        "",
        f"**Decision:** `{evidence.architecture_decision}`",
        "",
        evidence.architecture_rationale,
        "",
    ]
    summary = evidence.failures.get("attribution_summary", {})
    lines.extend(["## Failure attribution summary", ""])
    if summary:
        for cause, count in sorted(summary.items()):
            lines.append(f"- `{cause}`: {count}")
    else:
        lines.append("- No A/B disagreements requiring attribution.")
    lines.append("")
    return "\n".join(lines)


def write_reasoning_value_gate_report(
    evidence: ReasoningValueGateEvidence,
    *,
    report_path: str | Path = REPORT_PATH,
    adr_path: str | Path = ADR_PATH,
) -> Path:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_gate_report_markdown(evidence), encoding="utf-8")
    adr = Path(adr_path)
    adr.parent.mkdir(parents=True, exist_ok=True)
    a, b = evidence.arm_a, evidence.arm_b
    top3_a = a.get("top3_critical_recall", 0)
    top3_b = b.get("top3_critical_recall", 0)
    adr.write_text(
        f"""# ADR-012: Reasoning Value Gate architecture decision

**Status:** Accepted (evidence from harness)
**Date:** {evidence.generated_at[:10]}
**Git:** `{evidence.git_commit}`

## Evidence

| Metric | Arm A | Arm B |
| --- | --- | --- |
| Critical recall | {a.get("critical_recall", 0):.3f} | {b.get("critical_recall", 0):.3f} |
| Top-3 critical recall | {top3_a:.3f} | {top3_b:.3f} |
| Next-action fit | {a.get("next_action_fit", 0):.3f} | {b.get("next_action_fit", 0):.3f} |
| Privacy ablation Δ | — | {evidence.ablation_delta.get("next_action_fit", 0):+.3f} |

## Decision

**{evidence.architecture_decision}** — {evidence.architecture_rationale}

See [reasoning-value-gate-report.md](../reports/reasoning-value-gate-report.md).
""",
        encoding="utf-8",
    )
    return report_path


def run_reasoning_value_gate(
    *,
    ground_truth_path: str | Path,
    baseline_dir: str | Path,
    replay_fixture: str | Path,
    checkpoint_ids: list[str] | None = None,
    write_report: bool = True,
    repo: Path | None = None,
) -> ReasoningValueGateEvidence:
    truth = load_evaluation_truth(ground_truth_path)
    evidence = collect_reasoning_value_gate_evidence(
        truth,
        baseline_dir=baseline_dir,
        replay_fixture=replay_fixture,
        checkpoint_ids=checkpoint_ids,
        repo=repo,
    )
    if write_report:
        write_reasoning_value_gate_report(evidence)
    return evidence


__all__ = [
    "ADR_PATH",
    "REPORT_PATH",
    "ReasoningValueGateEvidence",
    "collect_reasoning_value_gate_evidence",
    "decide_architecture",
    "render_gate_report_markdown",
    "run_reasoning_value_gate",
    "write_reasoning_value_gate_report",
]
