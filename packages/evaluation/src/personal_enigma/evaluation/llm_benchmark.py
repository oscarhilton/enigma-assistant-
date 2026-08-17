"""LLM judge benchmark — Arm A heuristic vs Arm B PAYG (Reasoning Value Gate / R03).

Top-1 / top-3 flow
------------------
**Arm B1 (legacy):** per-candidate judge-v1 with direct surface/suppress/context decision.
**Arm B2 (default):** semantic-judge-v1 features → deterministic interruption policy.

1. For each candidate, Arm B calls the remote judge with a per-candidate prompt.
2. B1 returns ``JudgeV1Output``; B2 returns ``SemanticJudgeV1Output``.
3. B2 applies ``decide_interruption`` (observable facts + semantic features).
4. Rank surfaced candidates deterministically for top-3 / top-1 metrics.
5. ``policy_judgement`` (final alerts) is what metrics score against contracts.

Arm B logs ``model_judgement`` (ranked policy surfaces) and ``policy_judgement``
(final alerts after snapshot engine suppressions) separately.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from personal_enigma.attention.interruption_policy import (
    CandidatePolicyFacts,
    InterruptionMode,
    SemanticFeatures,
    decide_interruption,
    evidence_is_noise,
    interruption_mode_for_instant,
)
from personal_enigma.evaluation.checkpoint_runner import (
    load_checkpoint_snapshot,
    verify_arm_a_integrity,
)
from personal_enigma.evaluation.evaluation_transformed_v1_frozen import (
    snapshot_to_evaluation_transformed_v1_frozen,
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
    SemanticJudgeV1Output,
    SemanticJudgeV1ParseError,
    parse_judge_v1_output,
    parse_semantic_judge_v1_output,
    validate_evidence_ids,
)
from personal_enigma.transformation import (
    DefaultEnigmaTransformer,
    StubHmacResolver,
    TransformedContext,
    candidate_input_from_observation,
    infer_relations_from_evidence,
    merge_relations,
    pseudonymise_remote_text,
)
from personal_enigma.transformation.relations import SemanticRelation, relation_to_dict

EvaluationContextMode = Literal[
    "evaluation_transformed_v1",
    "evaluation_transformed_v2",
    "full_synthetic",
    "transformed",
]

JudgeArm = Literal["b1", "b2"]
PROMPT_VERSION = "semantic-judge-v1"
PROMPT_VERSION_B1 = "judge-v1"
SURFACE_CONFIDENCE_MIN = 0.5
# Demo/evaluation only — never use for real Private roots (ADR-005).
_EVAL_TRANSFORM_HMAC_KEY = b"evaluation-transform-gate-key"
_EVAL_RESOLVER = StubHmacResolver(_EVAL_TRANSFORM_HMAC_KEY)
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
Do not rely on any prior heuristic policy — evaluate evidence independently.

Attention decision semantics:
- surface: this candidate warrants the user's attention **now**
  (action or decision needed at this checkpoint instant)
- suppress: no useful intervention at this instant
- context: genuine but non-urgent information; use when relevant but no current
  intervention is useful

Important distinctions:
- An open obligation alone does not justify surface
- Important ≠ needs attention now; open ≠ urgent; candidate ≠ alert
- It is valid and often desirable for every candidate to receive suppress or
  context (zero surfaces is ok)

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

_SEMANTIC_JUDGE_PROMPT = """You are Enigma's semantic interpreter for Demo Mode evaluation.

Interpret the single candidate below against the sanitised checkpoint context.
Do NOT decide surface/suppress/context — return semantic feature scores only.
Enigma applies deterministic interruption policy locally using your scores plus
observable facts (now, due dates, open obligations, calendar proximity).

Return JSON only (no markdown, no chain-of-thought) using schema semantic-judge-v1.
Emit required score fields first; optional next_action comes last and may be null.

{{
  "schema_version": "semantic-judge-v1",
  "obligation_strength": 0.0-1.0,
  "user_responsibility": 0.0-1.0,
  "importance": 0.0-1.0,
  "time_sensitivity": 0.0-1.0,
  "actionability_now": 0.0-1.0,
  "confidence": 0.0-1.0,
  "reason_codes": ["EXPLICIT_REQUEST", "USER_OWNS_ACTION"],
  "next_action": {next_action_schema}
}}

Candidate:
{candidate_json}

Context snapshot:
{context_json}

