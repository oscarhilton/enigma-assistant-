"""Retention gate — establishment ≠ justification to retain (C29).

Pipeline::

    GroundedAssertion
      → epistemic strength sufficient?
      → legitimate user-owned purpose?
      → proportionate?
      → lifetime?
      → DURABLE / TTL / EPHEMERAL / REJECT

Confirmation grants epistemic status. Purpose grants retention.
Truth does not imply retention.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field

from personal_enigma.domain.grounding import (
    AssertionKind,
    AssertionValidityKind,
    DerivationKind,
    EpistemicStatus,
    GroundedAssertion,
)
from personal_enigma.domain.retention import RetentionClass, RetentionPurpose

_SELF_SUBJECTS = frozenset({"self", "user", "me", "person_self"})

_ESTABLISHMENT_STATUSES = frozenset(
    {
        EpistemicStatus.USER_REPORTED,
        EpistemicStatus.USER_CONFIRMED,
        EpistemicStatus.SOURCE_OBSERVED,
        EpistemicStatus.EXTERNALLY_VERIFIED,
        EpistemicStatus.SYSTEM_VERIFIED,
        EpistemicStatus.DETERMINISTICALLY_DERIVED,
        EpistemicStatus.MODEL_INFERRED,
    }
)

_REJECTED_EPISTEMIC_STATUSES = frozenset(
    {
        EpistemicStatus.UNKNOWN,
        EpistemicStatus.CONFLICTED,
        EpistemicStatus.STALE,
        EpistemicStatus.USER_UNCERTAIN,
    }
)

_DURABLE_EPISTEMIC_STATUSES = frozenset(
    {
        EpistemicStatus.USER_CONFIRMED,
        EpistemicStatus.USER_REPORTED,
        EpistemicStatus.SOURCE_OBSERVED,
        EpistemicStatus.EXTERNALLY_VERIFIED,
        EpistemicStatus.SYSTEM_VERIFIED,
        EpistemicStatus.DETERMINISTICALLY_DERIVED,
    }
)

_CONCRETE_LIFE_PREDICATES = frozenset(
    {
        "likes",
        "prefers",
        "birthday",
        "allergic_to",
        "works_on",
        "committed_to",
        "plans_to",
        "lives_in",
        "gift_history",
        "depends_on",
        "convention",
        "has_project",
        "relationship",
        "date",
    }
)

_PROHIBITED_THIRD_PARTY_PREDICATES = frozenset(
    {
        "is_emotionally_dependent_on",
        "personality_type",
        "relationship_strength",
        "psychological_state",
        "is_depressed",
        "is_anxious",
        "persuadability",
        "self_esteem",
        "political_leaning",
        "behavioural_pattern",
    }
)

_PROFILE_PREDICATE_FRAGMENTS = (
    "emotionally",
    "dependent",
    "personality",
    "psycholog",
    "persuad",
    "self_esteem",
    "relationship_strength",
    "behavioural",
)


class RetentionOutcome(StrEnum):
    """Gate decision — what may survive beyond the work that produced it."""

    DURABLE = "durable"
    TTL = "ttl"
    EPHEMERAL = "ephemeral"
    REJECT = "reject"


class RetentionRejectionReason(StrEnum):
    """Why retention was denied."""

    INSUFFICIENT_EPISTEMIC_STATUS = "insufficient_epistemic_status"
    INFERENCE_NOT_DURABLE = "inference_not_durable"
    NO_LEGITIMATE_PURPOSE = "no_legitimate_purpose"
    THIRD_PARTY_PROFILING = "third_party_profiling"
    HYPOTHESIS_NOT_PROMOTED = "hypothesis_not_promoted"
    DOSSIER_RISK = "dossier_risk"


class RetentionDecision(BaseModel):
    """Outcome of evaluating whether an established assertion deserves persistence."""

    assertion_id: str
    outcome: RetentionOutcome
    retention_class: RetentionClass
    purpose: RetentionPurpose | None = None
    lifetime: str | None = None
    provenance_refs: list[str] = Field(default_factory=list)
    rejection_reason: RetentionRejectionReason | None = None
    rationale: str = ""


class ForgetCascadeResult(BaseModel):
    """Ids removed when a retained assertion is forgotten — content never logged."""

    root_assertion_id: str
    deleted_assertion_ids: list[str] = Field(default_factory=list)
    deleted_derived_ids: list[str] = Field(default_factory=list)
    audit_id: str | None = None
    trigger: str = "forget"  # "forget" | "ttl_expiry"


class DurableAssertionStore(Protocol):
    """Stub interface for durable life-memory assertions (implementation deferred)."""

    def store(self, assertion: GroundedAssertion, decision: RetentionDecision) -> str: ...

    def forget(self, assertion_id: str) -> ForgetCascadeResult: ...

    def list_retained_ids(self) -> list[str]: ...


def is_self_subject(subject: str) -> bool:
    normalized = subject.strip().lower().replace("-", "_")
    if normalized in _SELF_SUBJECTS:
        return True
    return normalized.startswith("person_self")


def evaluate_retention(
    assertion: GroundedAssertion,
    *,
    now: datetime | None = None,
) -> RetentionDecision:
    """Decide whether a grounded assertion may survive beyond the current request."""
    _ = now  # reserved for TTL expiry evaluation in later slices
    provenance = list(assertion.evidence_refs) + list(assertion.derived_from)

    if assertion.epistemic_status in _REJECTED_EPISTEMIC_STATUSES:
        return _decision(
            assertion,
            outcome=RetentionOutcome.REJECT,
            retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
            rejection_reason=RetentionRejectionReason.INSUFFICIENT_EPISTEMIC_STATUS,
            rationale="Assertion is not established strongly enough to retain.",
            provenance_refs=provenance,
        )

    if assertion.epistemic_status not in _ESTABLISHMENT_STATUSES:
        return _decision(
            assertion,
            outcome=RetentionOutcome.REJECT,
            retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
            rejection_reason=RetentionRejectionReason.INSUFFICIENT_EPISTEMIC_STATUS,
            rationale="Assertion is not established strongly enough to retain.",
            provenance_refs=provenance,
        )

    if assertion.kind in (AssertionKind.HYPOTHESIS, AssertionKind.PATTERN):
        return _decision(
            assertion,
            outcome=RetentionOutcome.EPHEMERAL,
            retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
            rejection_reason=RetentionRejectionReason.HYPOTHESIS_NOT_PROMOTED,
            rationale="Hypotheses and patterns are answer-only until user-confirmed.",
            provenance_refs=provenance,
        )

    if assertion.epistemic_status == EpistemicStatus.MODEL_INFERRED:
        return _decision(
            assertion,
            outcome=RetentionOutcome.EPHEMERAL,
            retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
            rejection_reason=RetentionRejectionReason.INFERENCE_NOT_DURABLE,
            rationale="Inferred assertions may answer but must not silently become durable.",
            provenance_refs=provenance,
        )

    if assertion.derivation_kind == DerivationKind.INFERENCE:
        return _decision(
            assertion,
            outcome=RetentionOutcome.EPHEMERAL,
            retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
            rejection_reason=RetentionRejectionReason.INFERENCE_NOT_DURABLE,
            rationale="Inference-derived assertions are ephemeral unless explicitly confirmed.",
            provenance_refs=provenance,
        )

    third_party = not is_self_subject(assertion.subject)
    if third_party and _is_profiling_predicate(assertion.predicate):
        return _decision(
            assertion,
            outcome=RetentionOutcome.REJECT,
            retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
            rejection_reason=RetentionRejectionReason.THIRD_PARTY_PROFILING,
            rationale="Third-party psychological or behavioural profiling is not retainable.",
            provenance_refs=provenance,
        )

    purpose = _resolve_purpose(assertion)
    if purpose is None:
        return _decision(
            assertion,
            outcome=RetentionOutcome.EPHEMERAL,
            retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
            rejection_reason=RetentionRejectionReason.NO_LEGITIMATE_PURPOSE,
            rationale="No legitimate user-owned purpose justifies retention.",
            provenance_refs=provenance,
        )

    if third_party and assertion.predicate not in _CONCRETE_LIFE_PREDICATES:
        if assertion.kind != AssertionKind.PREFERENCE:
            return _decision(
                assertion,
                outcome=RetentionOutcome.REJECT,
                retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
                rejection_reason=RetentionRejectionReason.DOSSIER_RISK,
                rationale="Third-party retention limited to concrete life facts.",
                provenance_refs=provenance,
            )

    if assertion.epistemic_status not in _DURABLE_EPISTEMIC_STATUSES:
        return _decision(
            assertion,
            outcome=RetentionOutcome.EPHEMERAL,
            retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
            provenance_refs=provenance,
            rationale="Established for answering only.",
        )

    outcome, retention_class, lifetime = _lifetime_for(assertion, purpose)
    return _decision(
        assertion,
        outcome=outcome,
        retention_class=retention_class,
        purpose=purpose,
        lifetime=lifetime,
        provenance_refs=provenance,
        rationale=_rationale_for(outcome, purpose, third_party),
    )


def _is_profiling_predicate(predicate: str) -> bool:
    normalized = predicate.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in _PROHIBITED_THIRD_PARTY_PREDICATES:
        return True
    return any(fragment in normalized for fragment in _PROFILE_PREDICATE_FRAGMENTS)


def _resolve_purpose(assertion: GroundedAssertion) -> RetentionPurpose | None:
    tags = {tag.strip().lower() for tag in assertion.purpose_tags}
    if "user_explicit_recall" in tags or "remember_this" in tags:
        return RetentionPurpose.USER_EXPLICIT_RECALL
    if "temporary_case" in tags or "gift_planning" in tags:
        return RetentionPurpose.TEMPORARY_CASE
    if assertion.kind == AssertionKind.PREFERENCE:
        return RetentionPurpose.LIFE_FACT
    if assertion.kind == AssertionKind.FACT:
        if assertion.predicate in _CONCRETE_LIFE_PREDICATES:
            return RetentionPurpose.LIFE_FACT
        if "open_loop" in tags:
            return RetentionPurpose.OPEN_LOOP_TRACKING
    if assertion.kind == AssertionKind.DELEGATION:
        return RetentionPurpose.OPEN_LOOP_TRACKING
    return None


def _lifetime_for(
    assertion: GroundedAssertion,
    purpose: RetentionPurpose,
) -> tuple[RetentionOutcome, RetentionClass, str | None]:
    if purpose == RetentionPurpose.TEMPORARY_CASE:
        lifetime = assertion.temporal_scope or "until_case_resolved"
        if assertion.validity_kind == AssertionValidityKind.TTL:
            return RetentionOutcome.TTL, RetentionClass.ACTIVE_UNTIL_RESOLVED, lifetime
        return RetentionOutcome.TTL, RetentionClass.ACTIVE_UNTIL_RESOLVED, lifetime

    if assertion.validity_kind in (
        AssertionValidityKind.TTL,
        AssertionValidityKind.UNTIL_EVENT,
        AssertionValidityKind.DERIVED_LIFETIME,
    ):
        lifetime = assertion.temporal_scope or (
            assertion.valid_until.isoformat() if assertion.valid_until else "bounded"
        )
        return RetentionOutcome.TTL, RetentionClass.ACTIVE_UNTIL_RESOLVED, lifetime

    if assertion.validity_kind == AssertionValidityKind.SOURCE_LIFETIME:
        return RetentionOutcome.TTL, RetentionClass.EXPIRE_WITH_SOURCE, "source_lifetime"

    return RetentionOutcome.DURABLE, RetentionClass.DURABLE_SHADOW, None


def _rationale_for(
    outcome: RetentionOutcome,
    purpose: RetentionPurpose,
    third_party: bool,
) -> str:
    scope = "third-party concrete fact" if third_party else "user-owned life fact"
    if outcome == RetentionOutcome.DURABLE:
        return f"Durable {scope} with purpose {purpose.value}."
    if outcome == RetentionOutcome.TTL:
        return f"Purpose-bound {scope}; expires when justification ends."
    return "Retained for current answer only."


def _decision(
    assertion: GroundedAssertion,
    *,
    outcome: RetentionOutcome,
    retention_class: RetentionClass,
    purpose: RetentionPurpose | None = None,
    lifetime: str | None = None,
    provenance_refs: list[str] | None = None,
    rejection_reason: RetentionRejectionReason | None = None,
    rationale: str = "",
) -> RetentionDecision:
    return RetentionDecision(
        assertion_id=assertion.id,
        outcome=outcome,
        retention_class=retention_class,
        purpose=purpose,
        lifetime=lifetime,
        provenance_refs=list(provenance_refs or []),
        rejection_reason=rejection_reason,
        rationale=rationale,
    )
