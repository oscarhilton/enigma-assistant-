"""Live Fireworks A/B benchmark — Arm A frozen vs Arm B judge-v1 (R-L05)."""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from personal_enigma.evaluation.benchmark_budget import (
    BenchmarkBudgetLedger,
    BudgetGatedFireworksTransport,
)
from personal_enigma.evaluation.checkpoint_runner import (
    load_checkpoint_snapshot,
    verify_arm_a_integrity,
)
from personal_enigma.evaluation.evaluation_truth import EvaluationTruth
from personal_enigma.evaluation.llm_benchmark import (
    CheckpointArmResult,
    aggregate_support_fitness,
    score_arm_a,
    score_arm_b,
    snapshot_to_full_synthetic_context,
    snapshot_to_transformed_context,
)
from personal_enigma.evaluation.metrics.support_fitness import SupportFitnessMetrics
from personal_enigma.evaluation.observations import CheckpointSnapshot
from personal_enigma.reasoning import (
    FireworksChatTransport,
    PaygReasoningService,
    ReasoningMode,
)
from personal_enigma.reasoning.protocol import PaygTransport, ReasoningResult
from personal_enigma.reasoning.transport import MockPaygTransport
from personal_enigma.transformation import TransformedContext

LIVE_MODEL = "accounts/fireworks/models/gpt-oss-120b"
MAIN_REPS = 3
DISAGREEMENT_REPS = 5


class RepAwareTransport:
    """Adapts budget-gated Fireworks transport to the PaygTransport protocol."""

    def __init__(self, inner: BudgetGatedFireworksTransport) -> None:
        self._inner = inner

    @property
    def ledger(self) -> BenchmarkBudgetLedger:
        return self._inner.ledger

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        context: TransformedContext,
    ) -> ReasoningResult:
        rep = int(context.metadata.get("rep", 0))
        return self._inner.complete(
            model=model, prompt=prompt, context=context, rep=rep
        )


@dataclass
class LiveRepResult:
    checkpoint_id: str
    rep: int
    arm_result: CheckpointArmResult

    @property
    def metrics(self) -> SupportFitnessMetrics:
        return self.arm_result.metrics

    @property
    def latency_ms(self) -> float:
        return self.arm_result.latency_ms

    @property
    def cost_usd(self) -> float:
        return self.arm_result.cost_usd

    @property
    def parse_error(self) -> str | None:
        return self.arm_result.parse_error

    @property
    def schema_error(self) -> str | None:
        if self.arm_result.parse_error and "evidence_ids" in self.arm_result.parse_error:
            return self.arm_result.parse_error
        return None

    @property
    def privacy_error(self) -> str | None:
        return None

    def as_dict(self) -> dict[str, Any]:
        return {"checkpoint_id": self.checkpoint_id, "rep": self.rep, **self.arm_result.as_dict()}


@dataclass
class OutcomeCounts:
    rescues: int = 0
    regressions: int = 0
    agreements: int = 0
    shared_failures: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "rescues": self.rescues,
            "regressions": self.regressions,
            "agreements": self.agreements,
            "shared_failures": self.shared_failures,
        }


@dataclass
class LiveBenchmarkReport:
    scenario: str
    phase: str
    arm_a: list[CheckpointArmResult] = field(default_factory=list)
    arm_b_reps: dict[str, list[LiveRepResult]] = field(default_factory=dict)
    arm_a_aggregate: dict[str, float] = field(default_factory=dict)
    arm_b_aggregate: dict[str, float] = field(default_factory=dict)
    arm_b_stability_pct: float = 1.0
    schema_failure_rate: float = 0.0
    privacy_failure_rate: float = 0.0
    outcome_counts: OutcomeCounts = field(default_factory=OutcomeCounts)
    total_cost_usd: float = 0.0
    median_latency_ms: float = 0.0
    median_input_tokens: int = 0
    median_output_tokens: int = 0
    baseline_integrity_ok: bool = True
    checkpoint_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "phase": self.phase,
            "arm_a_aggregate": self.arm_a_aggregate,
            "arm_b_aggregate": self.arm_b_aggregate,
            "arm_b_stability_pct": self.arm_b_stability_pct,
            "schema_failure_rate": self.schema_failure_rate,
            "privacy_failure_rate": self.privacy_failure_rate,
            "outcome_counts": self.outcome_counts.as_dict(),
            "total_cost_usd": self.total_cost_usd,
            "median_latency_ms": self.median_latency_ms,
            "median_input_tokens": self.median_input_tokens,
            "median_output_tokens": self.median_output_tokens,
            "baseline_integrity_ok": self.baseline_integrity_ok,
            "checkpoint_ids": self.checkpoint_ids,
            "arm_a": [r.as_dict() for r in self.arm_a],
            "arm_b_reps": {
                cp_id: [r.as_dict() for r in reps]
                for cp_id, reps in self.arm_b_reps.items()
            },
        }