When summary and relations[] disagree, treat relations[] as authoritative for
dependency, blocker resolution, and actionability transitions. The summary may
compress or lag; structured relation facts override prose.
"""


def _evaluation_transformer(*, allow_remote: bool = True) -> DefaultEnigmaTransformer:
    return DefaultEnigmaTransformer(hmac_key=_EVAL_TRANSFORM_HMAC_KEY, allow_remote=allow_remote)


def canonical_json_hash(payload: Any) -> str:
    """Stable SHA-256 over canonical JSON (sort_keys, compact separators)."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def transformed_context_hash(ctx: TransformedContext) -> str:
    return canonical_json_hash(ctx.model_dump(mode="json"))


def serialise_transformed_context_for_judge(
    ctx: TransformedContext,
    *,
    candidate: AttentionCandidateObservation,
    checkpoint_at: datetime,
    privacy: Literal["legacy_v1", "remote_safe"],
    snapshot: CheckpointSnapshot | None = None,
) -> dict[str, Any]:
    """Privacy-gated wire shape for semantic judge — sole source for prompt context_json."""
    wire: dict[str, Any] = {
        "checkpoint": checkpoint_temporal_facts(checkpoint_at),
        "summary": ctx.summary,
        "candidate": candidate_to_dict(candidate, privacy=privacy),
        "entities": list(ctx.entities),
        "relations": [relation_to_dict(r) for r in ctx.relations],
    }
    if snapshot is not None:
        wire["memory"] = (
            {"open_obligation_ids": list(snapshot.memory_state.open_obligation_ids)}
            if snapshot.memory_state
            else {}
        )
        wire["retrieval"] = [
            {"query_id": r.query_id, "hits": list(r.hits)} for r in snapshot.retrieval
        ]
    return wire


@dataclass(frozen=True, slots=True)
class PromptAuditRecord:
    checkpoint_id: str
    context_mode: str
    candidate_id: str
    transformed_context_hash: str
    context_json_hash: str
    prompt_hash: str
    model: str
    rep: int
    context_json: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "checkpoint_id": self.checkpoint_id,
            "context_mode": self.context_mode,
            "candidate_id": self.candidate_id,
            "transformed_context_hash": self.transformed_context_hash,
            "context_json_hash": self.context_json_hash,
            "prompt_hash": self.prompt_hash,
            "model": self.model,
            "rep": self.rep,
        }
        if self.context_json is not None:
            out["context_json"] = self.context_json
        return out


def append_prompt_audit(record: PromptAuditRecord, audit_dir: str | Path) -> None:
    """Append one JSONL audit line (Step 7 proof artifact)."""
    root = Path(audit_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "prompt-audit.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record.as_dict(), sort_keys=True) + "\n")


def assert_prompt_safe(prompt: str, *, remote_payload: str | None = None) -> None:
    lower = prompt.lower()
    for marker in FORBIDDEN_PROMPT_MARKERS:
        if marker.lower() in lower:
            raise ValueError(
                f"benchmark prompt must not include evaluator-only marker {marker!r}"
            )
    if remote_payload is not None:
        from personal_enigma.transformation.title_sanitisation import (
            assert_no_raw_identity_in_text,
        )

        assert_no_raw_identity_in_text(remote_payload)


def checkpoint_temporal_facts(at: datetime) -> dict[str, Any]:
    """Deterministic calendar facts for judge context (not ground-truth labels)."""
    if at.tzinfo is None:
        at = at.replace(tzinfo=UTC)
    utc = at.astimezone(UTC).replace(microsecond=0)
    day_names = (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    )
    return {
        "now": utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "day_of_week": day_names[utc.weekday()],
        "is_weekend": utc.weekday() >= 5,
    }


def legacy_candidate_dict(candidate: AttentionCandidateObservation) -> dict[str, Any]:
    """Historical v1 — raw titles (ablation column only)."""
    return {
        "id": candidate.id,
        "title": candidate.title,
        "obligation_ids": candidate.obligation_ids,
        "evidence_ids": candidate.evidence_ids,
        "score": candidate.score,
    }


def legacy_snapshot_context_dict(snapshot: CheckpointSnapshot) -> dict[str, Any]:
    return {
        "checkpoint_id": snapshot.checkpoint_id,
        **checkpoint_temporal_facts(snapshot.at),
        "candidates": [legacy_candidate_dict(c) for c in snapshot.candidate_set],
        "memory": (
            {"open_obligation_ids": list(snapshot.memory_state.open_obligation_ids)}
            if snapshot.memory_state
            else {}
        ),
        "retrieval": [
            {"query_id": r.query_id, "hits": list(r.hits)} for r in snapshot.retrieval
        ],
    }


def snapshot_to_context_dict(
    snapshot: CheckpointSnapshot,
    *,
    privacy: Literal["legacy_v1", "remote_safe"] = "remote_safe",
) -> dict[str, Any]:
    if privacy == "legacy_v1":
        return legacy_snapshot_context_dict(snapshot)
    return {
        "checkpoint_id": snapshot.checkpoint_id,
        **checkpoint_temporal_facts(snapshot.at),
        "candidates": [remote_safe_candidate_dict(c) for c in snapshot.candidate_set],
        "memory": (
            {"open_obligation_ids": list(snapshot.memory_state.open_obligation_ids)}
            if snapshot.memory_state
            else {}
        ),
        "retrieval": [
            {"query_id": r.query_id, "hits": list(r.hits)} for r in snapshot.retrieval
        ],
    }


def remote_safe_candidate_dict(
    candidate: AttentionCandidateObservation,
) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "title": pseudonymise_remote_text(
            candidate.title, resolver=_EVAL_RESOLVER
        ),
        "obligation_ids": candidate.obligation_ids,
        "evidence_ids": candidate.evidence_ids,
        "score": candidate.score,
    }


