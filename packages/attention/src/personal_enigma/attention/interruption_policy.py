"""Deterministic interruption policy — semantic features + observable facts → decision.

Production policy never reads evaluator contract labels (MUST_SURFACE, etc.).
Callers supply ``CandidatePolicyFacts`` from domain/checkpoint state and
``SemanticFeatures`` from the remote semantic judge (Arm B2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

PolicyDecision = Literal["surface", "suppress", "context"]

# --- Tunable thresholds (calibration knobs; no evaluator labels) ---

CONFIDENCE_MIN = 0.50
"""Minimum model confidence before any non-suppress decision."""

SURFACE_SCORE_THRESHOLD = 0.72
"""Composite score at or above → surface."""

CONTEXT_SCORE_THRESHOLD = 0.55
"""Composite score at or above (but below surface) → context."""

WEIGHT_OBLIGATION_STRENGTH = 0.25
WEIGHT_USER_RESPONSIBILITY = 0.20
WEIGHT_IMPORTANCE = 0.15
WEIGHT_TIME_SENSITIVITY = 0.25
WEIGHT_ACTIONABILITY_NOW = 0.15

RESTFUL_URGENT_TIME_SENSITIVITY = 0.92
RESTFUL_URGENT_ACTIONABILITY = 0.92
"""On restful weekends, surface only when both exceed these bars."""

NEAR_TERM_HOURS = 36.0
"""Due within this window adds time-pressure boost to composite score."""

OVERDUE_SCORE_BOOST = 0.12
NEAR_TERM_MAX_BOOST = 0.10

NOISE_OBLIGATION_STRENGTH_MAX = 0.35
"""Inferred candidates with no open obligation below this → suppress."""

NOISE_INFERRED_KINDS: frozenset[str] = frozenset(
    {"inferred_obligation", "inferred_commitment"}
)

NOISE_EVIDENCE_PREFIX = "mail-noise-"


class InterruptionMode(StrEnum):
    NORMAL = "normal"
    RESTFUL_WEEKEND = "restful_weekend"


@dataclass(frozen=True, slots=True)
class SemanticFeatures:
    """Semantic interpretation from the remote judge (Arm B2)."""

    obligation_strength: float
    user_responsibility: float
    importance: float
    time_sensitivity: float
    actionability_now: float
    confidence: float
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CandidatePolicyFacts:
    """Observable world state for one attention candidate."""

    candidate_id: str
    now: datetime
    candidate_kind: str = ""
    obligation_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    has_open_obligation: bool = False
    is_completed: bool = False
    due_at: datetime | None = None
    has_existing_reminder: bool = False
    calendar_proximity_hours: float | None = None
    engine_suppressed: bool = False
    interruption_mode: InterruptionMode = InterruptionMode.NORMAL
    is_noise_evidence: bool = False

    @property
    def hours_until_due(self) -> float | None:
        if self.due_at is None:
            return None
        now = self.now if self.now.tzinfo else self.now.replace(tzinfo=UTC)
        due = self.due_at if self.due_at.tzinfo else self.due_at.replace(tzinfo=UTC)
        return (due - now).total_seconds() / 3600.0


@dataclass(frozen=True, slots=True)
class PolicyJudgement:
    decision: PolicyDecision
    reason: str | None = None
    composite_score: float = 0.0


def interruption_mode_for_instant(*, now: datetime, is_weekend: bool) -> InterruptionMode:
    """Derive interruption mode from calendar facts only."""
    if is_weekend:
        return InterruptionMode.RESTFUL_WEEKEND
    return InterruptionMode.NORMAL


def evidence_is_noise(evidence_ids: tuple[str, ...]) -> bool:
    return any(eid.startswith(NOISE_EVIDENCE_PREFIX) for eid in evidence_ids)


def composite_surface_score(
    semantic: SemanticFeatures,
    facts: CandidatePolicyFacts,
) -> float:
    """Weighted semantic score plus deterministic time-pressure boost."""
    score = (
        WEIGHT_OBLIGATION_STRENGTH * semantic.obligation_strength
        + WEIGHT_USER_RESPONSIBILITY * semantic.user_responsibility
        + WEIGHT_IMPORTANCE * semantic.importance
        + WEIGHT_TIME_SENSITIVITY * semantic.time_sensitivity
        + WEIGHT_ACTIONABILITY_NOW * semantic.actionability_now
    )
    hours = facts.hours_until_due
    if hours is not None:
        if hours <= 0:
            score += OVERDUE_SCORE_BOOST
        elif hours <= NEAR_TERM_HOURS:
            score += NEAR_TERM_MAX_BOOST * (1.0 - hours / NEAR_TERM_HOURS)
    if facts.is_noise_evidence:
        score *= 0.30
    if facts.calendar_proximity_hours is not None and facts.calendar_proximity_hours <= 2.0:
        score += 0.05
    return min(score, 1.0)


def decide_interruption(
    semantic: SemanticFeatures,
    facts: CandidatePolicyFacts,
) -> PolicyJudgement:
    """Map semantic interpretation + observable facts → surface/context/suppress."""
    if facts.engine_suppressed:
        return PolicyJudgement(decision="suppress", reason="engine_suppressed", composite_score=0.0)

    if semantic.confidence < CONFIDENCE_MIN:
        return PolicyJudgement(
            decision="suppress",
            reason="low_confidence",
            composite_score=composite_surface_score(semantic, facts),
        )

    if facts.interruption_mode == InterruptionMode.RESTFUL_WEEKEND:
        if (
            semantic.time_sensitivity < RESTFUL_URGENT_TIME_SENSITIVITY
            or semantic.actionability_now < RESTFUL_URGENT_ACTIONABILITY
        ):
            return PolicyJudgement(
                decision="suppress",
                reason="restful_weekend",
                composite_score=composite_surface_score(semantic, facts),
            )

    if (
        not facts.has_open_obligation
        and facts.candidate_kind in NOISE_INFERRED_KINDS
        and semantic.obligation_strength < NOISE_OBLIGATION_STRENGTH_MAX
    ):
        return PolicyJudgement(
            decision="suppress",
            reason="noise_no_obligation",
            composite_score=composite_surface_score(semantic, facts),
        )

    if facts.is_noise_evidence and semantic.obligation_strength < NOISE_OBLIGATION_STRENGTH_MAX:
        return PolicyJudgement(
            decision="suppress",
            reason="noise_evidence",
            composite_score=composite_surface_score(semantic, facts),
        )

    composite = composite_surface_score(semantic, facts)
    if composite >= SURFACE_SCORE_THRESHOLD:
        return PolicyJudgement(
            decision="surface",
            reason="composite_surface",
            composite_score=composite,
        )
    if composite >= CONTEXT_SCORE_THRESHOLD:
        return PolicyJudgement(
            decision="context",
            reason="composite_context",
            composite_score=composite,
        )
    return PolicyJudgement(decision="suppress", reason="below_threshold", composite_score=composite)


__all__ = [
    "CONFIDENCE_MIN",
    "CONTEXT_SCORE_THRESHOLD",
    "CandidatePolicyFacts",
    "CONTEXT_SCORE_THRESHOLD",
    "InterruptionMode",
    "NEAR_TERM_HOURS",
    "NOISE_EVIDENCE_PREFIX",
    "NOISE_INFERRED_KINDS",
    "NOISE_OBLIGATION_STRENGTH_MAX",
    "OVERDUE_SCORE_BOOST",
    "PolicyDecision",
    "PolicyJudgement",
    "RESTFUL_URGENT_ACTIONABILITY",
    "RESTFUL_URGENT_TIME_SENSITIVITY",
    "SURFACE_SCORE_THRESHOLD",
    "SemanticFeatures",
    "composite_surface_score",
    "decide_interruption",
    "evidence_is_noise",
    "interruption_mode_for_instant",
]