def _judge_v1_json(
    *,
    decision: str,
    evidence_ids: list[str] | None = None,
    next_action: dict[str, object] | None = None,
) -> str:
    payload: dict[str, object] = {
        "schema_version": "judge-v1",
        "attention": {
            "decision": decision,
            "priority": 4 if decision == "surface" else 0,
            "confidence": 0.9 if decision == "surface" else 0.95,
            "reason_codes": ["USER_COMMITMENT" if decision == "surface" else "LOW_VALUE_NOISE"],
            "evidence_ids": evidence_ids or [],
        },
        "next_action": next_action,
    }
    return json.dumps(payload)


class SmokeMockTransport:
    """Per-candidate judge-v1 mock for smoke / CI (no network)."""

    def __init__(self, checkpoint_id: str) -> None:
        self._checkpoint_id = checkpoint_id

    @staticmethod
    def _candidate_section(prompt: str) -> str:
        match = re.search(
            r"Candidate:\s*\n(\{.*?\})\n\nContext snapshot:",
            prompt,
            re.DOTALL,
        )
        return match.group(1) if match else ""

    @staticmethod
    def _candidate_id(prompt: str) -> str:
        section = SmokeMockTransport._candidate_section(prompt)
        match = re.search(r'"id":\s*"([^"]+)"', section)
        return match.group(1) if match else ""

    @staticmethod
    def _candidate_evidence(prompt: str) -> list[str]:
        section = SmokeMockTransport._candidate_section(prompt)
        match = re.search(r'"evidence_ids":\s*\[(.*?)\]', section, re.DOTALL)
        if not match:
            return []
        return re.findall(r'"([^"]+)"', match.group(1))

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        context: TransformedContext,
    ) -> ReasoningResult:
        candidate_id = self._candidate_id(prompt)
        evidence = self._candidate_evidence(prompt)

        if self._checkpoint_id == "cp-2026-01-21T13:30":
            if candidate_id == "item-obligation_brunch_book":
                text = _judge_v1_json(
                    decision="surface",
                    evidence_ids=evidence[:2] or ["rem-brunch-book"],
                )
            else:
                text = _judge_v1_json(decision="suppress", evidence_ids=evidence[:1])
        elif self._checkpoint_id == "cp-prizevault-smoke":
            if candidate_id == "item-noise-prizvault":
                text = _judge_v1_json(decision="suppress", evidence_ids=[])
            else:
                text = _judge_v1_json(decision="suppress", evidence_ids=evidence[:1])
        elif self._checkpoint_id == "cp-2026-01-11T11:00":
            text = _judge_v1_json(
                decision="suppress",
                evidence_ids=evidence[:1] if evidence else [],
            )
        else:
            if candidate_id == "item-obligation_december_expenses":
                text = _judge_v1_json(
                    decision="surface",
                    evidence_ids=evidence,
                    next_action={
                        "title": "Gather receipts",
                        "action_type": "admin",
                        "estimated_minutes": 5,
                        "confidence": 0.85,
                    },
                )
            else:
                text = _judge_v1_json(decision="suppress", evidence_ids=evidence[:1])

        return MockPaygTransport(response_text=text).complete(
            model=model, prompt=prompt, context=context
        )


def build_live_transport(
    *,
    live: bool,
    ledger: BenchmarkBudgetLedger,
    phase: str,
    checkpoint_id: str | None = None,
) -> PaygTransport:
    if live:
        inner = FireworksChatTransport()
        gated = BudgetGatedFireworksTransport(
            transport=inner, ledger=ledger, phase=phase
        )
        return RepAwareTransport(gated)
    if checkpoint_id:
        return SmokeMockTransport(checkpoint_id)
    return SmokeMockTransport("cp-default")


def _attention_pass(metrics: SupportFitnessMetrics) -> bool:
    return metrics.attention_accuracy >= 1.0