def candidate_to_dict(
    candidate: AttentionCandidateObservation,
    *,
    privacy: Literal["legacy_v1", "remote_safe"] = "remote_safe",
) -> dict[str, Any]:
    if privacy == "legacy_v1":
        return legacy_candidate_dict(candidate)
    return remote_safe_candidate_dict(candidate)


def _normalise_context_mode(
    mode: EvaluationContextMode,
) -> Literal["evaluation_transformed_v1", "evaluation_transformed_v2", "full_synthetic"]:
    if mode == "full_synthetic":
        return "full_synthetic"
    if mode in ("evaluation_transformed_v1", "transformed"):
        return "evaluation_transformed_v1"
    return "evaluation_transformed_v2"


def _context_for_mode(
    snapshot: CheckpointSnapshot, mode: EvaluationContextMode
) -> TransformedContext:
    normalised = _normalise_context_mode(mode)
    if normalised == "full_synthetic":
        return snapshot_to_full_synthetic_context(snapshot)
    if normalised == "evaluation_transformed_v1":
        return snapshot_to_evaluation_transformed_v1_frozen(snapshot)
    return snapshot_to_production_transformed(snapshot)


def infer_relations_from_candidate(
    candidate: AttentionCandidateObservation,
    *,
    checkpoint_at: datetime | None = None,
) -> list[SemanticRelation]:
    """Infer privacy-safe relations from observable candidate evidence (general patterns)."""
    groups = [
        infer_relations_from_evidence(
            obligation_id=oid,
            evidence_ids=list(candidate.evidence_ids),
            checkpoint_at=checkpoint_at,
        )
        for oid in candidate.obligation_ids
    ]
    return merge_relations(*groups)


def snapshot_to_production_transformed(snapshot: CheckpointSnapshot) -> TransformedContext:
    """DefaultEnigmaTransformer production path (evaluation uses same code)."""
    transformer = _evaluation_transformer(allow_remote=True)
    return transformer.build_remote_attention_context(
        checkpoint_id=snapshot.checkpoint_id,
        checkpoint_at=snapshot.at,
        candidates=[
            candidate_input_from_observation(c) for c in snapshot.candidate_set[:5]
        ],
        context_mode="evaluation_transformed_v2",
        may_transmit_remotely=True,
    )


def snapshot_to_evaluation_transformed_v1(snapshot: CheckpointSnapshot) -> TransformedContext:
    """Frozen historical stub (pre-R-L09 v2)."""
    return snapshot_to_evaluation_transformed_v1_frozen(snapshot)


def snapshot_to_transformed_context(snapshot: CheckpointSnapshot) -> TransformedContext:
    """Default evaluation transform — production v2 path."""
    return snapshot_to_production_transformed(snapshot)


def _prompt_privacy_for_context(ctx: TransformedContext) -> Literal["legacy_v1", "remote_safe"]:
    mode = str(ctx.metadata.get("context_mode", ""))
    if mode == "evaluation_transformed_v1" or ctx.metadata.get("frozen"):
        return "legacy_v1"
    return "remote_safe"


