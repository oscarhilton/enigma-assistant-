"""Failure attribution for Arm A vs Arm B disagreements (Reasoning Value Gate / R05)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

from personal_enigma.evaluation.checkpoint_runner import must_surface_obligations_at
from personal_enigma.evaluation.evaluation_truth import EvaluationTruth
from personal_enigma.evaluation.live_benchmark import LiveRepResult
from personal_enigma.evaluation.llm_benchmark import CheckpointArmResult
from personal_enigma.evaluation.observations import CheckpointSnapshot


class FailureCause(StrEnum):
    INGESTION = "INGESTION"
    IDENTITY = "IDENTITY"
    RETRIEVAL = "RETRIEVAL"
    MEMORY = "MEMORY"
    INTERPRETATION = "INTERPRETATION"
    ATTENTION_POLICY = "ATTENTION_POLICY"
    NEXT_ACTION_POLICY = "NEXT_ACTION_POLICY"
    TIMING = "TIMING"


@dataclass(frozen=True, slots=True)
class AttributionCase:
    checkpoint_id: str
    dimension: Literal["attention", "next_action"]
    cause: FailureCause
    narrative: str
    arm_a_pass: bool
    arm_b_pass: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "dimension": self.dimension,
            "cause": self.cause.value,
            "narrative": self.narrative,
            "arm_a_pass": self.arm_a_pass,
            "arm_b_pass": self.arm_b_pass,
        }


def _candidate_obligation_ids(snapshot: CheckpointSnapshot) -> set[str]:
    ids: set[str] = set()
    for cand in snapshot.candidate_set:
        ids.update(cand.obligation_ids)
        ids.add(cand.id.removeprefix("item-"))
    return ids


def _retrieval_covers(snapshot: CheckpointSnapshot, obligation_id: str) -> bool:
    return any(
        obs.query_id == obligation_id and obs.hits for obs in snapshot.retrieval
    )


def _memory_has(snapshot: CheckpointSnapshot, obligation_id: str) -> bool:
    return (
        snapshot.memory_state is not None
        and obligation_id in snapshot.memory_state.open_obligation_ids
    )


def attribute_attention_disagreement(
    snapshot: CheckpointSnapshot,
    truth: EvaluationTruth,
    *,
    arm_a: CheckpointArmResult,
    arm_b: CheckpointArmResult,
) -> AttributionCase | None:
    a_pass = arm_a.metrics.attention_accuracy >= 1.0
    b_pass = arm_b.metrics.attention_accuracy >= 1.0
    if a_pass == b_pass:
        return None

    required = must_surface_obligations_at(truth, snapshot.at)
    candidates = _candidate_obligation_ids(snapshot)
    surfaced = {oid for alert in snapshot.alerts for oid in alert.obligation_ids}
    missing = [oid for oid in required if oid not in surfaced]

    if missing:
        oid = missing[0]
        if oid not in candidates:
            cause = (
                FailureCause.RETRIEVAL
                if not _retrieval_covers(snapshot, oid)
                else FailureCause.INGESTION
            )
            narrative = f"Required {oid} absent from candidates at {snapshot.checkpoint_id}"
        elif not _memory_has(snapshot, oid):
            cause = FailureCause.MEMORY
            narrative = f"Required {oid} missing from memory open_obligation_ids"
        elif not a_pass and b_pass:
            cause = FailureCause.INTERPRETATION
            narrative = (
                f"LLM surfaced {oid}; heuristic missed (parents/brunch regression template)"
            )
        else:
            cause = FailureCause.ATTENTION_POLICY
            narrative = f"Heuristic policy missed MUST_SURFACE {oid}"
        return AttributionCase(
            checkpoint_id=snapshot.checkpoint_id,
            dimension="attention",
            cause=cause,
            narrative=narrative,
            arm_a_pass=a_pass,
            arm_b_pass=b_pass,
        )

    if not a_pass and b_pass:
        return AttributionCase(
            checkpoint_id=snapshot.checkpoint_id,
            dimension="attention",
            cause=FailureCause.INTERPRETATION,
            narrative=f"LLM corrected heuristic attention at {snapshot.checkpoint_id}",
            arm_a_pass=a_pass,
            arm_b_pass=b_pass,
        )

    return AttributionCase(
        checkpoint_id=snapshot.checkpoint_id,
        dimension="attention",
        cause=FailureCause.ATTENTION_POLICY,
        narrative=f"Attention disagreement at {snapshot.checkpoint_id}",
        arm_a_pass=a_pass,
        arm_b_pass=b_pass,
    )


def attribute_next_action_disagreement(
    arm_a: CheckpointArmResult,
    arm_b: CheckpointArmResult,
) -> AttributionCase | None:
    if arm_a.metrics.next_action_checkpoints_scored == 0:
        return None
    na_a = arm_a.metrics.next_action_accuracy >= 1.0
    na_b = arm_b.metrics.next_action_accuracy >= 1.0
    if na_a == na_b:
        return None
    if not na_a and na_b:
        cause, narrative = (
            FailureCause.INTERPRETATION,
            "LLM next_action improved on heuristic baseline",
        )
    else:
        cause, narrative = (
            FailureCause.NEXT_ACTION_POLICY,
            "Next action policy disagreement",
        )
    return AttributionCase(
        checkpoint_id=arm_a.checkpoint_id,
        dimension="next_action",
        cause=cause,
        narrative=narrative,
        arm_a_pass=na_a,
        arm_b_pass=na_b,
    )


def attribute_checkpoint_disagreements(
    snapshot: CheckpointSnapshot,
    truth: EvaluationTruth,
    *,
    arm_a: CheckpointArmResult,
    arm_b: CheckpointArmResult,
) -> list[AttributionCase]:
    cases: list[AttributionCase] = []
    att = attribute_attention_disagreement(snapshot, truth, arm_a=arm_a, arm_b=arm_b)
    if att:
        cases.append(att)
    na = attribute_next_action_disagreement(arm_a, arm_b)
    if na:
        cases.append(na)
    return cases


def attribute_benchmark(
    snapshots: dict[str, CheckpointSnapshot],
    truth: EvaluationTruth,
    *,
    arm_a_results: list[CheckpointArmResult],
    arm_b_results: list[CheckpointArmResult],
) -> list[AttributionCase]:
    by_a = {r.checkpoint_id: r for r in arm_a_results}
    by_b = {r.checkpoint_id: r for r in arm_b_results}
    cases: list[AttributionCase] = []
    for cp_id, snap in snapshots.items():
        if cp_id in by_a and cp_id in by_b:
            cases.extend(
                attribute_checkpoint_disagreements(
                    snap, truth, arm_a=by_a[cp_id], arm_b=by_b[cp_id]
                )
            )
    return cases


def enrich_failures_json(
    failures: dict[str, Any],
    attributions: list[AttributionCase],
) -> dict[str, Any]:
    enriched = dict(failures)
    enriched["attributions"] = [a.as_dict() for a in attributions]
    summary: dict[str, int] = {}
    for case in attributions:
        summary[case.cause.value] = summary.get(case.cause.value, 0) + 1
    enriched["attribution_summary"] = summary
    return enriched


def attribute_live_disagreements(
    snapshots: dict[str, CheckpointSnapshot],
    truth: EvaluationTruth,
    *,
    arm_a_results: list[CheckpointArmResult],
    arm_b_reps: dict[str, list[LiveRepResult]],
) -> list[AttributionCase]:
    """Attribute live-lane disagreements including unstable Arm B reps."""
    by_a = {r.checkpoint_id: r for r in arm_a_results}
    cases: list[AttributionCase] = []
    for cp_id, snap in snapshots.items():
        if cp_id not in by_a or cp_id not in arm_b_reps:
            continue
        reps = arm_b_reps[cp_id]
        if not reps:
            continue
        b_passes = [r.metrics.attention_accuracy >= 1.0 for r in reps]
        unstable = len(set(b_passes)) > 1
        majority_pass = sum(b_passes) >= (len(b_passes) // 2 + 1)
        idx = next((i for i, p in enumerate(b_passes) if p == majority_pass), 0)
        arm_b = CheckpointArmResult(
            checkpoint_id=cp_id,
            arm="B",
            metrics=reps[idx].metrics,
        )
        cases.extend(
            attribute_checkpoint_disagreements(
                snap, truth, arm_a=by_a[cp_id], arm_b=arm_b
            )
        )
        if unstable:
            cases.append(
                AttributionCase(
                    checkpoint_id=cp_id,
                    dimension="attention",
                    cause=FailureCause.INTERPRETATION,
                    narrative=f"Arm B unstable across {len(reps)} reps at {cp_id}",
                    arm_a_pass=by_a[cp_id].metrics.attention_accuracy >= 1.0,
                    arm_b_pass=majority_pass,
                )
            )
    return cases


__all__ = [
    "AttributionCase",
    "FailureCause",
    "attribute_benchmark",
    "attribute_checkpoint_disagreements",
    "attribute_live_disagreements",
    "enrich_failures_json",
]
