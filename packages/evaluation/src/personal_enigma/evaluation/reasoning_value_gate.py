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
LiveGateArchitectureDecision = Literal["clear_win", "small_win", "no_win"]
REPORT_PATH = Path("docs/reports/reasoning-value-gate-report.md")
LIVE_REPORT_PATH = Path("docs/reports/reasoning-value-gate-live-report.md")
ADR_PATH = Path("docs/adr/012-reasoning-value-gate-decision.md")
ADOPT_MIN_DELTA = 0.05
HYBRID_MIN_DELTA = 0.02
CLEAR_WIN_RECALL_DELTA = 0.05
CLEAR_WIN_SUPPRESS_FLOOR = -0.01
SMALL_WIN_RECALL_DELTA = 0.02


@dataclass
class LiveGateEvidence:
    git_commit: str
    scenario: str
    scenario_version: str
    generated_at: str
    live: bool
    arm_a: dict[str, float]
    arm_b: dict[str, float]
    deltas: dict[str, float]
    ablation_attention_delta: dict[str, float]
    ablation_next_action_delta: dict[str, float]
    arm_b_stability_pct: float
    schema_failure_rate: float
    privacy_failure_rate: float
    critical_regressions: int
    total_cost_usd: float
    median_latency_ms_arm_b: float
    median_input_tokens: int
    median_output_tokens: int
    architecture_decision: LiveGateArchitectureDecision
    architecture_rationale: str
    attributions: list[dict[str, Any]] = field(default_factory=list)
    benchmark: dict[str, Any] = field(default_factory=dict)
    ablation: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "git_commit": self.git_commit,
            "scenario": self.scenario,
            "scenario_version": self.scenario_version,
            "generated_at": self.generated_at,
            "live": self.live,
            "arm_a": self.arm_a,
            "arm_b": self.arm_b,
            "deltas": self.deltas,
            "ablation_attention_delta": self.ablation_attention_delta,
            "ablation_next_action_delta": self.ablation_next_action_delta,
            "arm_b_stability_pct": self.arm_b_stability_pct,
            "schema_failure_rate": self.schema_failure_rate,
            "privacy_failure_rate": self.privacy_failure_rate,
            "critical_regressions": self.critical_regressions,
            "total_cost_usd": self.total_cost_usd,
            "median_latency_ms_arm_b": self.median_latency_ms_arm_b,
            "median_input_tokens": self.median_input_tokens,
            "median_output_tokens": self.median_output_tokens,
            "architecture_decision": self.architecture_decision,
            "architecture_rationale": self.architecture_rationale,
            "attributions": self.attributions,
            "benchmark": self.benchmark,
            "ablation": self.ablation,
        }


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


def decide_live_architecture(
    arm_a: dict[str, float],
    arm_b: dict[str, float],
    *,
    critical_regressions: int,
    schema_failure_rate: float,
    privacy_failure_rate: float,
) -> tuple[LiveGateArchitectureDecision, str]:
    recall_delta = arm_b.get("critical_recall", 0.0) - arm_a.get("critical_recall", 0.0)
    suppress_delta = (
        arm_b.get("must_suppress_accuracy", 0.0) - arm_a.get("must_suppress_accuracy", 0.0)
    )
    schema_ok = schema_failure_rate <= 0.0
    privacy_ok = privacy_failure_rate <= 0.0
    if (
        recall_delta >= CLEAR_WIN_RECALL_DELTA
        and suppress_delta >= CLEAR_WIN_SUPPRESS_FLOOR
        and critical_regressions == 0
        and schema_ok
        and privacy_ok
    ):
        return (
            "clear_win",
            f"LLM clear win: recall Δ={recall_delta:+.3f}, suppress Δ={suppress_delta:+.3f}, "
            f"0 regressions, schema/privacy clean.",
        )
    if (
        recall_delta >= SMALL_WIN_RECALL_DELTA
        and suppress_delta >= CLEAR_WIN_SUPPRESS_FLOOR
        and critical_regressions <= 1
        and schema_failure_rate <= 0.05
        and privacy_ok
    ):
        return (
            "small_win",
            f"Hybrid threshold: recall Δ={recall_delta:+.3f}, suppress Δ={suppress_delta:+.3f}.",
        )
    return (
        "no_win",
        f"No win — keep deterministic (recall Δ={recall_delta:+.3f}, "
        f"regressions={critical_regressions}, schema_fail={schema_failure_rate:.1%}).",
    )