def snapshot_to_full_synthetic_context(snapshot: CheckpointSnapshot) -> TransformedContext:
    base = snapshot_to_production_transformed(snapshot)
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
            "metadata": {**base.metadata, "context_mode": "full_synthetic"},
            "may_transmit_remotely": False,
        }
    )


def build_judge_prompt(
    snapshot: CheckpointSnapshot,
    candidate: AttentionCandidateObservation,
    *,
    attention_only: bool = False,
    privacy: Literal["legacy_v1", "remote_safe"] = "remote_safe",
) -> str:
    next_action_schema = (
        "null"
        if attention_only
        else (
            '{ "title": "<micro-step>", "action_type": "admin", '
            '"estimated_minutes": <int>, "confidence": 0.0-1.0 }'
        )
    )
    candidate_json = json.dumps(
        candidate_to_dict(candidate, privacy=privacy), indent=2
    )
    context_json = json.dumps(
        snapshot_to_context_dict(snapshot, privacy=privacy), indent=2
    )
    prompt = _JUDGE_PROMPT.format(
        next_action_schema=next_action_schema,
        candidate_json=candidate_json,
        context_json=context_json,
    )
    if privacy == "legacy_v1":
        assert_prompt_safe(prompt)
    else:
        assert_prompt_safe(prompt, remote_payload=candidate_json + context_json)
    return prompt


def build_semantic_judge_prompt(
    ctx: TransformedContext,
    candidate: AttentionCandidateObservation,
    *,
    checkpoint_at: datetime,
    snapshot: CheckpointSnapshot | None = None,
    attention_only: bool = False,
    privacy: Literal["legacy_v1", "remote_safe"] = "remote_safe",
) -> str:
    next_action_schema = (
        "null"
        if attention_only
        else '{ "title": "<micro-step>", "estimated_minutes": <int> }'
    )
    context_dict = serialise_transformed_context_for_judge(
        ctx,
        candidate=candidate,
        checkpoint_at=checkpoint_at,
        privacy=privacy,
        snapshot=snapshot,
    )
    candidate_json = json.dumps(context_dict["candidate"], indent=2)
    context_json = json.dumps(context_dict, indent=2)
    prompt = _SEMANTIC_JUDGE_PROMPT.format(
        next_action_schema=next_action_schema,
        candidate_json=candidate_json,
        context_json=context_json,
    )
    if privacy == "legacy_v1":
        assert_prompt_safe(prompt)
    else:
        assert_prompt_safe(prompt, remote_payload=candidate_json + context_json)
    return prompt


def semantic_output_to_features(output: SemanticJudgeV1Output) -> SemanticFeatures:
    return SemanticFeatures(
        obligation_strength=output.obligation_strength,
        user_responsibility=output.user_responsibility,
        importance=output.importance,
        time_sensitivity=output.time_sensitivity,
        actionability_now=output.actionability_now,
        confidence=output.confidence,
        reason_codes=tuple(c.value for c in output.reason_codes),
    )


def build_candidate_policy_facts(
    snapshot: CheckpointSnapshot,
    candidate: AttentionCandidateObservation,
    truth: EvaluationTruth | None = None,
) -> CandidatePolicyFacts:
    temporal = checkpoint_temporal_facts(snapshot.at)
    open_ids = set(
        snapshot.memory_state.open_obligation_ids if snapshot.memory_state else []
    )
    obligation_id = candidate.obligation_ids[0] if candidate.obligation_ids else None
    due_at = None
    is_completed = False
    has_open = False
    if obligation_id:
        has_open = obligation_id in open_ids
        if truth is not None:
            obligation = truth.ground_truth.obligation_by_id(obligation_id)
            if obligation is not None:
                due_at = obligation.due_at
                is_completed = not obligation.is_open_at(snapshot.at)
                has_open = obligation.is_open_at(snapshot.at)
    has_reminder = any(eid.startswith("rem-") for eid in candidate.evidence_ids)
    cal_hours: float | None = None
    for eid in candidate.evidence_ids:
        if eid.startswith("cal-"):
            cal_hours = 0.5
            break
    mode = interruption_mode_for_instant(
        now=snapshot.at,
        is_weekend=bool(temporal.get("is_weekend")),
    )
    return CandidatePolicyFacts(
        candidate_id=candidate.id,
        now=snapshot.at,
        candidate_kind=candidate.kind,
        obligation_ids=tuple(candidate.obligation_ids),
        evidence_ids=tuple(candidate.evidence_ids),
        has_open_obligation=has_open,
        is_completed=is_completed,
        due_at=due_at,
        has_existing_reminder=has_reminder,
        calendar_proximity_hours=cal_hours,
        engine_suppressed=candidate.suppressed,
        interruption_mode=InterruptionMode(mode.value),
        is_noise_evidence=evidence_is_noise(tuple(candidate.evidence_ids)),
    )


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
    semantic_output: SemanticJudgeV1Output | None = None
    parse_error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "output": self.output.model_dump(mode="json") if self.output else None,
            "semantic_output": (
                self.semantic_output.model_dump(mode="json") if self.semantic_output else None
            ),
            "parse_error": self.parse_error,
        }


