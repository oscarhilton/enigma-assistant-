"""Attention → UI projection — qualification, ranking, presentation as separate layers.

Next Action (WORTH DOING) is never equated with attention ``context``. The
conversational layer may combine ``context`` items and ``next_actions`` in copy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from personal_enigma.attention.interruption_policy import (
    CONTEXT_SCORE_THRESHOLD,
    SURFACE_SCORE_THRESHOLD,
    CandidatePolicyFacts,
    InterruptionMode,
    PolicyDecision,
    SemanticFeatures,
    composite_surface_score,
    decide_interruption,
    evidence_is_noise,
    interruption_mode_for_instant,
)
from personal_enigma.attention.snapshot import (
    AttentionCandidateSnapshot,
    CheckpointSnapshot,
)

PolicyDecisionLiteral = Literal["surface", "context", "suppress"]
AttentionBucket = Literal["needs_you", "context", "can_wait"]


class SemanticInput(BaseModel):
    """Frozen semantic judge output for one candidate."""

    obligation_strength: float
    user_responsibility: float
    importance: float
    time_sensitivity: float
    actionability_now: float
    confidence: float
    reason_codes: list[str] = Field(default_factory=list)

    def to_features(self) -> SemanticFeatures:
        return SemanticFeatures(
            obligation_strength=self.obligation_strength,
            user_responsibility=self.user_responsibility,
            importance=self.importance,
            time_sensitivity=self.time_sensitivity,
            actionability_now=self.actionability_now,
            confidence=self.confidence,
            reason_codes=tuple(self.reason_codes),
        )


class AttentionReason(BaseModel):
    code: str
    label: str


class NextActionView(BaseModel):
    id: str
    title: str
    reason: str
    optional: bool = True
    estimated_minutes: int | None = None
    source_candidate_id: str | None = None


class AttentionItemView(BaseModel):
    id: str
    title: str
    explanation: str
    policy_decision: PolicyDecisionLiteral
    bucket: AttentionBucket
    rank: int | None = None
    composite_score: float | None = None
    actionability_now: float | None = None
    reasons: list[AttentionReason] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    state_changed_at: str | None = None


class CanWaitSummary(BaseModel):
    total_suppressed: int
    sample_titles: list[str] = Field(default_factory=list)


class PresentationPlan(BaseModel):
    chat_opening_count: int = 0
    notification_slot_count: int = 1
    proactive_silence: bool = False


class AttentionState(BaseModel):
    simulated_time: str
    checkpoint_id: str | None = None
    needs_you: list[AttentionItemView] = Field(default_factory=list)
    context: list[AttentionItemView] = Field(default_factory=list)
    next_actions: list[NextActionView] = Field(default_factory=list)
    can_wait_summary: CanWaitSummary | None = None
    presentation: PresentationPlan = Field(default_factory=PresentationPlan)


class QualificationDebug(BaseModel):
    item_id: str
    checkpoint_id: str
    policy_decision: PolicyDecisionLiteral
    composite_score: float
    surface_threshold: float = SURFACE_SCORE_THRESHOLD
    context_threshold: float = CONTEXT_SCORE_THRESHOLD
    obligation_strength: float
    user_responsibility: float
    importance: float
    time_sensitivity: float
    actionability_now: float
    confidence: float
    overdue_boost: float = 0.0
    near_term_boost: float = 0.0
    calendar_boost: float = 0.0
    noise_multiplier: float = 1.0
    eligible_for_needs_you: bool
    policy_reason: str | None = None
    reason_codes: list[str] = Field(default_factory=list)


@dataclass
class ProjectedCandidate:
    candidate: AttentionCandidateSnapshot
    semantic: SemanticInput
    facts: CandidatePolicyFacts
    judgement: Any
    composite: float
    bucket: AttentionBucket


@dataclass
class ProjectionArtifacts:
    state: AttentionState
    debug_by_id: dict[str, QualificationDebug] = field(default_factory=dict)


def _temporal_facts(at: datetime) -> dict[str, Any]:
    if at.tzinfo is None:
        at = at.replace(tzinfo=UTC)
    utc = at.astimezone(UTC).replace(microsecond=0)
    return {"is_weekend": utc.weekday() >= 5}


def build_policy_facts(
    snapshot: CheckpointSnapshot,
    candidate: AttentionCandidateSnapshot,
) -> CandidatePolicyFacts:
    temporal = _temporal_facts(snapshot.at)
    open_ids = set(
        snapshot.memory_state.open_obligation_ids if snapshot.memory_state else []
    )
    obligation_id = candidate.obligation_ids[0] if candidate.obligation_ids else None
    has_open = obligation_id in open_ids if obligation_id else False
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
        due_at=None,
        has_existing_reminder=has_reminder,
        calendar_proximity_hours=cal_hours,
        engine_suppressed=candidate.suppressed,
        interruption_mode=InterruptionMode(mode.value),
        is_noise_evidence=evidence_is_noise(tuple(candidate.evidence_ids)),
    )


def policy_decision_to_bucket(decision: PolicyDecision) -> AttentionBucket:
    if decision == "surface":
        return "needs_you"
    if decision == "context":
        return "context"
    return "can_wait"


def _boost_breakdown(
    semantic: SemanticFeatures,
    facts: CandidatePolicyFacts,
) -> tuple[float, float, float, float]:
    hours = facts.hours_until_due
    overdue = 0.0
    near_term = 0.0
    if hours is not None:
        if hours <= 0:
            overdue = 0.12
        elif hours <= 36.0:
            near_term = 0.10 * (1.0 - hours / 36.0)
    calendar = 0.0
    if facts.calendar_proximity_hours is not None and facts.calendar_proximity_hours <= 2.0:
        calendar = 0.05
    noise_multiplier = 0.30 if facts.is_noise_evidence else 1.0
    return overdue, near_term, calendar, noise_multiplier


def _explanation_for(candidate: AttentionCandidateSnapshot, semantic: SemanticInput) -> str:
    if semantic.actionability_now >= 0.85:
        return "Unblocked now — you could move this forward when you have a moment."
    if semantic.time_sensitivity >= 0.5:
        return "Timing is starting to matter, but it does not need to interrupt you yet."
    return "Still relevant — Enigma is holding this as context, not an interrupt."


def _derive_next_actions(
    snapshot: CheckpointSnapshot,
    projected: list[ProjectedCandidate],
) -> list[NextActionView]:
    """Next-action / support layer — separate from attention qualification.

    Context items remain in ``context[]``. This function decides whether the
    support layer suggests WORTH DOING; it does not remap attention buckets.
    """
    if snapshot.next_action is not None:
        na = snapshot.next_action
        return [
            NextActionView(
                id=na.action_id or "next-action-primary",
                title=na.title,
                reason=na.why_this_now or "A useful next step when you have capacity.",
                optional=True,
                estimated_minutes=na.estimated_minutes,
            )
        ]
    actions: list[NextActionView] = []
    for row in projected:
        if row.bucket != "context":
            continue
        if row.semantic.actionability_now < 0.85:
            continue
        actions.append(
            NextActionView(
                id=f"next-{row.candidate.id}",
                title=row.candidate.title,
                reason="Unblocked now",
                optional=True,
                source_candidate_id=row.candidate.id,
            )
        )
    return actions[:2]


def build_presentation_plan(needs_you_count: int) -> PresentationPlan:
    if needs_you_count == 0:
        return PresentationPlan(
            chat_opening_count=0,
            notification_slot_count=0,
            proactive_silence=True,
        )
    return PresentationPlan(
        chat_opening_count=needs_you_count,
        notification_slot_count=min(1, needs_you_count),
        proactive_silence=False,
    )


def project_attention_state(
    snapshot: CheckpointSnapshot,
    semantics: dict[str, SemanticInput],
) -> ProjectionArtifacts:
    projected: list[ProjectedCandidate] = []
    debug_by_id: dict[str, QualificationDebug] = {}

    for candidate in snapshot.candidate_set:
        semantic_input = semantics.get(candidate.id)
        if semantic_input is None:
            continue
        semantic = semantic_input.to_features()
        facts = build_policy_facts(snapshot, candidate)
        judgement = decide_interruption(semantic, facts)
        composite = composite_surface_score(semantic, facts)
        bucket = policy_decision_to_bucket(judgement.decision)
        overdue, near_term, calendar, noise_mult = _boost_breakdown(semantic, facts)
        debug_by_id[candidate.id] = QualificationDebug(
            item_id=candidate.id,
            checkpoint_id=snapshot.checkpoint_id,
            policy_decision=judgement.decision,
            composite_score=composite,
            obligation_strength=semantic.obligation_strength,
            user_responsibility=semantic.user_responsibility,
            importance=semantic.importance,
            time_sensitivity=semantic.time_sensitivity,
            actionability_now=semantic.actionability_now,
            confidence=semantic.confidence,
            overdue_boost=overdue,
            near_term_boost=near_term,
            calendar_boost=calendar,
            noise_multiplier=noise_mult,
            eligible_for_needs_you=composite >= SURFACE_SCORE_THRESHOLD,
            policy_reason=judgement.reason,
            reason_codes=list(semantic.reason_codes),
        )
        projected.append(
            ProjectedCandidate(
                candidate=candidate,
                semantic=semantic_input,
                facts=facts,
                judgement=judgement,
                composite=composite,
                bucket=bucket,
            )
        )

    needs_you_rows = sorted(
        [row for row in projected if row.bucket == "needs_you"],
        key=lambda row: (-row.composite, row.candidate.id),
    )
    context_rows = sorted(
        [row for row in projected if row.bucket == "context"],
        key=lambda row: (-row.composite, row.candidate.id),
    )
    can_wait_rows = [row for row in projected if row.bucket == "can_wait"]

    def _item(row: ProjectedCandidate, rank: int | None) -> AttentionItemView:
        return AttentionItemView(
            id=row.candidate.id,
            title=row.candidate.title,
            explanation=_explanation_for(row.candidate, row.semantic),
            policy_decision=row.judgement.decision,
            bucket=row.bucket,
            rank=rank,
            composite_score=row.composite,
            actionability_now=row.semantic.actionability_now,
            reasons=[
                AttentionReason(code=code, label=code.replace("_", " ").title())
                for code in row.semantic.reason_codes
            ],
            evidence_ids=list(row.candidate.evidence_ids),
            state_changed_at=snapshot.at.isoformat(),
        )

    needs_you = [_item(row, index + 1) for index, row in enumerate(needs_you_rows)]
    context = [_item(row, index + 1) for index, row in enumerate(context_rows)]
    suppressed_titles = [
        row.candidate.title for row in can_wait_rows if row.candidate.title
    ]
    for candidate in snapshot.suppressed_candidates:
        if candidate.title:
            suppressed_titles.append(candidate.title)

    state = AttentionState(
        simulated_time=snapshot.at.isoformat(),
        checkpoint_id=snapshot.checkpoint_id,
        needs_you=needs_you,
        context=context,
        next_actions=_derive_next_actions(snapshot, projected),
        can_wait_summary=CanWaitSummary(
            total_suppressed=len(can_wait_rows) + len(snapshot.suppressed_candidates),
            sample_titles=suppressed_titles[:5],
        ),
        presentation=build_presentation_plan(len(needs_you)),
    )
    return ProjectionArtifacts(state=state, debug_by_id=debug_by_id)


__all__ = [
    "AttentionBucket",
    "AttentionItemView",
    "AttentionState",
    "CanWaitSummary",
    "NextActionView",
    "PresentationPlan",
    "ProjectionArtifacts",
    "QualificationDebug",
    "SemanticInput",
    "build_presentation_plan",
    "build_policy_facts",
    "policy_decision_to_bucket",
    "project_attention_state",
]