def compute_outcome_counts(
    arm_a: list[CheckpointArmResult],
    arm_b_reps: dict[str, list[LiveRepResult]],
) -> OutcomeCounts:
    counts = OutcomeCounts()
    by_a = {r.checkpoint_id: r for r in arm_a}
    for cp_id, reps in arm_b_reps.items():
        if cp_id not in by_a or not reps:
            continue
        a_pass = _attention_pass(by_a[cp_id].metrics)
        b_passes = [_attention_pass(r.metrics) for r in reps]
        b_majority = sum(b_passes) >= (len(b_passes) // 2 + 1)
        if a_pass and b_majority:
            counts.agreements += 1
        elif not a_pass and not b_majority:
            counts.shared_failures += 1
        elif not a_pass and b_majority:
            counts.rescues += 1
        elif a_pass and not b_majority:
            counts.regressions += 1
    return counts


def rep_stability_pct(reps: list[LiveRepResult]) -> float:
    if len(reps) < 2:
        return 1.0
    passes = [_attention_pass(r.metrics) for r in reps]
    majority = sum(passes) >= (len(passes) // 2 + 1)
    agree = sum(1 for p in passes if p == majority)
    return agree / len(passes)


def aggregate_b_reps(
    arm_b_reps: dict[str, list[LiveRepResult]],
) -> dict[str, float]:
    majority_metrics: list[SupportFitnessMetrics] = []
    for reps in arm_b_reps.values():
        if not reps:
            continue
        passes = [_attention_pass(r.metrics) for r in reps]
        majority = sum(passes) >= (len(passes) // 2 + 1)
        idx = next((i for i, p in enumerate(passes) if p == majority), 0)
        majority_metrics.append(reps[idx].metrics)
    return aggregate_support_fitness(majority_metrics)


def load_snapshot(baseline_dir: Path, checkpoint_id: str) -> CheckpointSnapshot:
    if checkpoint_id == "cp-prizevault-smoke":
        smoke = (
            Path(__file__).resolve().parents[3]
            / "fixtures"
            / "smoke"
            / "cp-prizevault-smoke.json"
        )
        return load_checkpoint_snapshot(smoke)
    return load_checkpoint_snapshot(baseline_dir / f"{checkpoint_id}.json")


def score_live_rep(
    snapshot: CheckpointSnapshot,
    truth: EvaluationTruth,
    *,
    service: PaygReasoningService,
    rep: int,
    context_mode: Literal["transformed", "full_synthetic"] = "transformed",
    model: str = LIVE_MODEL,
) -> LiveRepResult:
    ctx = (
        snapshot_to_full_synthetic_context(snapshot)
        if context_mode == "full_synthetic"
        else snapshot_to_transformed_context(snapshot)
    )
    ctx = ctx.model_copy(update={"metadata": {**ctx.metadata, "rep": str(rep)}})
    arm_result = score_arm_b(
        snapshot, truth, service=service, context=ctx, model=model
    )
    return LiveRepResult(
        checkpoint_id=snapshot.checkpoint_id, rep=rep, arm_result=arm_result
    )


def run_live_benchmark(
    truth: EvaluationTruth,
    *,
    baseline_dir: str | Path,
    checkpoint_ids: list[str],
    transport: PaygTransport,
    phase: str = "main",
    reps: int = MAIN_REPS,
    context_mode: Literal["transformed", "full_synthetic"] = "transformed",
    ledger: BenchmarkBudgetLedger | None = None,
) -> LiveBenchmarkReport:
    root = Path(baseline_dir)
    mismatches = verify_arm_a_integrity(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    scenario = str(manifest.get("scenario", "alex-v1"))
    service = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=transport)

    report = LiveBenchmarkReport(
        scenario=scenario,
        phase=phase,
        baseline_integrity_ok=not mismatches,
        checkpoint_ids=list(checkpoint_ids),
    )

    for cp_id in checkpoint_ids:
        snapshot = load_snapshot(root, cp_id)
        report.arm_a.append(score_arm_a(snapshot, truth))
        rep_results: list[LiveRepResult] = []
        for rep in range(reps):
            rep_results.append(
                score_live_rep(
                    snapshot,
                    truth,
                    service=service,
                    rep=rep,
                    context_mode=context_mode,
                )
            )
        report.arm_b_reps[cp_id] = rep_results

    report.arm_a_aggregate = aggregate_support_fitness(
        [r.metrics for r in report.arm_a]
    )
    report.arm_b_aggregate = aggregate_b_reps(report.arm_b_reps)
    report.outcome_counts = compute_outcome_counts(report.arm_a, report.arm_b_reps)

    all_reps = [r for reps in report.arm_b_reps.values() for r in reps]
    if all_reps:
        stabilities = [
            rep_stability_pct(reps) for reps in report.arm_b_reps.values() if reps
        ]
        report.arm_b_stability_pct = (
            sum(stabilities) / len(stabilities) if stabilities else 1.0
        )
        report.schema_failure_rate = sum(
            1 for r in all_reps if r.parse_error
        ) / len(all_reps)
        report.median_latency_ms = statistics.median([r.latency_ms for r in all_reps])
        report.total_cost_usd = sum(r.cost_usd for r in all_reps)

    if ledger is not None:
        report.total_cost_usd = ledger.cumulative_usd
        if ledger.records:
            report.median_input_tokens = int(
                statistics.median([r.prompt_tokens for r in ledger.records])
            )
            report.median_output_tokens = int(
                statistics.median([r.completion_tokens for r in ledger.records])
            )

    return report


def checkpoint_ids_from_manifest(baseline_dir: str | Path) -> list[str]:
    manifest = json.loads(
        (Path(baseline_dir) / "manifest.json").read_text(encoding="utf-8")
    )
    checksums = manifest.get("checksums", {})
    if isinstance(checksums, dict):
        return sorted(checksums)
    return []


def mock_response_for_checkpoint(checkpoint_id: str) -> str:
    return _judge_v1_json(decision="suppress")


__all__ = [
    "DISAGREEMENT_REPS",
    "LIVE_MODEL",
    "MAIN_REPS",
    "LiveBenchmarkReport",
    "LiveRepResult",
    "OutcomeCounts",
    "RepAwareTransport",
    "SmokeMockTransport",
    "aggregate_b_reps",
    "build_live_transport",
    "checkpoint_ids_from_manifest",
    "compute_outcome_counts",
    "load_snapshot",
    "mock_response_for_checkpoint",
    "rep_stability_pct",
    "run_live_benchmark",
    "score_live_rep",
]
