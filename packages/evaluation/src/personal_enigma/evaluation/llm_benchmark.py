"""LLM judge benchmark — Arm A heuristic vs Arm B PAYG (Reasoning Value Gate / R03).

Supersedes D14 — structured ``attention`` + ``next_action`` on frozen snapshots.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from personal_enigma.evaluation.checkpoint_runner import (
    load_checkpoint_snapshot,
    verify_arm_a_integrity,
)
from personal_enigma.evaluation.evaluation_truth import EvaluationTruth
from personal_enigma.evaluation.metrics.support_fitness import (
    SupportFitnessMetrics,
    compute_support_fitness_metrics,
)
from personal_enigma.evaluation.observations import (
    CheckpointSnapshot,
    CostEvent,
    NextActionObservation,
    SurfacedAlert,
)
from personal_enigma.reasoning import PaygReasoningService, ReasoningMode, ReplayPaygTransport
from personal_enigma.reasoning.structured_output import (
    LlmJudgeOutput,
    LlmJudgeParseError,
    parse_llm_judge_output,
)
from personal_enigma.transformation import TransformedContext

PROMPT_VERSION = "reasoning-gate-v1"
FORBIDDEN_PROMPT_MARKERS = (
    "support_challenges",
    "poor_actions",
    "good_next_actions",
    "persona",
    "admin_avoidance",
    "MUST_SURFACE",
    "MUST_SUPPRESS",
)

_JUDGE_PROMPT = """You are Enigma's reasoning judge for Demo Mode evaluation.

Given the sanitised context snapshot, return JSON only (no markdown, no chain-of-thought):

{{
  "attention": {{
    "item_id": "<obligation or candidate id>",
    "behaviour": "surface" | "suppress",
    "priority": 1-5
  }},
  "next_action": {{
    "title": "<concrete micro-step>",
    "estimated_minutes": <int>,
    "effort": "trivial" | "light" | "moderate" | "heavy",
    "why_this_now": "<one sentence>"
  }}
}}