@dataclass(frozen=True, slots=True)
class SemanticRankedCandidate:
    candidate: AttentionCandidateObservation
    semantic: SemanticJudgeV1Output
    policy_decision: Literal["surface", "suppress", "context"]
    composite_score: float = 0.0


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


def rank_semantic_judgements(
    snapshot: CheckpointSnapshot,
    judgements: list[CandidateJudgement],
    truth: EvaluationTruth,
) -> list[SemanticRankedCandidate]:
    by_id = {c.id: c for c in snapshot.candidate_set}
    ranked: list[tuple[SemanticRankedCandidate, tuple[float, float, str]]] = []
    for judgement in judgements:
        if judgement.semantic_output is None:
            continue
        candidate = by_id.get(judgement.candidate_id)
        if candidate is None:
            continue
        facts = build_candidate_policy_facts(snapshot, candidate, truth)
        policy = decide_interruption(
            semantic_output_to_features(judgement.semantic_output),
            facts,
        )
        if policy.decision != "surface":
            continue
        ranked.append(
            (
                SemanticRankedCandidate(
                    candidate=candidate,
                    semantic=judgement.semantic_output,
                    policy_decision=policy.decision,
                    composite_score=policy.composite_score,
                ),
                (-policy.composite_score, -candidate.score, candidate.id),
            )
        )
    ranked.sort(key=lambda row: row[1])
    return [row[0] for row in ranked]


def semantic_ranked_to_alerts(
    snapshot: CheckpointSnapshot,
    ranked: list[SemanticRankedCandidate],
) -> list[SurfacedAlert]:
    alerts: list[SurfacedAlert] = []
    for row in ranked:
        alerts.append(
            SurfacedAlert(
                id=row.candidate.id,
                title=row.candidate.title,
                kind=row.candidate.kind,
                score=row.composite_score,
                obligation_ids=list(row.candidate.obligation_ids),
                evidence_ids=list(row.candidate.evidence_ids),
                surfaced_at=snapshot.at,
            )
        )
    return alerts


def filter_semantic_snapshot_policy(
    snapshot: CheckpointSnapshot,
    ranked: list[SemanticRankedCandidate],
) -> list[SurfacedAlert]:
    alerts: list[SurfacedAlert] = []
    for row in ranked:
        if row.candidate.suppressed:
            continue
        alerts.append(
            SurfacedAlert(
                id=row.candidate.id,
                title=row.candidate.title,
                kind=row.candidate.kind,
                score=row.composite_score,
                obligation_ids=list(row.candidate.obligation_ids),
                evidence_ids=list(row.candidate.evidence_ids),
                surfaced_at=snapshot.at,
            )
        )
    return alerts


