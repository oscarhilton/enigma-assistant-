"""LLM judge benchmark — Arm A heuristic vs Arm B PAYG (Reasoning Value Gate / R03).

Top-1 / top-3 flow (judge-v1 / R-L02)
--------------------------------------
1. For each candidate in the frozen ``candidate_set``, Arm B calls the remote judge
   with a per-candidate prompt (``Candidate:`` block + sanitised context snapshot).
2. Each call returns ``JudgeV1Output`` with an independent ``attention.decision``.
3. ``rank_candidate_judgements`` deterministically ranks candidates whose model
   decision is ``surface`` by ``(-priority, -heuristic score, candidate id)``.
4. Top-3 alerts (and top-1 recall metrics) come from that ranked list after
   ``apply_attention_policy`` may suppress model surfaces (e.g. snapshot-suppressed).
5. ``next_action`` is taken from the top ranked surfaced candidate when present.

Arm B logs ``model_judgement`` (ranked model surfaces) and ``policy_judgement``
(final alerts after deterministic policy) separately.
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
    RescueRegressionCase,
    SupportFitnessMetrics,
    compute_benchmark_rescue_regression,
    compute_support_fitness_metrics,
)
from personal_enigma.evaluation.observations import (
    AttentionCandidateObservation,
    CheckpointSnapshot,
    CostEvent,
    NextActionObservation,
    SurfacedAlert,
)
from personal_enigma.reasoning import PaygReasoningService, ReasoningMode, ReplayPaygTransport
from personal_enigma.reasoning.structured_output import (
    InvalidEvidenceIdsError,
    JudgeV1Attention,
    JudgeV1Output,
    JudgeV1ParseError,
    parse_judge_v1_output,
    validate_evidence_ids,
)
from personal_enigma.transformation import TransformedContext

PROMPT_VERSION = "judge-v1"
SURFACE_CONFIDENCE_MIN = 0.5
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

Judge the single candidate below against the sanitised checkpoint context.
Return JSON only (no markdown, no chain-of-thought) using schema judge-v1:

{{
  "schema_version": "judge-v1",
  "attention": {{
    "decision": "surface" | "suppress" | "context",
    "priority": 0-5,
    "confidence": 0.0-1.0,
    "reason_codes": ["USER_COMMITMENT", "DEADLINE_APPROACHING"],
    "evidence_ids": ["<ids from candidate only>"]
  }},
  "next_action": {next_action_schema}
}}

Candidate:
{candidate_json}

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


def candidate_to_dict(candidate: AttentionCandidateObservation) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "title": candidate.title,
        "obligation_ids": candidate.obligation_ids,
        "evidence_ids": candidate.evidence_ids,
        "score": candidate.score,
        "suppressed": candidate.suppressed,
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


def build_judge_prompt(
    snapshot: CheckpointSnapshot,
    candidate: AttentionCandidateObservation,
    *,
    attention_only: bool = False,
) -> str:
    next_action_schema = (
        "null"
        if attention_only
        else (
            '{ "title": "<micro-step>", "action_type": "admin", '
            '"estimated_minutes": <int>, "confidence": 0.0-1.0 }'
        )
    )
    prompt = _JUDGE_PROMPT.format(
        next_action_schema=next_action_schema,
        candidate_json=json.dumps(candidate_to_dict(candidate), indent=2),
        context_json=json.dumps(snapshot_to_context_dict(snapshot), indent=2),
    )
    assert_prompt_safe(prompt)
    return prompt


@dataclass(frozen=True, slots=True)
class PolicyJudgement:
    decision: Literal["surface", "suppress", "context"]
    reason: str | None = None


def apply_attention_policy(attention: JudgeV1Attention) -> PolicyJudgement:
    """Deterministic post-model policy (confidence gate before ranking)."""
    if attention.decision == "surface" and attention.confidence < SURFACE_CONFIDENCE_MIN:
        return PolicyJudgement(decision="suppress", reason="surface_threshold")
    return PolicyJudgement(decision=attention.decision)


@dataclass(frozen=True, slots=True)
class CandidateJudgement:
    candidate_id: str
    output: JudgeV1Output | None = None
    parse_error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "output": self.output.model_dump(mode="json") if self.output else None,
            "parse_error": self.parse_error,
        }


def rank_candidate_judgements(
    snapshot: CheckpointSnapshot,
    judgements: list[CandidateJudgement],
) -> list[tuple[AttentionCandidateObservation, JudgeV1Output]]:
    by_id = {c.id: c for c in snapshot.candidate_set}
    ranked: list[tuple[AttentionCandidateObservation, JudgeV1Output, tuple[int, float, str]]] = []
    for judgement in judgements:
        if judgement.output is None:
            continue
        policy = apply_attention_policy(judgement.output.attention)
        if policy.decision != "surface":
            continue
        candidate = by_id.get(judgement.candidate_id)
        if candidate is None:
            continue
        ranked.append(
            (
                candidate,
                judgement.output,
                (
                    -judgement.output.attention.priority,
                    -candidate.score,
                    candidate.id,
                ),
            )
        )
    ranked.sort(key=lambda row: row[2])
    return [(c, o) for c, o, _ in ranked]


def filter_snapshot_attention_policy(
    snapshot: CheckpointSnapshot,
    ranked_surfaces: list[tuple[AttentionCandidateObservation, JudgeV1Output]],
) -> list[SurfacedAlert]:
    alerts: list[SurfacedAlert] = []
    for candidate, output in ranked_surfaces:
        if candidate.suppressed:
            continue
        alerts.append(
            SurfacedAlert(
                id=candidate.id,
                title=candidate.title,
                kind=candidate.kind,
                score=float(output.attention.priority) / 5.0,
                obligation_ids=list(candidate.obligation_ids),
                evidence_ids=list(output.attention.evidence_ids or candidate.evidence_ids),
                surfaced_at=snapshot.at,
            )
        )
    return alerts


def ranked_surfaces_to_alerts(
    snapshot: CheckpointSnapshot,
    ranked_surfaces: list[tuple[AttentionCandidateObservation, JudgeV1Output]],
) -> list[SurfacedAlert]:
    alerts: list[SurfacedAlert] = []
    for candidate, output in ranked_surfaces:
        alerts.append(
            SurfacedAlert(
                id=candidate.id,
                title=candidate.title,
                kind=candidate.kind,
                score=float(output.attention.priority) / 5.0,
                obligation_ids=list(candidate.obligation_ids),
                evidence_ids=list(output.attention.evidence_ids or candidate.evidence_ids),
                surfaced_at=snapshot.at,
            )
        )
    return alerts


def pick_next_action(
    ranked_surfaces: list[tuple[AttentionCandidateObservation, JudgeV1Output]],
) -> NextActionObservation | None:
    for _candidate, output in ranked_surfaces:
        if output.next_action is None:
            continue
        title = output.next_action.title
        return NextActionObservation(
            title=title,
            action_id=title.strip().lower().replace(" ", "_"),
            estimated_minutes=output.next_action.estimated_minutes,
        )
    return None


def aggregate_support_fitness(metrics: list[SupportFitnessMetrics]) -> dict[str, float]:
    if not metrics:
        return {
            "critical_recall": 1.0,
            "must_suppress_accuracy": 1.0,
            "top1_critical_recall": 1.0,
            "top3_critical_recall": 1.0,
            "next_action_fit": 1.0,
        }
    n = len(metrics)
    return {
        "critical_recall": sum(m.top3_critical_recall for m in metrics) / n,
        "must_suppress_accuracy": sum(m.suppression_accuracy for m in metrics) / n,
        "top1_critical_recall": sum(m.top1_critical_recall for m in metrics) / n,
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
    candidate_judgements: list[CandidateJudgement] = field(default_factory=list)
    model_judgement: list[SurfacedAlert] = field(default_factory=list)
    policy_judgement: list[SurfacedAlert] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "arm": self.arm,
            "metrics": self.metrics.as_dict(),
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "parse_error": self.parse_error,
            "candidate_judgements": [j.as_dict() for j in self.candidate_judgements],
            "model_judgement": [
                {
                    "id": a.id,
                    "title": a.title,
                    "obligation_ids": list(a.obligation_ids),
                    "score": a.score,
                }
                for a in self.model_judgement
            ],
            "policy_judgement": [
                {
                    "id": a.id,
                    "title": a.title,
                    "obligation_ids": list(a.obligation_ids),
                    "score": a.score,
                }
                for a in self.policy_judgement
            ],
        }


@dataclass
class LlmBenchmarkReport:
    scenario: str
    arm_a: list[CheckpointArmResult] = field(default_factory=list)
    arm_b: list[CheckpointArmResult] = field(default_factory=list)
    arm_a_aggregate: dict[str, float] = field(default_factory=dict)
    arm_b_aggregate: dict[str, float] = field(default_factory=dict)
    rescue_regression_cases: list[RescueRegressionCase] = field(default_factory=list)
    rescue_regression_counts: dict[str, int] = field(default_factory=dict)
    baseline_integrity_ok: bool = True
    baseline_mismatches: list[str] = field(default_factory=list)
    attention_only: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "attention_only": self.attention_only,
            "arm_a_aggregate": self.arm_a_aggregate,
            "arm_b_aggregate": self.arm_b_aggregate,
            "rescue_regression_cases": [c.as_dict() for c in self.rescue_regression_cases],
            "rescue_regression_counts": self.rescue_regression_counts,
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
        checkpoint_id=snapshot.checkpoint_id,
        arm="A",
        metrics=metrics,
        model_judgement=list(snapshot.alerts),
        policy_judgement=list(snapshot.alerts),
    )


def _judge_candidate(
    snapshot: CheckpointSnapshot,
    candidate: AttentionCandidateObservation,
    *,
    service: PaygReasoningService,
    context: TransformedContext,
    model: str,
    attention_only: bool,
) -> CandidateJudgement:
    prompt = build_judge_prompt(snapshot, candidate, attention_only=attention_only)
    try:
        result = service.reason(context, prompt=prompt, model=model)
        output = parse_judge_v1_output(result.text)
        validate_evidence_ids(output, set(candidate.evidence_ids))
        return CandidateJudgement(candidate_id=candidate.id, output=output)
    except (JudgeV1ParseError, InvalidEvidenceIdsError, ValueError) as exc:
        return CandidateJudgement(
            candidate_id=candidate.id,
            parse_error=str(exc),
        )


def score_arm_b(
    snapshot: CheckpointSnapshot,
    truth: EvaluationTruth,
    *,
    service: PaygReasoningService,
    context: TransformedContext | None = None,
    model: str = "payg-gate",
    attention_only: bool = False,
) -> CheckpointArmResult:
    ctx = context or snapshot_to_transformed_context(snapshot)
    start = time.perf_counter()
    judgements: list[CandidateJudgement] = []
    total_cost = 0.0
    first_parse_error: str | None = None

    for candidate in snapshot.candidate_set:
        judgement = _judge_candidate(
            snapshot,
            candidate,
            service=service,
            context=ctx,
            model=model,
            attention_only=attention_only,
        )
        judgements.append(judgement)
        if judgement.parse_error and first_parse_error is None:
            first_parse_error = judgement.parse_error

    latency_ms = (time.perf_counter() - start) * 1000.0

    if first_parse_error is not None and all(j.output is None for j in judgements):
        metrics = compute_support_fitness_metrics(
            truth, alerts=snapshot.alerts, next_action=None, at=snapshot.at
        )
        return CheckpointArmResult(
            checkpoint_id=snapshot.checkpoint_id,
            arm="B",
            metrics=metrics,
            latency_ms=latency_ms,
            parse_error=first_parse_error,
            candidate_judgements=judgements,
        )

    ranked = rank_candidate_judgements(snapshot, judgements)
    model_alerts = ranked_surfaces_to_alerts(snapshot, ranked)
    policy_alerts = filter_snapshot_attention_policy(snapshot, ranked)
    next_action = None if attention_only else pick_next_action(ranked)

    metrics = compute_support_fitness_metrics(
        truth,
        alerts=policy_alerts,
        next_action=next_action,
        at=snapshot.at,
    )

    return CheckpointArmResult(
        checkpoint_id=snapshot.checkpoint_id,
        arm="B",
        metrics=metrics,
        latency_ms=latency_ms,
        cost_usd=total_cost,
        parse_error=first_parse_error,
        candidate_judgements=judgements,
        model_judgement=model_alerts,
        policy_judgement=policy_alerts,
    )


def run_llm_benchmark(
    truth: EvaluationTruth,
    *,
    baseline_dir: str | Path,
    replay_fixture: str | Path | None = None,
    checkpoint_ids: list[str] | None = None,
    context_mode: Literal["transformed", "full_synthetic"] = "transformed",
    attention_only: bool = False,
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
        attention_only=attention_only,
    )
    for cp_id in checkpoint_ids:
        snapshot = load_checkpoint_snapshot(root / f"{cp_id}.json")
        report.arm_a.append(score_arm_a(snapshot, truth))
        ctx = (
            snapshot_to_full_synthetic_context(snapshot)
            if context_mode == "full_synthetic"
            else snapshot_to_transformed_context(snapshot)
        )
        report.arm_b.append(
            score_arm_b(
                snapshot,
                truth,
                service=service,
                context=ctx,
                attention_only=attention_only,
            )
        )

    report.arm_a_aggregate = aggregate_support_fitness([r.metrics for r in report.arm_a])
    report.arm_b_aggregate = aggregate_support_fitness([r.metrics for r in report.arm_b])
    cases, counts = compute_benchmark_rescue_regression(report.arm_a, report.arm_b)
    report.rescue_regression_cases = cases
    report.rescue_regression_counts = counts
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
    "CandidateJudgement",
    "CheckpointArmResult",
    "LlmBenchmarkReport",
    "PolicyJudgement",
    "PROMPT_VERSION",
    "SURFACE_CONFIDENCE_MIN",
    "aggregate_support_fitness",
    "apply_attention_policy",
    "assert_prompt_safe",
    "benchmark_cost_events",
    "build_judge_prompt",
    "filter_snapshot_attention_policy",
    "pick_next_action",
    "rank_candidate_judgements",
    "run_llm_benchmark",
    "score_arm_a",
    "score_arm_b",
    "snapshot_to_full_synthetic_context",
    "snapshot_to_transformed_context",
]