Context snapshot:
{context_json}
"""


def assert_prompt_safe(prompt: str) -> None:
    lower = prompt.lower()
    for marker in FORBIDDEN_PROMPT_MARKERS:
        if marker.lower() in lower:
            raise ValueError(
                f"benchmark prompt must not include evaluator-only marker {marker!r}"
            )


def snapshot_to_context_dict(snapshot: CheckpointSnapshot) -> dict[str, Any]:
    return {
        "checkpoint_id": snapshot.checkpoint_id,
        "at": snapshot.at.isoformat(),
        "candidates": [
            {
                "id": c.id,
                "title": c.title,
                "obligation_ids": c.obligation_ids,
                "evidence_ids": c.evidence_ids,
                "score": c.score,
                "suppressed": c.suppressed,
            }
            for c in snapshot.candidate_set
        ],
        "surfaced": [
            {"id": a.id, "title": a.title, "obligation_ids": a.obligation_ids}
            for a in snapshot.alerts
        ],
        "memory": (
            {"open_obligation_ids": list(snapshot.memory_state.open_obligation_ids)}
            if snapshot.memory_state
            else {}
        ),
        "retrieval": [
            {"query_id": r.query_id, "hits": list(r.hits)} for r in snapshot.retrieval
        ],
    }


def snapshot_to_transformed_context(snapshot: CheckpointSnapshot) -> TransformedContext:
    candidates = snapshot.candidate_set[:5]
    parts = [f"Checkpoint {snapshot.checkpoint_id} at {snapshot.at.isoformat()}"]
    for cand in candidates:
        parts.append(f"Candidate {cand.id}: {cand.title} score={cand.score:.2f}")
    entities = [
        f"OBLIGATION_{oid.replace('obligation_', '').upper()}"
        for cand in candidates
        for oid in cand.obligation_ids
    ]
    return TransformedContext(
        summary=" | ".join(parts),
        entities=sorted(set(entities)),
        metadata={
            "source_type": "evaluation_checkpoint",
            "checkpoint_id": snapshot.checkpoint_id,
            "record_id": snapshot.checkpoint_id,
        },
        may_transmit_remotely=True,
    )


def snapshot_to_full_synthetic_context(snapshot: CheckpointSnapshot) -> TransformedContext:
    base = snapshot_to_transformed_context(snapshot)
    synthetic = re.sub(
        r"OBLIGATION_([A-Z0-9_]+)",
        lambda m: m.group(1).replace("_", " ").title(),
        base.summary,
    )
    return base.model_copy(
        update={
            "summary": synthetic.replace("Candidate item-", "Reminder: ")
            + " | people: Alex, Elena, Maya",
            "entities": ["Alex", "Elena", "Maya"],
            "may_transmit_remotely": False,
        }
    )


def build_judge_prompt(snapshot: CheckpointSnapshot) -> str:
    prompt = _JUDGE_PROMPT.format(
        context_json=json.dumps(snapshot_to_context_dict(snapshot), indent=2)
    )
    assert_prompt_safe(prompt)
    return prompt


def llm_output_to_alerts(
    snapshot: CheckpointSnapshot, output: LlmJudgeOutput
) -> list[SurfacedAlert]:
    if output.attention.behaviour == "suppress":
        return []
    item_id = output.attention.item_id
    for cand in snapshot.candidate_set:
        if cand.id == item_id or item_id in cand.obligation_ids:
            return [
                SurfacedAlert(
                    id=cand.id,
                    title=cand.title,
                    kind=cand.kind,
                    score=float(output.attention.priority) / 5.0,
                    obligation_ids=list(cand.obligation_ids),
                    evidence_ids=list(cand.evidence_ids),
                    surfaced_at=snapshot.at,
                )
            ]
    return [
        SurfacedAlert(
            id=item_id,
            title=output.next_action.title,
            score=float(output.attention.priority) / 5.0,
            obligation_ids=[item_id] if item_id.startswith("obligation_") else [],
            surfaced_at=snapshot.at,
        )
    ]


def llm_output_to_next_action(output: LlmJudgeOutput) -> NextActionObservation:
    title = output.next_action.title
    return NextActionObservation(
        title=title,
        action_id=title.strip().lower().replace(" ", "_"),
        estimated_minutes=output.next_action.estimated_minutes,
        effort=output.next_action.effort,
        why_this_now=output.next_action.why_this_now,
    )


def aggregate_support_fitness(metrics: list[SupportFitnessMetrics]) -> dict[str, float]:
    if not metrics:
        return {
            "critical_recall": 1.0,
            "must_suppress_accuracy": 1.0,
            "top3_critical_recall": 1.0,
            "next_action_fit": 1.0,
        }
    n = len(metrics)
    return {
        "critical_recall": sum(m.top3_critical_recall for m in metrics) / n,
        "must_suppress_accuracy": sum(m.suppression_accuracy for m in metrics) / n,
        "top3_critical_recall": sum(m.top3_critical_recall for m in metrics) / n,
        "next_action_fit": sum(m.next_action_accuracy for m in metrics) / n,
    }


@dataclass
class CheckpointArmResult:
    checkpoint_id: str
    arm: Literal["A", "B"]
    metrics: SupportFitnessMetrics
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    parse_error: str | None = None
    llm_output: LlmJudgeOutput | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "arm": self.arm,
            "metrics": self.metrics.as_dict(),
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "parse_error": self.parse_error,
        }


@dataclass
class LlmBenchmarkReport:
    scenario: str
    arm_a: list[CheckpointArmResult] = field(default_factory=list)
    arm_b: list[CheckpointArmResult] = field(default_factory=list)
    arm_a_aggregate: dict[str, float] = field(default_factory=dict)
    arm_b_aggregate: dict[str, float] = field(default_factory=dict)
    baseline_integrity_ok: bool = True
    baseline_mismatches: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "arm_a_aggregate": self.arm_a_aggregate,
            "arm_b_aggregate": self.arm_b_aggregate,
            "baseline_integrity_ok": self.baseline_integrity_ok,
            "baseline_mismatches": self.baseline_mismatches,
            "checkpoints": {
                "arm_a": [r.as_dict() for r in self.arm_a],
                "arm_b": [r.as_dict() for r in self.arm_b],
            },
        }


def score_arm_a(snapshot: CheckpointSnapshot, truth: EvaluationTruth) -> CheckpointArmResult:
    metrics = compute_support_fitness_metrics(
        truth,
        alerts=snapshot.alerts,
        next_action=snapshot.next_action,
        at=snapshot.at,
    )
    return CheckpointArmResult(
        checkpoint_id=snapshot.checkpoint_id, arm="A", metrics=metrics
    )


def score_arm_b(
    snapshot: CheckpointSnapshot,
    truth: EvaluationTruth,
    *,
    service: PaygReasoningService,
    context: TransformedContext | None = None,
    model: str = "payg-gate",
) -> CheckpointArmResult:
    prompt = build_judge_prompt(snapshot)
    ctx = context or snapshot_to_transformed_context(snapshot)
    start = time.perf_counter()
    try:
        result = service.reason(ctx, prompt=prompt, model=model)
        latency_ms = (time.perf_counter() - start) * 1000.0
        output = parse_llm_judge_output(result.text)
    except (LlmJudgeParseError, ValueError) as exc:
        latency_ms = (time.perf_counter() - start) * 1000.0
        metrics = compute_support_fitness_metrics(
            truth, alerts=snapshot.alerts, next_action=None, at=snapshot.at
        )
        return CheckpointArmResult(
            checkpoint_id=snapshot.checkpoint_id,
            arm="B",
            metrics=metrics,
            latency_ms=latency_ms,
            parse_error=str(exc),
        )

    alerts = llm_output_to_alerts(snapshot, output)
    next_action = llm_output_to_next_action(output)
    metrics = compute_support_fitness_metrics(
        truth, alerts=alerts, next_action=next_action, at=snapshot.at
    )
    usage = result.usage
    return CheckpointArmResult(
        checkpoint_id=snapshot.checkpoint_id,
        arm="B",
        metrics=metrics,
        latency_ms=latency_ms,
        cost_usd=usage.estimated_cost_usd if usage else 0.0,
        llm_output=output,
    )


def run_llm_benchmark(
    truth: EvaluationTruth,
    *,
    baseline_dir: str | Path,
    replay_fixture: str | Path | None = None,
    checkpoint_ids: list[str] | None = None,
    context_mode: Literal["transformed", "full_synthetic"] = "transformed",
) -> LlmBenchmarkReport:
    root = Path(baseline_dir)
    mismatches = verify_arm_a_integrity(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    scenario = str(manifest.get("scenario", "alex-v1"))
    if checkpoint_ids is None:
        checksums = manifest.get("checksums", {})
        checkpoint_ids = sorted(checksums) if isinstance(checksums, dict) else []

    transport = (
        ReplayPaygTransport(replay_fixture, force_offline=True) if replay_fixture else None
    )
    service = PaygReasoningService(
        mode=ReasoningMode.ENABLED if transport else ReasoningMode.DRY_RUN,
        transport=transport,
    )

    report = LlmBenchmarkReport(
        scenario=scenario,
        baseline_integrity_ok=not mismatches,
        baseline_mismatches=mismatches,
    )
    for cp_id in checkpoint_ids:
        snapshot = load_checkpoint_snapshot(root / f"{cp_id}.json")
        report.arm_a.append(score_arm_a(snapshot, truth))
        ctx = (
            snapshot_to_full_synthetic_context(snapshot)
            if context_mode == "full_synthetic"
            else snapshot_to_transformed_context(snapshot)
        )
        report.arm_b.append(score_arm_b(snapshot, truth, service=service, context=ctx))

    report.arm_a_aggregate = aggregate_support_fitness([r.metrics for r in report.arm_a])
    report.arm_b_aggregate = aggregate_support_fitness([r.metrics for r in report.arm_b])
    return report


def benchmark_cost_events(arm_b: list[CheckpointArmResult]) -> list[CostEvent]:
    return [
        CostEvent(
            category="attention_reasoning",
            model="payg-gate",
            input_tokens=800,
            output_tokens=120,
            estimated_usd=r.cost_usd or 0.002,
        )
        for r in arm_b
    ]


__all__ = [
    "FORBIDDEN_PROMPT_MARKERS",
    "CheckpointArmResult",
    "LlmBenchmarkReport",
    "PROMPT_VERSION",
    "aggregate_support_fitness",
    "assert_prompt_safe",
    "benchmark_cost_events",
    "build_judge_prompt",
    "run_llm_benchmark",
    "score_arm_a",
    "score_arm_b",
    "snapshot_to_full_synthetic_context",
    "snapshot_to_transformed_context",
]