def pick_semantic_next_action(
    ranked: list[SemanticRankedCandidate],
) -> NextActionObservation | None:
    for row in ranked:
        if row.semantic.next_action is None:
            continue
        title = row.semantic.next_action.title
        return NextActionObservation(
            title=title,
            action_id=title.strip().lower().replace(" ", "_"),
            estimated_minutes=row.semantic.next_action.estimated_minutes,
        )
    return None


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
    experiment_invalid: bool = False
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
            "experiment_invalid": self.experiment_invalid,
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
    judge_arm: JudgeArm = "b2",
    prompt_privacy: Literal["legacy_v1", "remote_safe"] = "remote_safe",
) -> CandidateJudgement:
    if judge_arm == "b2":
        return _judge_candidate_semantic(
            snapshot,
            candidate,
            service=service,
            context=context,
            model=model,
            attention_only=attention_only,
            prompt_privacy=prompt_privacy,
        )
    prompt = build_judge_prompt(
        snapshot, candidate, attention_only=attention_only, privacy=prompt_privacy
    )
    result = None
    try:
        result = service.reason(context, prompt=prompt, model=model)
        output = parse_judge_v1_output(result.text)
        validate_evidence_ids(output, set(candidate.evidence_ids))
        return CandidateJudgement(candidate_id=candidate.id, output=output)
    except (JudgeV1ParseError, InvalidEvidenceIdsError, ValueError) as exc:
        detail = str(exc)
        if result is not None:
            debug_bits: list[str] = []
            finish_reason = result.metadata.get("finish_reason")
            response_shape = result.metadata.get("response_shape")
            if finish_reason:
                debug_bits.append(f"finish_reason={finish_reason}")
            if response_shape:
                debug_bits.append(str(response_shape))
            if debug_bits:
                detail = f"{detail} [{' '.join(debug_bits)}]"
        return CandidateJudgement(
            candidate_id=candidate.id,
            parse_error=detail,
        )


def _judge_candidate_semantic(
    snapshot: CheckpointSnapshot,
    candidate: AttentionCandidateObservation,
    *,
    service: PaygReasoningService,
    context: TransformedContext,
    model: str,
    attention_only: bool,
    prompt_privacy: Literal["legacy_v1", "remote_safe"] = "remote_safe",
    audit_dir: str | Path | None = None,
) -> CandidateJudgement:
    try:
        prompt = build_semantic_judge_prompt(
            context,
            candidate,
            checkpoint_at=snapshot.at,
            snapshot=snapshot,
            attention_only=attention_only,
            privacy=prompt_privacy,
        )
    except ValueError as exc:
        return CandidateJudgement(
            candidate_id=candidate.id,
            parse_error=f"prompt_build_failed: {exc}",
        )
    context_dict = serialise_transformed_context_for_judge(
        context,
        candidate=candidate,
        checkpoint_at=snapshot.at,
        privacy=prompt_privacy,
        snapshot=snapshot,
    )
    if audit_dir is not None:
        rep = int(context.metadata.get("rep", 0))
        ctx_hash = transformed_context_hash(context)
        ctx_json_hash = canonical_json_hash(context_dict)
        prompt_hash = canonical_json_hash(prompt)
        context_mode = str(context.metadata.get("context_mode", "unknown"))
        append_prompt_audit(
            PromptAuditRecord(
                checkpoint_id=snapshot.checkpoint_id,
                context_mode=context_mode,
                candidate_id=candidate.id,
                transformed_context_hash=ctx_hash,
                context_json_hash=ctx_json_hash,
                prompt_hash=prompt_hash,
                model=model,
                rep=rep,
                context_json=(
                    context_dict if prompt_privacy == "remote_safe" else None
                ),
            ),
            audit_dir,
        )
    result = None
    try:
        result = service.reason(context, prompt=prompt, model=model)
        output = parse_semantic_judge_v1_output(result.text)
        return CandidateJudgement(candidate_id=candidate.id, semantic_output=output)
    except (SemanticJudgeV1ParseError, ValueError) as exc:
        detail = str(exc)
        if result is not None:
            debug_bits: list[str] = []
            finish_reason = result.metadata.get("finish_reason")
            response_shape = result.metadata.get("response_shape")
            retried = result.metadata.get("retried_for_length")
            if finish_reason:
                debug_bits.append(f"finish_reason={finish_reason}")
            if retried == "true":
                debug_bits.append("retried_for_length=true")
            if response_shape:
                debug_bits.append(str(response_shape))
            if debug_bits:
                detail = f"{detail} [{' '.join(debug_bits)}]"
        return CandidateJudgement(candidate_id=candidate.id, parse_error=detail)