def collect_live_gate_evidence(
    truth: EvaluationTruth,
    *,
    main: object,
    ablation: dict[str, Any],
    attributions: list[dict[str, Any]],
    ledger: object,
    live: bool,
    repo: Path | None = None,
) -> LiveGateEvidence:
    repo = repo or Path.cwd()
    arm_a = getattr(main, "arm_a_aggregate", {})
    arm_b = getattr(main, "arm_b_aggregate", {})
    deltas = {k: arm_b.get(k, 0.0) - arm_a.get(k, 0.0) for k in set(arm_a) | set(arm_b)}
    outcomes = getattr(main, "outcome_counts", None)
    critical_regressions = outcomes.regressions if outcomes else 0
    decision, rationale = decide_live_architecture(
        arm_a,
        arm_b,
        critical_regressions=critical_regressions,
        schema_failure_rate=float(getattr(main, "schema_failure_rate", 0.0)),
        privacy_failure_rate=float(getattr(main, "privacy_failure_rate", 0.0)),
    )
    return LiveGateEvidence(
        git_commit=_git_commit(repo),
        scenario=str(getattr(main, "scenario", "alex-v1")),
        scenario_version=truth.scenario_version,
        generated_at=datetime.now(tz=UTC).isoformat(),
        live=live,
        arm_a=arm_a,
        arm_b=arm_b,
        deltas=deltas,
        ablation_attention_delta=ablation.get("attention_delta", {}),
        ablation_next_action_delta=ablation.get("next_action_delta", {}),
        arm_b_stability_pct=float(getattr(main, "arm_b_stability_pct", 1.0)),
        schema_failure_rate=float(getattr(main, "schema_failure_rate", 0.0)),
        privacy_failure_rate=float(getattr(main, "privacy_failure_rate", 0.0)),
        critical_regressions=critical_regressions,
        total_cost_usd=float(getattr(ledger, "cumulative_usd", 0.0)),
        median_latency_ms_arm_b=float(getattr(main, "median_latency_ms", 0.0)),
        median_input_tokens=int(getattr(main, "median_input_tokens", 0)),
        median_output_tokens=int(getattr(main, "median_output_tokens", 0)),
        architecture_decision=decision,
        architecture_rationale=rationale,
        attributions=attributions,
        benchmark=getattr(main, "as_dict", lambda: {})(),
        ablation=ablation,
    )


def render_live_gate_report_markdown(evidence: LiveGateEvidence) -> str:
    a, b, d = evidence.arm_a, evidence.arm_b, evidence.deltas
    lines = [
        "# Reasoning Value Gate — Live Report",
        "",
        f"- Generated: {evidence.generated_at}",
        f"- Git: `{evidence.git_commit}`",
        f"- Scenario: `{evidence.scenario}` v{evidence.scenario_version}",
        f"- Live Fireworks: `{evidence.live}`",
        f"- Total cost: ${evidence.total_cost_usd:.4f}",
        "",
        "## Exit gate metrics",
        "",
        "| Metric | Arm A | LLM B | Delta |",
        "| --- | --- | --- | --- |",
        f"| MUST_SURFACE recall (critical) | {a.get('critical_recall', 0):.3f} | {b.get('critical_recall', 0):.3f} | {d.get('critical_recall', 0):+.3f} |",
        f"| MUST_SUPPRESS accuracy | {a.get('must_suppress_accuracy', 0):.3f} | {b.get('must_suppress_accuracy', 0):.3f} | {d.get('must_suppress_accuracy', 0):+.3f} |",
        f"| Top-3 critical recall | {a.get('top3_critical_recall', 0):.3f} | {b.get('top3_critical_recall', 0):.3f} | {d.get('top3_critical_recall', 0):+.3f} |",
        f"| Next-action fit | {a.get('next_action_fit', 0):.3f} | {b.get('next_action_fit', 0):.3f} | {d.get('next_action_fit', 0):+.3f} |",
        f"| Stable decisions (B) | n/a | {evidence.arm_b_stability_pct:.1%} | — |",
        f"| Schema failures | — | {evidence.schema_failure_rate:.1%} | — |",
        f"| Privacy failures | — | {evidence.privacy_failure_rate:.1%} | — |",
        f"| Critical regressions | — | {evidence.critical_regressions} | — |",
        f"| Median latency | ~ms | {evidence.median_latency_ms_arm_b:.1f} ms | — |",
        f"| Median input tokens | — | {evidence.median_input_tokens} | — |",
        f"| Median output tokens | — | {evidence.median_output_tokens} | — |",
        "",
        "## Privacy ablation (10 hardest)",
        "",
        f"- Attention delta: `{evidence.ablation_attention_delta}`",
        f"- Next-action delta: `{evidence.ablation_next_action_delta}`",
        "",
        "## Architecture decision",
        "",
        f"**Decision:** `{evidence.architecture_decision}`",
        "",
        evidence.architecture_rationale,
        "",
    ]
    if evidence.attributions:
        lines.extend(["## Failure attributions", ""])
        for att in evidence.attributions[:20]:
            lines.append(
                f"- `{att.get('checkpoint_id')}` [{att.get('cause')}]: {att.get('narrative')}"
            )
    lines.append("")
    return "\n".join(lines)