def score_arm_b(
    snapshot: CheckpointSnapshot,
    truth: EvaluationTruth,
    *,
    service: PaygReasoningService,
    context: TransformedContext | None = None,
    model: str = "payg-gate",
    attention_only: bool = False,
    judge_arm: JudgeArm = "b2",
    prompt_privacy: Literal["legacy_v1", "remote_safe"] = "remote_safe",
    audit_dir: str | Path | None = None,
) -> CheckpointArmResult:
    ctx = context or snapshot_to_transformed_context(snapshot)
    ctx = ctx.model_copy(
        update={"metadata": {**ctx.metadata, "judge_arm": judge_arm}}
    )
    effective_privacy = prompt_privacy
    if prompt_privacy == "remote_safe" and _prompt_privacy_for_context(ctx) == "legacy_v1":
        effective_privacy = "legacy_v1"
    start = time.perf_counter()
    judgements: list[CandidateJudgement] = []
    total_cost = 0.0
    first_parse_error: str | None = None
    prompt_build_failed = False

    for candidate in snapshot.candidate_set:
        if judge_arm == "b2":
            judgement = _judge_candidate_semantic(
                snapshot,
                candidate,
                service=service,
                context=ctx,
                model=model,
                attention_only=attention_only,
                prompt_privacy=effective_privacy,
                audit_dir=audit_dir,
            )
        else:
            judgement = _judge_candidate(
                snapshot,
                candidate,
                service=service,
                context=ctx,
                model=model,
                attention_only=attention_only,
                judge_arm=judge_arm,
                prompt_privacy=effective_privacy,
            )
        judgements.append(judgement)
        if judgement.parse_error and first_parse_error is None:
            first_parse_error = judgement.parse_error
        if judgement.parse_error and judgement.parse_error.startswith("prompt_build_failed"):
            prompt_build_failed = True

    latency_ms = (time.perf_counter() - start) * 1000.0

    all_judgements_failed = first_parse_error is not None and all(
        j.output is None and j.semantic_output is None for j in judgements
    )
    if prompt_build_failed or all_judgements_failed:
        metrics = compute_support_fitness_metrics(
            truth, alerts=[], next_action=None, at=snapshot.at
        )
        return CheckpointArmResult(
            checkpoint_id=snapshot.checkpoint_id,
            arm="B",
            metrics=metrics,
            latency_ms=latency_ms,
            parse_error=first_parse_error,
            experiment_invalid=True,
            candidate_judgements=judgements,
        )

    if judge_arm == "b2":
        ranked_sem = rank_semantic_judgements(snapshot, judgements, truth)
        model_alerts = semantic_ranked_to_alerts(snapshot, ranked_sem)
        policy_alerts = filter_semantic_snapshot_policy(snapshot, ranked_sem)
        next_action = (
            None if attention_only else pick_semantic_next_action(ranked_sem)
        )
    else:
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
    context_mode: EvaluationContextMode = "evaluation_transformed_v1",
    attention_only: bool = False,
    judge_arm: JudgeArm = "b2",
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
        ctx = _context_for_mode(snapshot, context_mode)
        prompt_privacy = (
            "legacy_v1"
            if _normalise_context_mode(context_mode) == "evaluation_transformed_v1"
            else "remote_safe"
        )
        report.arm_b.append(
            score_arm_b(
                snapshot,
                truth,
                service=service,
                context=ctx,
                attention_only=attention_only,
                judge_arm=judge_arm,
                prompt_privacy=prompt_privacy,
            )
        )

    report.arm_a_aggregate = aggregate_support_fitness([r.metrics for r in report.arm_a])
    valid_b = [r for r in report.arm_b if not r.experiment_invalid]
    report.arm_b_aggregate = aggregate_support_fitness([r.metrics for r in valid_b])
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
    "JudgeArm",
    "LlmBenchmarkReport",
    "PolicyJudgement",
    "PROMPT_VERSION",
    "PROMPT_VERSION_B1",
    "SURFACE_CONFIDENCE_MIN",
    "SemanticRankedCandidate",
    "aggregate_support_fitness",
    "apply_attention_policy",
    "assert_prompt_safe",
    "benchmark_cost_events",
    "build_candidate_policy_facts",
    "build_judge_prompt",
    "PromptAuditRecord",
    "append_prompt_audit",
    "build_semantic_judge_prompt",
    "canonical_json_hash",
    "checkpoint_temporal_facts",
    "serialise_transformed_context_for_judge",
    "transformed_context_hash",
    "filter_semantic_snapshot_policy",
    "filter_snapshot_attention_policy",
    "pick_next_action",
    "pick_semantic_next_action",
    "rank_candidate_judgements",
    "rank_semantic_judgements",
    "run_llm_benchmark",
    "score_arm_a",
    "score_arm_b",
    "semantic_output_to_features",
    "semantic_ranked_to_alerts",
    "snapshot_to_full_synthetic_context",
    "snapshot_to_transformed_context",
]