def write_live_gate_report(
    evidence: LiveGateEvidence,
    *,
    report_path: str | Path = LIVE_REPORT_PATH,
    adr_path: str | Path = ADR_PATH,
) -> Path:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_live_gate_report_markdown(evidence), encoding="utf-8")
    adr = Path(adr_path)
    a, b, d = evidence.arm_a, evidence.arm_b, evidence.deltas
    adr.write_text(
        f"""# ADR-012: Reasoning Value Gate architecture decision

**Status:** Accepted (live gate evidence — placeholders filled when live run completes)
**Date:** {evidence.generated_at[:10]}
**Git:** `{evidence.git_commit}`

## Live evidence

| Metric | Arm A | LLM B | Delta |
| --- | --- | --- | --- |
| Critical recall | {a.get("critical_recall", 0):.3f} | {b.get("critical_recall", 0):.3f} | {d.get("critical_recall", 0):+.3f} |
| Must-suppress accuracy | {a.get("must_suppress_accuracy", 0):.3f} | {b.get("must_suppress_accuracy", 0):.3f} | {d.get("must_suppress_accuracy", 0):+.3f} |
| Top-3 critical recall | {a.get("top3_critical_recall", 0):.3f} | {b.get("top3_critical_recall", 0):.3f} | {d.get("top3_critical_recall", 0):+.3f} |
| Next-action fit | {a.get("next_action_fit", 0):.3f} | {b.get("next_action_fit", 0):.3f} | {d.get("next_action_fit", 0):+.3f} |
| Total live cost | ~$0 | ${evidence.total_cost_usd:.4f} | — |
| B stability | n/a | {evidence.arm_b_stability_pct:.1%} | — |
| Critical regressions | — | {evidence.critical_regressions} | — |
| Schema failure rate | — | {evidence.schema_failure_rate:.1%} | — |
| Privacy ablation (attention) | — | — | {evidence.ablation_attention_delta} |
| Privacy ablation (next-action) | — | — | {evidence.ablation_next_action_delta} |

## Multi-axis decision

**{evidence.architecture_decision}** — {evidence.architecture_rationale}

| Outcome | Criteria |
| --- | --- |
| CLEAR WIN | recall Δ≥+5pp AND suppress Δ≥-1pp AND regressions=0 AND schema/privacy=100% |
| SMALL WIN | hybrid threshold (recall Δ≥+2pp, suppress Δ≥-1pp, ≤1 regression) |
| NO WIN | keep deterministic |

See [reasoning-value-gate-live-report.md](../reports/reasoning-value-gate-live-report.md).
""",
        encoding="utf-8",
    )
    return report_path


def collect_reasoning_value_gate_evidence(
    truth: EvaluationTruth,
    *,
    baseline_dir: str | Path,
    replay_fixture: str | Path,
    checkpoint_ids: list[str] | None = None,
    repo: Path | None = None,
    attention_only: bool = False,
) -> ReasoningValueGateEvidence:
    repo = repo or Path.cwd()
    benchmark = run_llm_benchmark(
        truth,
        baseline_dir=baseline_dir,
        replay_fixture=replay_fixture,
        checkpoint_ids=checkpoint_ids,
        attention_only=attention_only,
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
    attention_only: bool = False,
) -> ReasoningValueGateEvidence:
    truth = load_evaluation_truth(ground_truth_path)
    evidence = collect_reasoning_value_gate_evidence(
        truth,
        baseline_dir=baseline_dir,
        replay_fixture=replay_fixture,
        checkpoint_ids=checkpoint_ids,
        repo=repo,
        attention_only=attention_only,
    )
    if write_report:
        write_reasoning_value_gate_report(evidence)
    return evidence


__all__ = [
    "ADR_PATH",
    "LIVE_REPORT_PATH",
    "REPORT_PATH",
    "LiveGateArchitectureDecision",
    "LiveGateEvidence",
    "ReasoningValueGateEvidence",
    "collect_live_gate_evidence",
    "collect_reasoning_value_gate_evidence",
    "decide_architecture",
    "decide_live_architecture",
    "render_gate_report_markdown",
    "render_live_gate_report_markdown",
    "run_reasoning_value_gate",
    "write_live_gate_report",
    "write_reasoning_value_gate_report",
]
